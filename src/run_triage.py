"""Run TicketPilot against the complete sample ticket dataset."""

import json
import logging
from pathlib import Path

from src.agent.triage_agent import create_groq_client, run_ticket_triage


ROOT = Path(__file__).resolve().parent.parent
TICKETS_FILE = ROOT / "data" / "tickets.json"
RESULTS_FILE = ROOT / "data" / "triage_results.json"


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    with TICKETS_FILE.open("r", encoding="utf-8-sig") as file:
        tickets = json.load(file)

    if not isinstance(tickets, list) or not tickets:
        raise ValueError("Ticket dataset must be a non-empty JSON list.")

    client = create_groq_client()
    results = []

    print(f"\nTicketPilot processing {len(tickets)} tickets.\n")

    for ticket in tickets:
        print("\n" + "=" * 65)
        print(f"TICKET: {ticket['ticket_id']}")
        print(f"SUBJECT: {ticket['subject']}")
        print("=" * 65)

        result = run_ticket_triage(ticket, client)
        results.append(result)

        print("\nSUGGESTED CATEGORY:", result["category"])
        print("TOOLS CALLED:", [
            call["tool"] for call in result["tool_calls"]
        ])
        print("TOOL ROUNDS:", result["tool_rounds"])
        print("STATUS:", result["status"])
        print("CUSTOMER REPLY:\n", result["reply"])

    with RESULTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    completed = sum(
        result["status"] == "completed" for result in results
    )

    print("\n" + "=" * 65)
    print("TICKETPILOT RUN SUMMARY")
    print("=" * 65)
    print(f"Total tickets: {len(results)}")
    print(f"Completed: {completed}")
    print(f"Safety cap reached: {len(results) - completed}")
    print(f"Results saved: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
