"""Tests for OrderDesk tools, schemas, and TicketPilot orchestration."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.tools import (
    lookup_order_status,
    classify_ticket_category,
    check_refund_eligibility,
)


# WEEK 1: ORDER LOOKUP

def test_known_order_returns_correct_status():
    result = lookup_order_status("A123")
    assert result["found"] is True
    assert result["status"] == "Shipped"
    assert result["customer"] == "Ali Khan"


def test_unknown_order_returns_not_found():
    result = lookup_order_status("X999")
    assert result["found"] is False
    assert result["error"] == "Order not found."


def test_lowercase_order_id_is_supported():
    result = lookup_order_status("a123")
    assert result["found"] is True
    assert result["order_id"] == "A123"


def test_empty_order_id_is_rejected():
    result = lookup_order_status(" ")
    assert result["found"] is False
    assert "error" in result


def test_all_six_sample_orders_exist():
    for order_id in ("A123", "A124", "A125", "A126", "A127", "A128"):
        assert lookup_order_status(order_id)["found"] is True


def test_non_string_order_id_is_rejected():
    result = lookup_order_status(None)
    assert result["found"] is False
    assert result["error"] == "A valid order ID is required."


# WEEK 2: TICKET CLASSIFICATION

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("I was charged twice for my purchase", "billing"),
        ("My package delivery is delayed", "shipping"),
        ("The mobile application crashes", "bug"),
        ("I need help with my account", "other"),
    ],
)
def test_ticket_classification(text, expected):
    assert classify_ticket_category(text)["category"] == expected


def test_empty_ticket_text_returns_other():
    assert classify_ticket_category("")["category"] == "other"


# WEEK 2: REFUND ELIGIBILITY

@pytest.mark.parametrize("order_id", ["A125", "A126"])
def test_delivered_and_cancelled_orders_qualify_for_review(order_id):
    result = check_refund_eligibility(order_id)
    assert result["found"] is True
    assert result["eligible"] is True


@pytest.mark.parametrize("order_id", ["A123", "A124", "A127", "A128"])
def test_other_order_statuses_do_not_qualify(order_id):
    result = check_refund_eligibility(order_id)
    assert result["found"] is True
    assert result["eligible"] is False


def test_unknown_order_refund_eligibility():
    result = check_refund_eligibility("X999")
    assert result["found"] is False
    assert result["eligible"] is False


# WEEK 2: GROQ TOOL SCHEMAS

def test_groq_tool_schemas_are_valid():
    from src.schema import ORDER_TOOLS

    assert len(ORDER_TOOLS) == 4

    expected = {
        "lookup_order_status": "order_id",
        "classify_ticket_category": "text",
        "check_refund_eligibility": "order_id",
        "search_policy_docs": "query",
    }

    for tool in ORDER_TOOLS:
        assert tool["type"] == "function"

        function = tool["function"]
        name = function["name"]

        assert name in expected
        assert function["description"]

        parameters = function["parameters"]
        assert parameters["type"] == "object"
        assert expected[name] in parameters["properties"]
        assert parameters["required"] == [expected[name]]
        assert parameters["additionalProperties"] is False


# WEEK 2: MULTI-ROUND ORCHESTRATION

def make_tool_response(tool_name, arguments, call_id="call_1"):
    call = SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(
            name=tool_name,
            arguments=__import__("json").dumps(arguments),
        ),
        model_dump=lambda exclude_none=True: {
            "id": call_id,
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": __import__("json").dumps(arguments),
            },
        },
    )

    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[call],
                )
            )
        ]
    )


def make_final_response(content):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                    tool_calls=None,
                )
            )
        ]
    )


def make_mock_client(responses):
    client = MagicMock()

    client.chat.completions.create.side_effect = responses

    return client


def test_agent_supports_multiple_tool_rounds():
    from src.agent.triage_agent import run_ticket_triage

    client = make_mock_client([
        make_tool_response(
            "lookup_order_status",
            {"order_id": "A125"},
            "call_1",
        ),
        make_tool_response(
            "check_refund_eligibility",
            {"order_id": "A125"},
            "call_2",
        ),
        make_final_response(
            "Category: billing\n"
            "Tools used: lookup_order_status, check_refund_eligibility\n"
            "Reply: Your order qualifies for a refund review."
        ),
        make_final_response(
            "Category: billing\\n"
            "Policy evidence reviewed. Final response ready."
        ),
    ])

    ticket = {
        "ticket_id": "TEST001",
        "subject": "Refund request",
        "body": "Please check my refund for order A125.",
        "customer_email": "test@example.com",
        "order_id": "A125",
    }

    result = run_ticket_triage(ticket, client)

    assert result["status"] == "completed"
    assert result["tool_rounds"] == 3
    assert len(result["tool_calls"]) == 3
    assert result["category"] == "billing"
    assert result["tool_calls"][0]["tool"] == "lookup_order_status"
    assert result["tool_calls"][1]["tool"] == "check_refund_eligibility"
    assert result["tool_calls"][2]["tool"] == "search_policy_docs"
    assert "refund_policy.txt" in result["reply"]


def test_agent_enforces_tool_round_safety_cap():
    from src.agent.triage_agent import run_ticket_triage

    client = make_mock_client([
        make_tool_response(
            "classify_ticket_category",
            {"text": "Payment issue"},
            "call_1",
        ),
        make_tool_response(
            "classify_ticket_category",
            {"text": "Payment issue"},
            "call_2",
        ),
    ])

    ticket = {
        "ticket_id": "TEST002",
        "subject": "Payment issue",
        "body": "My payment failed.",
        "order_id": None,
    }

    result = run_ticket_triage(
        ticket,
        client,
        max_tool_rounds=1,
    )

    assert result["status"] == "safety_cap_reached"
    assert result["tool_rounds"] == 1
    assert len(result["tool_calls"]) == 1


def test_agent_rejects_invalid_safety_cap():
    from src.agent.triage_agent import run_ticket_triage

    with pytest.raises(ValueError):
        run_ticket_triage({}, MagicMock(), max_tool_rounds=0)


def test_technical_issue_takes_priority_over_shipping_keyword():
    text = "The checkout button becomes unresponsive after I update my delivery address."
    result = classify_ticket_category(text)

    assert result["category"] == "bug"
    assert "unresponsive" in result["reason"]

from src.agent.triage_agent import _extract_category, _category_from_tool_calls


def test_extract_category_from_markdown_response():
    response = "**Suggested Category:** Billing – payment issue"
    assert _extract_category(response) == "billing"


def test_category_fallback_uses_classification_tool():
    tool_calls = [
        {
            "tool": "classify_ticket_category",
            "result": {"category": "bug"},
        }
    ]
    assert _category_from_tool_calls(tool_calls) == "bug"

# WEEK 2: DETERMINISTIC CUSTOMER REPLY GUARDRAILS

from src.agent.replies import build_customer_reply


def test_refund_reply_does_not_promise_review_or_payment():
    ticket = {"order_id": "A125"}
    calls = [
        {
            "tool": "check_refund_eligibility",
            "result": {
                "found": True,
                "eligible": True,
                "order_id": "A125",
                "status": "Delivered",
            },
        }
    ]

    reply = build_customer_reply(ticket, calls)

    assert "qualifies for a refund review" in reply
    assert "has started" in reply
    assert "refund has been approved" in reply
    assert "refund-processing status" in reply
    assert "will be issued" not in reply


def test_shipping_reply_does_not_invent_tracking_or_guarantees():
    ticket = {"order_id": "A124"}
    calls = [
        {
            "tool": "lookup_order_status",
            "result": {
                "found": True,
                "order_id": "A124",
                "status": "Processing",
                "estimated_delivery": "2026-11-22",
                "customer": "Sara Ahmed",
            },
        }
    ]

    reply = build_customer_reply(ticket, calls)

    assert "Processing" in reply
    assert "November 22, 2026" in reply
    assert "does not confirm dispatch" in reply
    assert "tracking information" in reply
    assert "guaranteed delivery date" in reply


def test_bug_reply_does_not_claim_engineering_notification():
    ticket = {"order_id": None}
    calls = [
        {
            "tool": "classify_ticket_category",
            "result": {"category": "bug"},
        }
    ]

    reply = build_customer_reply(ticket, calls)

    assert "technical issue" in reply
    assert "do not confirm whether an engineering team has been notified" in reply
    assert "engineering team has been notified and is working" not in reply
