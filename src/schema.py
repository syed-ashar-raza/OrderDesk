"""OpenAI-compatible tool schema for OrderDesk."""

ORDER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order_status",
            "description": (
                "Retrieve the status and estimated delivery date "
                "of a customer order using its order ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID, for example A123.",
                    }
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    }
]