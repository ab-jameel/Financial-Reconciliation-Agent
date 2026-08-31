# backend/orchestration/src/recon_orchestration/investigator/policy_store.py
from datetime import date as Date
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from fastembed import TextEmbedding

COLLECTION = "policies"
_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
_client = QdrantClient(url="http://localhost:6333")


class NoPolicyInEffectError(Exception):
    """Raised when the transaction date predates every known version of the
    matched policy — applying any version retroactively would be wrong, so
    this must surface as an explicit gap, never silently fall back to latest."""


def retrieve_policy(query: str, transaction_date: Date) -> dict:
    # Step 1: semantic search identifies the TOPIC only.
    query_vec = list(_model.embed([query]))[0]
    response = _client.query_points(
        collection_name=COLLECTION,
        query=query_vec.tolist(),
        limit=5,
    )
    hits = response.points
    if not hits:
        raise NoPolicyInEffectError(f"No policy found matching query: {query!r}")
    policy_name = hits[0].payload["policy_name"]

    # Step 2: fetch ALL versions/chunks of that policy by exact filter,
    # independent of their embedding scores.
    all_chunks, _ = _client.scroll(
        collection_name=COLLECTION,
        scroll_filter=Filter(must=[FieldCondition(key="policy_name", match=MatchValue(value=policy_name))]),
        limit=1000,
    )
    versions_seen = {c.payload["version"]: Date.fromisoformat(c.payload["effective_date"]) for c in all_chunks}

    # Step 3: pick the version in effect on transaction_date — max effective_date <= transaction_date.
    eligible = {v: eff for v, eff in versions_seen.items() if eff <= transaction_date}
    if not eligible:
        raise NoPolicyInEffectError(
            f"Transaction date {transaction_date} predates every known version of "
            f"policy '{policy_name}' (earliest: {min(versions_seen.values())})."
        )
    correct_version = max(eligible, key=lambda v: eligible[v])

    version_chunks = sorted(
        (c for c in all_chunks if c.payload["version"] == correct_version),
        key=lambda c: c.payload["chunk_index"],
    )
    return {
        "policy_name": policy_name,
        "version": correct_version,
        "effective_date": eligible[correct_version].isoformat(),
        "text": "\n\n".join(c.payload["text"] for c in version_chunks),
    }