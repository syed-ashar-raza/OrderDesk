"""Build customer replies using verified ticket and tool data."""

from datetime import date, datetime


def _build_base_customer_reply(ticket: dict, tool_calls: list[dict]) -> str:
    """Create a factual customer reply without unsupported commitments."""

    results = {
        entry["tool"]: entry.get("result", {})
        for entry in tool_calls
    }

    order_id = ticket.get("order_id")
    refund = results.get("check_refund_eligibility")
    order = results.get("lookup_order_status")
    category_result = results.get("classify_ticket_category", {})
    category = category_result.get("category", "other")

    if refund is not None:
        if not refund.get("found"):
            return (
                f"Thank you for contacting us about order {order_id}. "
                "We could not verify the order details, so refund eligibility "
                "cannot currently be confirmed. Please check the order ID "
                "and contact support for further assistance."
            )

        if refund.get("eligible"):
            return (
                f"Thank you for contacting us about order {order_id}. "
                "According to our demo policy, this order qualifies for a "
                "refund review. This result does not confirm that a review "
                "has started or that a refund has been approved, initiated, "
                "or processed. The available system does not provide a "
                "refund-processing status."
            )

        return (
            f"Thank you for contacting us about order {order_id}. "
            "According to our demo policy, this order does not currently "
            "qualify for a refund review. This is an eligibility result "
            "under the demonstration policy, not confirmation of a payment "
            "or refund transaction."
        )

    if order is not None:
        if not order.get("found"):
            return (
                f"Thank you for contacting us about order {order_id}. "
                "We could not find this order in the available order records, "
                "so its current status cannot be verified."
            )

        status = order.get("status", "Unknown")
        eta = order.get("estimated_delivery")
        customer = order.get("customer")
        greeting = f"Hello {customer}," if customer else "Hello,"

        reply = (
            f"{greeting}\n\n"
            f"Order {order_id} is currently listed as **{status}** "
            "in our order records."
        )

        if eta:
            try:
                parsed_eta = datetime.strptime(eta, "%Y-%m-%d").date()
                formatted_eta = parsed_eta.strftime("%B %d, %Y")
                reply += (
                    f" The recorded estimated delivery date is "
                    f"**{formatted_eta}**."
                )

                if parsed_eta < date.today():
                    reply += (
                        " This estimated date has passed. The available "
                        "order lookup does not provide a revised delivery date."
                    )
            except ValueError:
                reply += " The recorded estimated delivery date could not be interpreted."

        reply += (
            "\n\nThis status lookup does not confirm dispatch, tracking "
            "information, or a guaranteed delivery date."
        )
        return reply

    ticket_text = (
        f"{ticket.get('subject', '')} {ticket.get('body', '')}"
    ).lower()

    duplicate_charge_terms = (
        "charged twice",
        "duplicate charge",
        "double charge",
        "charged two times",
        "same purchase",
    )

    if category == "billing" and any(
        term in ticket_text for term in duplicate_charge_terms
    ):
        return (
            "Thank you for reporting the duplicate charge. "
            "We cannot currently verify whether both entries represent "
            "completed charges or whether one is a pending authorization. "
            "According to our demo billing policy, a pending authorization "
            "may temporarily appear alongside a completed charge. Such "
            "authorizations are generally released within 5 to 10 business "
            "days, although the actual timing depends on your bank or "
            "payment provider.\n\n"
            "If the duplicate charge remains unresolved, the policy "
            "requires referral to the billing support team. This triage "
            "does not confirm that a referral has been made. Please use "
            "the approved secure support channel for payment details; "
            "never share your full card number, password, or security code "
            "in a support ticket."
        )

    if category == "bug":
        return (
            "Thank you for reporting this technical issue. We understand "
            "that the problem is affecting your experience. The available "
            "triage tools do not confirm whether an engineering team has "
            "been notified or whether the issue is being investigated. "
            "Please include any relevant error details when contacting "
            "support for further assistance."
        )

    return (
        "Thank you for contacting OrderDesk Support. Your ticket has been "
        "classified for review. The available information does not establish "
        "any additional action or outcome, but your reported issue has been "
        "captured in this triage result."
    )


def build_customer_reply(ticket: dict, tool_calls: list[dict]) -> str:
    """Build a deterministic reply and attach actual retrieved policy evidence."""
    reply = _build_base_customer_reply(ticket, tool_calls)

    retrieval_entries = [
        entry for entry in tool_calls
        if entry.get("tool") == "search_policy_docs"
    ]

    if not retrieval_entries:
        return reply

    result = retrieval_entries[-1].get("result", {})
    policy_results = result.get("results", [])

    if not result.get("found") or not policy_results:
        return (
            reply
            + "\n\n**Policy verification:** The available policy information "
            "does not establish the rule for this situation. Human review is "
            "recommended; no policy outcome can be confirmed."
        )

    evidence_lines = [
        "\n\n**Policy evidence retrieved:**"
    ]

    for item in policy_results:
        source = item.get("source", "Unknown source")
        chunk_id = item.get("chunk_id", "Unknown chunk")
        content = item.get("content", "")
        evidence_lines.append(
            f"\n- Source: `{source}` | Chunk: `{chunk_id}`"
            f"\n  Evidence: {content}"
        )

    return reply + "".join(evidence_lines)
