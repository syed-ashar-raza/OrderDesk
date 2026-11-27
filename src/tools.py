"""Application tools available to the OrderDesk AI agents."""

from src.database import ORDERS
from src.policy_retriever import search_policy_docs


def lookup_order_status(order_id: str) -> dict:
    """Look up an order by ID and return its status."""

    if not isinstance(order_id, str) or not order_id.strip():
        return {
            "found": False,
            "error": "A valid order ID is required.",
        }

    normalized_id = order_id.strip().upper()
    order = ORDERS.get(normalized_id)

    if order is None:
        return {
            "found": False,
            "order_id": normalized_id,
            "error": "Order not found.",
        }

    return {
        "found": True,
        **order,
    }


def classify_ticket_category(text: str) -> dict:
    """Classify a support ticket using deterministic keyword rules."""

    if not isinstance(text, str) or not text.strip():
        return {
            "category": "other",
            "reason": "Ticket text is empty or invalid.",
        }

    normalized_text = text.lower()

    keywords = {
        "billing": (
            "payment", "charged", "charge", "billing", "invoice",
            "refund", "overcharged", "declined", "transaction",
        ),
        "shipping": (
            "shipping", "shipped", "delivery", "delivered",
            "tracking", "package", "shipment", "arrived",
        ),
        "bug": (
            "crash", "crashes", "error", "bug", "broken",
            "unresponsive", "not working", "server",
            "application", "app", "website", "login",
        ),
    }

    for category in ("bug", "billing", "shipping"):
        matched = [
            keyword
            for keyword in keywords[category]
            if keyword in normalized_text
        ]

        if matched:
            return {
                "category": category,
                "reason": f"Matched keywords: {', '.join(matched)}",
            }

    return {
        "category": "other",
        "reason": "No category-specific keywords matched.",
    }


def check_refund_eligibility(order_id: str) -> dict:
    """Check whether an order qualifies for a refund review."""

    if not isinstance(order_id, str) or not order_id.strip():
        return {
            "found": False,
            "eligible": False,
            "error": "A valid order ID is required.",
        }

    normalized_id = order_id.strip().upper()
    order = ORDERS.get(normalized_id)

    if order is None:
        return {
            "found": False,
            "order_id": normalized_id,
            "eligible": False,
            "reason": "Order not found. Refund eligibility cannot be determined.",
        }

    status = order["status"].lower()
    eligible = status in ("delivered", "cancelled")

    return {
        "found": True,
        "order_id": normalized_id,
        "status": order["status"],
        "eligible": eligible,
        "reason": (
            "Order qualifies for a refund review under the demo policy."
            if eligible
            else "Order status does not qualify for a refund review under the demo policy."
        ),
    }
