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

    {
        "type": "function",
        "function": {
            "name": "search_policy_docs",
            "description": (
                "Search the OrderDesk policy knowledge base using semantic "
                "similarity. MUST be called before drafting replies involving "
                "refunds, returns, shipping deadlines, timelines, or policy rules. "
                "Use retrieved policy content as evidence and never invent rules."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The customer's policy-related question or ticket context."
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of policy chunks to retrieve.",
                        "minimum": 1,
                        "maximum": 5
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },

]
