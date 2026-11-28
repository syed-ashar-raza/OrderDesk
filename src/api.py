"""FastAPI service for the OrderDesk ticket triage agent."""

import json
import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.agent.triage_agent import create_groq_client, run_ticket_triage

logger = logging.getLogger(__name__)

app = FastAPI(
    title="OrderDesk Triage API",
    description="API for the TicketPilot AI support triage agent.",
    version="1.0.0",
)


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str = "API-REQUEST"
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=10000)
    order_id: str | None = None
    customer_email: str | None = None

    @field_validator("subject", "body")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field cannot contain only whitespace.")
        return value.strip()


@lru_cache(maxsize=1)
def get_groq_client():
    return create_groq_client()


def log_triage_request(ticket_id: str, category: str | None, tools_used: list[str]) -> None:
    """Append non-sensitive triage metadata to the local JSONL log."""

    record = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "ticket_id": ticket_id,
        "category": category,
        "tools_used": tools_used,
    }

    try:
        log_path = Path("logs/triage_requests.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(record) + "\n")
    except OSError:
        logger.exception("Could not write triage request log.")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "orderdesk-triage-api"}


@app.post("/triage")
def triage_ticket(request: TriageRequest):
    ticket = request.model_dump()

    try:
        client = get_groq_client()
        result = run_ticket_triage(ticket, client)

        tools_used = list(dict.fromkeys(
            call.get("tool", "unknown")
            for call in result.get("tool_calls", [])
        ))

        log_triage_request(
            ticket_id=result.get("ticket_id") or ticket.get("ticket_id"),
            category=result.get("category"),
            tools_used=tools_used,
        )

        policy_sources = list(dict.fromkeys(
            item.get("source")
            for call in result.get("tool_calls", [])
            if call.get("tool") == "search_policy_docs"
            for item in call.get("result", {}).get("results", [])
            if item.get("source")
        ))

        return {
            "ticket_id": result.get("ticket_id"),
            "category": result.get("category"),
            "reply": result.get("reply"),
            "tools_used": tools_used,
            "policy_sources": policy_sources,
            "classification_confidence": result.get("classification_confidence"),
            "escalated": result.get("escalated", False),
            "outcome": result.get("outcome", "completed"),
            "escalation_reason": result.get("escalation_reason"),
            "tool_rounds": result.get("tool_rounds"),
            "status": result.get("status"),
        }

    except RuntimeError as exc:
        logger.exception("Triage service configuration error.")
        raise HTTPException(
            status_code=503,
            detail="Triage service is not configured correctly.",
        ) from exc

    except Exception as exc:
        logger.exception("Ticket triage failed.")
        raise HTTPException(
            status_code=502,
            detail="Ticket triage failed because an upstream service encountered an error.",
        ) from exc
