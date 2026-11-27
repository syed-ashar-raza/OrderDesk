"""Multi-turn tool orchestration for the TicketPilot agent."""

import json
import logging
import os
import re
from datetime import date

from groq import Groq

from src.agent.prompts import TRIAGE_SYSTEM_PROMPT
from src.agent.replies import build_customer_reply
from src.schema import ORDER_TOOLS
from src.tools import (
    check_refund_eligibility,
    classify_ticket_category,
    lookup_order_status,
    search_policy_docs,
)

logger = logging.getLogger(__name__)

TOOL_FUNCTIONS = {
    "lookup_order_status": lookup_order_status,
    "classify_ticket_category": classify_ticket_category,
    "check_refund_eligibility": check_refund_eligibility,
    "search_policy_docs": search_policy_docs,
}


def run_ticket_triage(
    ticket: dict,
    client: Groq,
    max_tool_rounds: int = 5,
) -> dict:
    """Run a ticket through the agent until it produces a final response."""

    if not isinstance(ticket, dict):
        raise TypeError("Ticket must be a dictionary.")

    if max_tool_rounds < 1:
        raise ValueError("max_tool_rounds must be at least 1.")

    ticket_id = ticket.get("ticket_id", "UNKNOWN")
    subject = ticket.get("subject", "")
    body = ticket.get("body", "")
    order_id = ticket.get("order_id")

    ticket_text = (
        f"Ticket ID: {ticket_id}\n"
        f"Subject: {subject}\n"
        f"Body: {body}\n"
        f"Customer email: {ticket.get('customer_email', 'Not provided')}\n"
        f"Order ID: {order_id or 'Not provided'}\n"
        f"Current date: {date.today().isoformat()}"
    )

    messages = [
        {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
        {"role": "user", "content": ticket_text},
    ]

    tool_calls_log = []
    tool_rounds = 0

    while True:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=messages,
            tools=ORDER_TOOLS,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls or []

        if not tool_calls:
            retrieval_done = any(
                entry.get("tool") == "search_policy_docs"
                for entry in tool_calls_log
            )

            if _requires_policy_retrieval(ticket_text) and not retrieval_done:
                if tool_rounds >= max_tool_rounds:
                    return {
                        "ticket_id": ticket_id,
                        "category": None,
                        "reply": "",
                        "tool_calls": tool_calls_log,
                        "tool_rounds": tool_rounds,
                        "status": "safety_cap_reached",
                    }

                print(f"\\n[TICKET {ticket_id}] ENFORCED POLICY RETRIEVAL")
                try:
                    retrieval_query = f"Subject: {subject}\nIssue: {body}"
                    result = search_policy_docs(retrieval_query, top_k=3)
                except (RuntimeError, ValueError, TypeError) as exc:
                    result = {"found": False, "error": str(exc), "results": []}

                print("Result:", json.dumps(result, default=str))
                tool_calls_log.append({
                    "tool": "search_policy_docs",
                    "arguments": {"query": retrieval_query, "top_k": 3},
                    "result": result,
                })
                messages.append({
                    "role": "user",
                    "content": (
                        "Mandatory policy retrieval has now been performed. "
                        "Review this evidence before producing your final response: "
                        + json.dumps(result, default=str)
                    ),
                })
                tool_rounds += 1
                continue

            return {
                "ticket_id": ticket_id,
                "category": _extract_category(assistant_message.content) or _category_from_tool_calls(tool_calls_log),
                "reply": build_customer_reply(ticket, tool_calls_log),
                "tool_calls": tool_calls_log,
                "tool_rounds": tool_rounds,
                "status": "completed",
            }

        if tool_rounds >= max_tool_rounds:
            logger.warning(
                "Safety cap reached for ticket %s after %s tool rounds.",
                ticket_id,
                max_tool_rounds,
            )
            return {
                "ticket_id": ticket_id,
                "category": None,
                "reply": "",
                "tool_calls": tool_calls_log,
                "tool_rounds": tool_rounds,
                "status": "safety_cap_reached",
            }

        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    call.model_dump(exclude_none=True)
                    for call in tool_calls
                ],
            }
        )

        for call in tool_calls:
            function_name = call.function.name
            arguments = {}

            if function_name not in TOOL_FUNCTIONS:
                result = {
                    "error": f"Unknown tool: {function_name}",
                }
            else:
                arguments = {}
                try:
                    arguments = json.loads(call.function.arguments or "{}")

                    if not isinstance(arguments, dict):
                        raise ValueError("Tool arguments must be a JSON object.")

                    if function_name == "search_policy_docs":
                        arguments["query"] = (
                            f"Subject: {subject}\nIssue: {body}"
                        )
                        arguments["top_k"] = 3

                    print(
                        f"\n[TICKET {ticket_id}] TOOL: {function_name}"
                    )
                    print("Arguments:", json.dumps(arguments))

                    result = TOOL_FUNCTIONS[function_name](**arguments)

                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    result = {"error": str(exc)}

            print("Result:", json.dumps(result, default=str))

            tool_calls_log.append(
                {
                    "tool": function_name,
                    "arguments": arguments,
                    "result": result,
                }
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, default=str),
                }
            )

        tool_rounds += 1



def _requires_policy_retrieval(ticket_text: str) -> bool:
    """Identify tickets requiring policy evidence before a reply."""
    terms = (
        "refund", "return", "shipping", "shipment", "delivery",
        "delivered", "deadline", "business day", "policy",
        "duplicate charge", "charged twice", "billing rule",
        "damaged", "defective", "escalat",
    )
    normalized = ticket_text.lower()
    return any(term in normalized for term in terms)


def _category_from_tool_calls(tool_calls_log: list[dict]) -> str | None:
    """Get the authoritative category returned by the classification tool."""

    valid_categories = {"billing", "shipping", "bug", "other"}

    for entry in tool_calls_log:
        if entry.get("tool") == "classify_ticket_category":
            result = entry.get("result", {})
            category = result.get("category") if isinstance(result, dict) else None

            if category in valid_categories:
                return category

    return None


def _extract_category(response_text: str | None) -> str | None:
    """Extract a category from the model's final response."""

    if not response_text:
        return None

    match = re.search(
        r"(?im)^\s*\**\s*(?:suggested\s+)?category\s*\**\s*:\s*\**\s*(billing|shipping|bug|other)\b",
        response_text,
    )
    if match:
        return match.group(1).lower()

    return None


def create_groq_client() -> Groq:
    """Create a Groq client using the project's environment configuration."""

    import os

    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing from .env")

    return Groq(api_key=api_key)
