# OrderDesk - AI-Powered Support Triage Agent

OrderDesk is a Python-based AI customer-support triage system built with Groq function calling. It demonstrates multi-tool orchestration, policy-grounded retrieval, evidence-based customer replies, and deterministic response guardrails.

## Features

### Week 1 - Order Support
- Groq API integration using GPT-OSS 120B.
- Order status lookup.
- Six fictional sample orders.
- Unknown-order handling.
- Environment-based API key management.

### Week 2 - Multi-Tool Ticket Triage
- Processes fictional support tickets.
- Classifies tickets as billing, shipping, bug, or other.
- Looks up order status.
- Checks refund eligibility.
- Supports multi-turn tool calling.
- Enforces a configurable five-round safety limit.
- Logs tool calls and results.
- Generates deterministic customer replies from verified data.

### Week 3 - Retrieval-Augmented Generation (RAG)
- Four policy documents covering refunds, shipping, billing, and escalation.
- Text chunking with overlap.
- Local embeddings generated using Ollama and nomic-embed-text.
- SHA-256 content hashes for embedding-cache keys.
- Persistent JSON embedding cache.
- Cosine-similarity-based semantic retrieval.
- Lexical matching and synonym normalization.
- search_policy_docs exposed as an agent tool.
- Policy retrieval enforced before policy-dependent replies.
- Retrieved source filenames, chunk identifiers, and evidence included in customer replies.
- Honest abstention when available policy documents do not support an answer.

## Architecture

1. Load a support ticket from the local dataset.
2. Send the ticket and system prompt to the Groq model.
3. The model selects and calls available Python tools.
4. Python executes the requested tools and returns their results.
5. Policy-dependent tickets trigger policy retrieval before a customer reply is generated.
6. The retriever loads policy documents, chunks their contents, and obtains embeddings.
7. Previously generated embeddings are reused from the JSON cache.
8. Relevant policy chunks are ranked using semantic and lexical evidence.
9. Python generates a deterministic customer reply using verified tool results.
10. Retrieved policy evidence is attached to the triage result.

## RAG Implementation

### Policy knowledge base

Policy documents are stored in `data/policies/`:

| Document | Coverage |
|---|---|
| refund_policy.txt | Refund review eligibility, conditions, and processing |
| shipping_policy.txt | Processing, delivery estimates, and tracking |
| billing_policy.txt | Duplicate charges and payment authorizations |
| escalation_policy.txt | Issues requiring human support review |

### Retrieval pipeline

The retriever in `src/policy_retriever.py`:

- Splits policy text into chunks while preserving content.
- Generates embeddings using the local Ollama embedding model.
- Uses SHA-256 hashes to identify reusable chunk embeddings.
- Stores cached vectors in `data/policies/embedding_cache.json`.
- Calculates cosine similarity between query and document embeddings.
- Combines semantic similarity with lexical evidence.
- Returns the most relevant policy chunks.

The query embedding is generated at search time. Document embeddings are cached and reused when their content and embedding model remain unchanged.

### Policy-grounded replies

The agent exposes `search_policy_docs` as a callable tool.

When a ticket concerns refunds, returns, shipping deadlines, billing rules, or other policy requirements, retrieval is required before generating the final reply.

Customer-facing responses include retrieved source documents and chunk evidence. When the available documents do not establish a policy, the system communicates that limitation instead of inventing an answer.

## Response Safety

Customer-facing replies are generated deterministically in `src/agent/replies.py`.

The system avoids unsupported claims about:

- Refund approval or payment processing.
- Payment reversals.
- Tracking information and guaranteed delivery.
- Completed billing referrals or escalations.
- Engineering-team notifications.
- Policy rules not supported by retrieved evidence.

## Technology Stack

- Python 3.14
- Groq Python SDK
- GPT-OSS 120B
- Groq function calling
- Ollama
- nomic-embed-text
- JSON embedding cache
- NumPy-compatible vector operations implemented in Python
- python-dotenv
- pytest

## Setup

1. Clone the repository:

   `git clone https://github.com/syed-ashar-raza/OrderDesk.git`

2. Enter the project:

   `cd OrderDesk`

3. Create a virtual environment:

   `python -m venv .venv`

4. Activate it:

   `.\.venv\Scripts\Activate.ps1`

5. Install dependencies:

   `python -m pip install -r requirements.txt`

6. Copy `.env.example` to `.env`.

7. Add your Groq API key and model:

   `GROQ_API_KEY=your_api_key`

   `GROQ_MODEL=openai/gpt-oss-120b`

8. Install and start Ollama.

9. Download the embedding model:

   `ollama pull nomic-embed-text`

The embedding service must be available at the default local Ollama API endpoint.

## Run

Week 1 - Order assistant:

`python -m src.main`

Week 2 and Week 3 - Process support tickets:

`python -m src.run_triage`

The triage runner displays ticket categories, tool calls, policy retrieval results, and customer replies. Results are saved to `data/triage_results.json`.

## Tests

Run the full test suite:

`python -m pytest -v`

Latest verified result: **39 passed**.

Coverage includes:

- Order lookup and ticket classification.
- Refund eligibility.
- Tool schemas and multi-tool orchestration.
- Safety-cap behavior.
- Deterministic customer-reply guardrails.
- Text chunking and content preservation.
- Cosine similarity.
- Lexical matching and synonym normalization.
- Embedding-cache reuse.
- UTF-8 BOM handling.

## Project Structure

    OrderDesk/
    |-- data/
    |   |-- policies/
    |   |   |-- refund_policy.txt
    |   |   |-- shipping_policy.txt
    |   |   |-- billing_policy.txt
    |   |   |-- escalation_policy.txt
    |   |   |-- embedding_cache.json
    |   |-- tickets.json
    |-- src/
    |   |-- agent/
    |   |   |-- prompts.py
    |   |   |-- replies.py
    |   |   |-- triage_agent.py
    |   |-- database.py
    |   |-- main.py
    |   |-- run_triage.py
    |   |-- schema.py
    |   |-- tools.py
    |   |-- policy_retriever.py
    |-- tests/
    |   |-- test_tools.py
    |   |-- test_policy_retriever.py
    |-- .env.example
    |-- .gitignore
    |-- README.md
    |-- requirements.txt

## Security and Limitations

- API keys are stored in `.env`.
- `.env` is excluded from Git.
- `.env.example` contains placeholders only.
- Never commit credentials.
- Sample orders, tickets, and policy documents are fictional.
- The policy knowledge base is for demonstration purposes only.
- The system does not process real refunds, reverse payments, or modify real orders.
- The project is not connected to a production support platform.
- Policy retrieval does not guarantee that every relevant document will be retrieved.

## Validation Status

| Validation | Result |
|---|---|
| Groq integration | Previously verified |
| Order lookup | Previously verified |
| Ticket classification | Previously verified |
| Refund eligibility | Previously verified |
| Multi-tool orchestration | Previously verified |
| Policy retrieval | Verified |
| Embedding-cache reuse | Verified |
| Unsupported-policy abstention | Verified |
| Deterministic policy-grounded replies | Verified |
| Automated tests | 39 passed |

---

Built as a practical demonstration of Python tool integration, LLM orchestration, retrieval-augmented generation, policy-grounded responses, and AI response safety.
