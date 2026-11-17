"""Tests for the OrderDesk order lookup tool and Groq schema."""

from src.tools import lookup_order_status


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


def test_groq_tool_schema_is_valid():
    from src.schema import ORDER_TOOLS

    assert len(ORDER_TOOLS) == 1

    tool = ORDER_TOOLS[0]

    assert tool["type"] == "function"

    function = tool["function"]

    assert function["name"] == "lookup_order_status"
    assert isinstance(function["description"], str)
    assert function["description"]

    parameters = function["parameters"]

    assert parameters["type"] == "object"
    assert "order_id" in parameters["properties"]
    assert parameters["properties"]["order_id"]["type"] == "string"
    assert parameters["required"] == ["order_id"]
    assert parameters["additionalProperties"] is False


def test_non_string_order_id_is_rejected():
    result = lookup_order_status(None)

    assert result["found"] is False
    assert result["error"] == "A valid order ID is required."