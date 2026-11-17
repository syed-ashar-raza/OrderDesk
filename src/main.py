"""OrderDesk: Groq-powered order status assistant."""

import json
import os

from dotenv import load_dotenv
from groq import Groq

from src.schema import ORDER_TOOLS
from src.tools import lookup_order_status


load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

if not API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing from .env")

client = Groq(api_key=API_KEY)


def run_order_assistant(question: str) -> str:
    """Run a complete Groq function-calling interaction."""

    messages = [
        {
            "role": "system",
            "content": (
                "You are OrderDesk, an order status assistant. "
                "Use lookup_order_status for every order-status question. "
                "Never invent order details or delivery dates. "
                "Only report information returned by the tool. "
                "If an order is not found, clearly say so."
            ),
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=ORDER_TOOLS,
        tool_choice="auto",
    )

    print("\n--- RAW MODEL RESPONSE ---")
    print(response.model_dump_json(indent=2))

    assistant_message = response.choices[0].message
    tool_calls = assistant_message.tool_calls

    if not tool_calls:
        answer = assistant_message.content or (
            "The model did not request an order lookup."
        )
        print("\n--- FINAL ANSWER ---")
        print(answer)
        return answer

    messages.append(
        {
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [
                call.model_dump(exclude_none=True)
                for call in tool_calls
            ],
        }
    )

    for call in tool_calls:
        function_name = call.function.name

        if function_name != "lookup_order_status":
            raise ValueError(f"Unexpected function: {function_name}")

        arguments = json.loads(call.function.arguments or "{}")

        if not isinstance(arguments, dict):
            raise ValueError("Function arguments must be a JSON object.")

        print("\n--- FUNCTION CALL ---")
        print("Name:", function_name)
        print("Call ID:", call.id)
        print("Arguments:", arguments)

        result = lookup_order_status(**arguments)

        print("\n--- FUNCTION RESULT ---")
        print(json.dumps(result, indent=2))

        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            }
        )

    final_response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    final_answer = (
        final_response.choices[0].message.content
        or "No final answer was generated."
    )

    print("\n--- FINAL ANSWER ---")
    print(final_answer)

    return final_answer


if __name__ == "__main__":
    question = input("Ask OrderDesk about an order: ").strip()

    if not question:
        raise SystemExit("Please enter an order question.")

    run_order_assistant(question)