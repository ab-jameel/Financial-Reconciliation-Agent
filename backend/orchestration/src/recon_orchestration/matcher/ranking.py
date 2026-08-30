# backend/orchestration/src/recon_orchestration/matcher/ranking.py
from fastembed import TextEmbedding
from recon_common.models import Transaction, LedgerEntry, RankedCandidate

_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


def rank_candidates(
    transaction: Transaction, ledger_entries: list[LedgerEntry], top_k: int = 5
) -> list[RankedCandidate]:
    """Ranks ledger entries by description similarity. Returns candidates for a
    human or the investigator to consider. NEVER call this to decide a match —
    the return type has no match-verdict field, by design."""
    txn_vec = list(_model.embed([transaction.description]))[0]
    led_vecs = list(_model.embed([le.description for le in ledger_entries]))

    def cosine(a, b):
        import numpy as np
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    scored = [
        RankedCandidate(ledger_entry_id=le.id, similarity_score=cosine(txn_vec, vec))
        for le, vec in zip(ledger_entries, led_vecs)
    ]
    return sorted(scored, key=lambda c: c.similarity_score, reverse=True)[:top_k]