"""Application tools available to the LLM."""

from src.database import ORDERS


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
