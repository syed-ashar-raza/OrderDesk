"""Build customer replies using verified ticket and tool data."""

from datetime import date, datetime


def build_customer_reply(ticket: dict, tool_calls: list[dict]) -> str:
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
