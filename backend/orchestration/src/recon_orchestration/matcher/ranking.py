"""Embedding-based ranking of ledger candidates by description similarity."""

from fastembed import TextEmbedding
from recon_common.models import Transaction, LedgerEntry, RankedCandidate

_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


def rank_candidates(
    transaction: Transaction, ledger_entries: list[LedgerEntry], top_k: int = 5
) -> list[RankedCandidate]:
    """Rank ledger entries by description similarity and return the top candidates.

    Produces candidates for a human or the investigator to consider. Never
    use this to decide a match: the return type has no match-verdict field.
    """
    txn_vec = list(_model.embed([transaction.description]))[0]
    led_vecs = list(_model.embed([le.description for le in ledger_entries]))

    def cosine(a, b):
        """Return the cosine similarity between two embedding vectors."""
        import numpy as np
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    scored = [
        RankedCandidate(ledger_entry_id=le.id, similarity_score=cosine(txn_vec, vec))
        for le, vec in zip(ledger_entries, led_vecs)
    ]
    return sorted(scored, key=lambda c: c.similarity_score, reverse=True)[:top_k]
