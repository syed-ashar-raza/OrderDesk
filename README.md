# OrderDesk — Groq Tool-Calling Assistant

A Python AI order-support assistant demonstrating end-to-end LLM function calling with Groq and a local mock order database.

## Features
- Groq API integration using GPT-OSS 120B.
- Function calling with `lookup_order_status`.
- Six fictional sample orders.
- Structured tool arguments and function responses.
- Unknown-order handling without fabricated information.
- Environment-based API key management.
- Automated tests with pytest.

## Architecture
Customer Question ? Groq API ? Function Call ? Python Tool ? Mock Database ? Tool Result ? Final Answer

## Technology Stack
- Python 3.14
- Groq Python SDK
- GPT-OSS 120B
- python-dotenv
- pytest

## Setup

1. Clone the repository.
2. Create a virtual environment:
   `python -m venv .venv`
3. Activate it:
   `.venv\Scripts\Activate.ps1`
4. Install dependencies:
   `python -m pip install -r requirements.txt`
5. Copy `.env.example` to `.env`.
6. Add your Groq API key to `.env`.

Required environment variables:
- `GROQ_API_KEY`
- `GROQ_MODEL=openai/gpt-oss-120b`

## Run
`python -m src.main`

Example question: What's the status of order A123?

## Tests
`python -m pytest -v`

Latest verified result: 7 passed.

## Sample Orders

| Order ID | Customer | Status |
|---|---|---|
| A123 | Ali Khan | Shipped |
| A124 | Sara Ahmed | Processing |
| A125 | Usman Malik | Delivered |
| A126 | Fatima Noor | Cancelled |
| A127 | Hamza Ali | Out for delivery |
| A128 | Ayesha Iqbal | Processing |

All sample records are fictional and stored locally.

## Security
- API keys are stored in `.env`.
- `.env` is excluded from Git.
- `.env.example` contains placeholders only.
- Never commit credentials.

## Validation Status
- Live Groq integration: Passed.
- Known-order lookup: Passed.
- Unknown-order handling: Passed.
- Automated tests: 7 passed.
- Python compilation: Passed.

This project demonstrates a local tool-calling workflow. It is not connected to a real order-management system.
