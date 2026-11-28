import json
import time
from pathlib import Path

from src.agent.triage_agent import create_groq_client, run_ticket_triage


def main():
    tickets = json.loads(
        Path("eval_tickets.json").read_text(encoding="utf-8")
    )

    client = create_groq_client()
    passed = 0
    category_correct = 0
    total = len(tickets)

    print(f"\nOrderDesk Evaluation: {total} tickets\n")

    for expected in tickets:
        ticket = {
            key: value
            for key, value in expected.items()
            if not key.startswith("expected_")
        }

        ticket_id = ticket["ticket_id"]

        try:
            for attempt in range(4):
                try:
                    result = run_ticket_triage(ticket, client)
                    break
                except Exception as exc:
                    message = str(exc).lower()
                    limited = (
                        "429" in message
                        or "rate_limit_exceeded" in message
                        or "ratelimiterror" in type(exc).__name__.lower()
                    )
                    if not limited or attempt == 3:
                        raise
                    delay = 15 * (attempt + 1)
                    print(
                        f"  Groq rate limit: retrying {ticket_id} "
                        f"in {delay}s (attempt {attempt + 2}/4)."
                    )
                    time.sleep(delay)

            category_ok = (
                result.get("category") == expected["expected_category"]
            )

            if category_ok:
                category_correct += 1

            policy_sources = [
                item.get("source", "").lower()
                for call in result.get("tool_calls", [])
                if call.get("tool") == "search_policy_docs"
                for item in call.get("result", {}).get("results", [])
                if item.get("source")
            ]

            topic = expected.get("expected_policy_topic")

            if topic in (None, "unsupported"):
                policy_ok = True
            else:
                policy_ok = any(
                    topic.lower() in source
                    for source in policy_sources
                )

            escalation_ok = (
                result.get("escalated", False)
                == expected["expected_escalation"]
            )

            ticket_passed = (
                category_ok and policy_ok and escalation_ok
            )

            if ticket_passed:
                passed += 1

            print(
                f"{ticket_id}: {'PASS' if ticket_passed else 'FAIL'} "
                f"| category={'PASS' if category_ok else 'FAIL'} "
                f"| policy={'PASS' if policy_ok else 'FAIL'} "
                f"| escalation={'PASS' if escalation_ok else 'FAIL'}"
            )

            if not ticket_passed:
                print(
                    f"  Expected category: {expected['expected_category']}"
                    f" | Actual: {result.get('category')}"
                )
                print(f"  Policy sources: {policy_sources}")
                print(
                    f"  Expected escalation: "
                    f"{expected['expected_escalation']}"
                    f" | Actual: {result.get('escalated')}"
                )

        except Exception as exc:
            print(f"{ticket_id}: ERROR | {type(exc).__name__}: {exc}")

    print("\n========== EVALUATION SUMMARY ==========")
    print(f"Tickets evaluated: {total}")
    print(f"Tickets passed: {passed}/{total}")
    print(f"Category accuracy: {category_correct / total * 100:.1f}%")
    print(f"Overall pass rate: {passed / total * 100:.1f}%")
    print("========================================")


if __name__ == "__main__":
    main()
