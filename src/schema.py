"""OpenAI-compatible tool schemas for OrderDesk."""

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
    },
    {
        "type": "function",
        "function": {
            "name": "classify_ticket_category",
            "description": (
                "Classify a support ticket into billing, shipping, bug, "
                "or other. Use the complete ticket subject and body."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The ticket subject and body.",
                    }
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_refund_eligibility",
            "description": (
                "Check whether an order qualifies for a refund review "
                "under the local demo policy. Always use this tool "
                "before answering refund eligibility questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The customer's order ID.",
                    }
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
]
