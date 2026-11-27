import hashlib
import json
import math
import re
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT_DIR / "data" / "policies"
CACHE_FILE = POLICY_DIR / "embedding_cache.json"

EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_URL = "http://localhost:11434/api/embed"

MAX_CHUNK_CHARS = 500
CHUNK_OVERLAP = 80


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split policy text into readable chunks without breaking short rules."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if max_chars < 1:
        raise ValueError("max_chars must be greater than zero")

    units = [line.strip() for line in text.splitlines() if line.strip()]
    chunks = []
    current = ""

    for unit in units:
        if len(unit) > max_chars:
            if current:
                chunks.append(current)
                current = ""

            start = 0
            while start < len(unit):
                end = start + max_chars
                chunks.append(unit[start:end].strip())

                if end >= len(unit):
                    break

                start = end - min(CHUNK_OVERLAP, max_chars - 1)

            continue

        candidate = f"{current}\n{unit}" if current else unit

        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            current = unit

    if current:
        chunks.append(current)

    return chunks


def _chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {"model": EMBEDDING_MODEL, "embeddings": {}}

    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        raise RuntimeError(
            f"Embedding cache is unreadable: {CACHE_FILE}"
        )

    if data.get("model") != EMBEDDING_MODEL:
        return {"model": EMBEDDING_MODEL, "embeddings": {}}

    if not isinstance(data.get("embeddings"), dict):
        raise RuntimeError("Embedding cache has an invalid structure")

    return data


def _save_cache(cache: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = CACHE_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps(cache, indent=2),
        encoding="utf-8",
    )
    temporary_file.replace(CACHE_FILE)


def _request_embeddings(texts: list[str]) -> list[list[float]]:
    payload = json.dumps({
        "model": EMBEDDING_MODEL,
        "input": texts,
    }).encode("utf-8")

    request = Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Could not generate embeddings. Confirm that Ollama is running "
            f"and {EMBEDDING_MODEL} is installed. Details: {exc}"
        ) from exc

    embeddings = data.get("embeddings")

    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise RuntimeError("Ollama returned an invalid embedding response")

    for vector in embeddings:
        if not isinstance(vector, list) or not vector:
            raise RuntimeError("Ollama returned an empty embedding vector")

    return embeddings


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if len(vector_a) != len(vector_b):
        raise ValueError("Embedding dimensions do not match")

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)



_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "can", "could",
    "do", "does", "for", "from", "get", "how", "i", "if", "in",
    "is", "it", "me", "my", "of", "on", "or", "our", "should",
    "the", "their", "they", "this", "to", "what", "when", "where", "which",
    "who", "why", "will", "with", "would", "you", "your",
    "orderdesk", "company", "customers", "customer", "order",
    "cover", "take", "standard", "inconvenience", "please", "tell", "same", "purchase", "investigate", "issue", "reported", "arrived", "yet", "current", "date", "provided", "email", "subject", "body",
    "orders", "policy", "has", "not", "status", "ticket", "id",
}

_SYNONYM_GROUPS = (
    {"charge", "charged", "charges", "charging", "duplicate", "twice"},
    {"damaged", "damage", "defective", "broken"},
    {"shipping", "shipment", "ship", "shipped", "package", "parcel"},
    {"delivery", "delivered", "undelivered"},
    {"refund", "refunded", "refunding"},
    {"escalate", "escalated", "escalation"},
    {"compensation", "compensate", "reimbursement"},
    {"duty", "duties", "customs", "tax", "taxes"},
    {"approval", "approved", "approve"},
    {"return", "returned", "returning"},
)

_SYNONYM_LOOKUP = {
    word: group
    for group in _SYNONYM_GROUPS
    for word in group
}


def _query_concepts(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", text.lower().replace("'s", ""))
    concepts = set()

    for word in words:
        if word in _STOP_WORDS:
            continue

        group = _SYNONYM_LOOKUP.get(word)
        concepts.add(sorted(group)[0] if group else word)

    return concepts


def _lexical_evidence(query: str, content: str) -> list[str]:
    query_concepts = _query_concepts(query)
    content_concepts = _query_concepts(content)

    return sorted(query_concepts & content_concepts)


def search_policy_docs(query: str, top_k: int = 3) -> dict:
    """Retrieve policy chunks ranked by cosine similarity."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError("top_k must be a positive integer")

    if not POLICY_DIR.exists():
        return {
            "found": False,
            "query": query,
            "results": [],
            "message": "Policy directory does not exist.",
        }

    documents = []

    for file_path in sorted(POLICY_DIR.glob("*.txt")):
        content = file_path.read_text(encoding="utf-8-sig")
        for index, chunk in enumerate(chunk_text(content)):
            documents.append({
                "source": file_path.name,
                "chunk_index": index,
                "content": chunk,
                "hash": _chunk_hash(chunk),
            })

    if not documents:
        return {
            "found": False,
            "query": query,
            "results": [],
            "message": "No policy documents were found.",
        }

    cache = _load_cache()
    embeddings_cache = cache["embeddings"]

    missing = [
        document for document in documents
        if document["hash"] not in embeddings_cache
    ]

    cache_hits = len(documents) - len(missing)

    if missing:
        new_vectors = _request_embeddings(
            [document["content"] for document in missing]
        )

        for document, vector in zip(missing, new_vectors):
            embeddings_cache[document["hash"]] = vector

        _save_cache(cache)

    query_vector = _request_embeddings([query])[0]

    results = []

    for document in documents:
        vector = embeddings_cache[document["hash"]]

        similarity = _cosine_similarity(query_vector, vector)
        lexical_matches = _lexical_evidence(
            query, document["content"]
        )

        if not lexical_matches:
            continue

        query_concepts = _query_concepts(query)

        concept_weights = {
            "broken": 3.0,
            "charge": 2.0,
            "refund": 2.0,
            "customs": 2.0,
            "compensation": 2.0,
            "escalate": 2.0,
        }

        matched_weight = sum(
            concept_weights.get(term, 1.0)
            for term in lexical_matches
        )
        total_weight = sum(
            concept_weights.get(term, 1.0)
            for term in query_concepts
        )

        lexical_score = matched_weight / max(total_weight, 1.0)

        # Reject chunks supported only by weak keyword overlap.
        if lexical_score < 0.35:
            continue

        query_terms = set(
            re.findall(r"[a-z]+", query.lower().replace("'s", ""))
        ) - _STOP_WORDS

        content_terms = set(
            re.findall(
                r"[a-z]+",
                document["content"].lower().replace("'s", ""),
            )
        ) - _STOP_WORDS

        exact_matches = query_terms & content_terms
        exact_match_bonus = min(len(exact_matches), 3) * 0.08

        relevance_score = (
            similarity
            + (0.15 * lexical_score)
            + exact_match_bonus
        )

        results.append({
            "source": document["source"],
            "chunk_id": document["hash"][:12],
            "chunk_index": document["chunk_index"],
            "content": document["content"],
            "similarity": round(similarity, 6),
            "lexical_matches": lexical_matches,
            "relevance_score": round(relevance_score, 6),
        })

    results.sort(
        key=lambda item: item["relevance_score"],
        reverse=True,
    )

    return {
        "found": bool(results),
        "query": query,
        "results": results[:top_k],
        "message": (
            "Relevant policy evidence retrieved."
            if results else
            "No sufficiently relevant policy evidence was found."
        ),
        "cache": {
            "total_chunks": len(documents),
            "embedded_chunks": len(missing),
            "cache_hits": cache_hits,
            "model": EMBEDDING_MODEL,
        },
    }
