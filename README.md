# OrderDesk — AI-Powered Support Triage Agent

A Python customer-support assistant built with Groq function calling. Demonstrates order lookup, ticket classification, refund eligibility checks, and multi-turn tool orchestration.

## Features

### Week 1 — Order Support
- Groq API integration using GPT-OSS 120B.
- `lookup_order_status` function.
- Six fictional sample orders.
- Unknown-order handling.
- Environment-based API key management.

### Week 2 — Multi-Tool Ticket Triage
- Processes 12 fictional support tickets.
- Classifies tickets: `billing`, `shipping`, `bug`, or `other`.
- Looks up order status.
- Checks refund eligibility.
- Supports multiple tool calls across conversation rounds.
- Configurable five-round safety limit.
- Logs tool calls and results.
- Generates deterministic customer replies from verified data.
- Includes regression tests for unsupported customer-facing claims.

## Architecture

1. Load a ticket from `data/tickets.json`.
2. Send the ticket and system prompt to the Groq model.
3. The model selects and calls Python tools.
4. Python executes the tools and returns results.
5. The conversation continues until a final response or safety limit.
6. Extract the category and generate a deterministic customer reply.
7. Print and save results to `data/triage_results.json`.

## Response Safety

The LLM handles tool selection and orchestration. Python generates customer-facing replies through `src/agent/replies.py`.

This prevents unsupported claims about:
- Refund approval or payment processing.
- Tracking information and delivery guarantees.
- Engineering-team notifications.
- Actions not confirmed by available tools.

## Tools

| Tool | Purpose |
|---|---|
| `lookup_order_status(order_id)` | Retrieves recorded order status and estimated delivery. |
| `classify_ticket_category(text)` | Classifies a support ticket. |
| `check_refund_eligibility(order_id)` | Checks refund-review eligibility. |

### Demonstration Refund Policy

Orders with `Delivered` or `Cancelled` status qualify for refund review under the local demonstration policy. Eligibility does not mean a refund was approved or processed.

## Project Structure

    OrderDesk/
    ├── data/
    │   ├── tickets.json
    │   └── triage_results.json
    ├── src/
    │   ├── agent/
    │   │   ├── __init__.py
    │   │   ├── prompts.py
    │   │   ├── replies.py
    │   │   └── triage_agent.py
    │   ├── __init__.py
    │   ├── database.py
    │   ├── main.py
    │   ├── run_triage.py
    │   ├── schema.py
    │   └── tools.py
    ├── tests/
    │   └── test_tools.py
    ├── .env.example
    ├── .gitignore
    ├── README.md
    └── requirements.txt

## Technology Stack

- Python 3.14
- Groq Python SDK
- GPT-OSS 120B
- Groq function calling
- python-dotenv
- pytest

## Setup

1. Clone: `git clone https://github.com/syed-ashar-raza/OrderDesk.git`
2. Enter the project: `cd OrderDesk`
3. Create environment: `python -m venv .venv`
4. Activate: `.\.venv\Scripts\Activate.ps1`
5. Install: `python -m pip install -r requirements.txt`
6. Copy `.env.example` to `.env`.
7. Add your Groq API key.

Required environment variables:

- `GROQ_API_KEY`
- `GROQ_MODEL=openai/gpt-oss-120b`

## Run

Week 1 — Order assistant:

`python -m src.main`

Week 2 — Process all support tickets:

`python -m src.run_triage`

The triage runner prints ticket categories, tool calls, and customer replies. It saves results to `data/triage_results.json`.

## Tests

Run: `python -m pytest -v`

Latest verified result: **28 passed**.

Coverage includes:
- Order lookup.
- Ticket classification.
- Refund eligibility.
- Tool schemas.
- Multi-turn orchestration.
- Safety-cap behavior.
- Category extraction and fallback.
- Deterministic customer-reply guardrails.

## Sample Dataset

Six fictional order records and twelve fictional support tickets. Scenarios include refunds, delivery delays, order-status questions, login errors, and website malfunctions.

All sample data is stored locally.

## Security and Limitations

- API keys are stored in `.env`.
- `.env` is excluded from Git.
- `.env.example` contains placeholders only.
- Never commit credentials.
- The database and tickets are fictional local data.
- Refund eligibility uses a simplified demonstration policy.
- The project does not process real refunds or modify real orders.
- It is not connected to a production support platform.

## Validation Status

| Validation | Result |
|---|---|
| Groq integration | Passed |
| Order lookup | Passed |
| Ticket classification | Passed |
| Refund eligibility | Passed |
| Multi-turn tool calling | Passed |
| Safety-cap tests | Passed |
| Reply regression tests | Passed |
| Automated tests | 28 passed |
| Previous full live triage | 12 tickets completed |
| Targeted live verification | Passed |

---

Built as a practical demonstration of Python tool integration, LLM orchestration, multi-tool workflows, and evidence-based AI response design.
