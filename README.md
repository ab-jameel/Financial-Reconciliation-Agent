# Financial Reconciliation Agent

A LangGraph-based agent that automates bank-to-ledger reconciliation: it matches
bank transactions against internal ledger entries, investigates exceptions with
an LLM-powered agent, and writes corrections to a mock ERP — but only after
human approval, enforced at a database-level boundary that is independent of
the agent itself.


## Results (held-out benchmark, never used for tuning)

| Metric | Naive baseline | Agent |
|---|---|---|
| F1 | 0.436 | **0.909** |
| Correct disposition rate | — | **0.808** |
| Manual review count (of 100) | 62 | **52** |
| % fewer manual touches | — | **16.1%** |
| Avg cost / transaction | — | $0.0046 |
| Avg latency / investigated case | — | ~24s |

Generator version `v4`, seeds `20260828` (tuning) / `20260829` (held-out). Every
number above is measured on data the system was never tuned against — not a
"targeting" estimate. Several earlier versions of this table were quietly
wrong, for reasons that turned out to matter more than the numbers themselves.

## Architecture

- **Deterministic matcher** — exact amount + currency + date + reference key
  decides what auto-clears. Nothing fuzzy can flip a transaction to "matched."
- **Embedding ranking layer** — surfaces fuzzy candidates for a human or the
  investigator to consider. The type it returns has no field capable of
  expressing a match verdict, so it is structurally incapable of auto-clearing
  anything, however high the similarity score.
- **Reconciliation safety layer** — even a transaction that passes the
  deterministic key must also pass an invoice-existence check and an atomic
  "not already claimed by another transaction" check before it can auto-clear.
  Closes a real gap where duplicate transactions and missing-invoice cases
  could otherwise silently slip through.
- **LangGraph orchestration** — Postgres-backed checkpointing (one thread per
  case), `interrupt()`-based human review with the interrupt payload itself
  persisted in ordinary state, a rejection → re-investigation cycle capped at
  2 rounds before escalation.
- **Investigator** — ReWOO-planned evidence gathering, a ReAct tool loop
  (policy retrieval, related-transaction search, date/amount deltas, invoice
  checks), and a Reflection step that re-checks the tentative conclusion
  against the policy version actually in effect on the transaction's date.
- **Write-back safety layer** — the mock ERP runs as its own process with its
  own least-privileged database role. RSA-signed, case/amount/entity-scoped,
  short-lived approval tokens are verified *inside* the ERP itself, fully
  independent of the agent — the ERP has no private key on its side of the
  boundary and cannot mint its own valid token. Idempotency keys prevent
  replay. The audit log is hash-chained, and the app's own runtime database
  role has no UPDATE/DELETE grant on it — enforced by Postgres itself, not
  application code.
- **PDF statement ingestion** — extracts transactions from real bank statement
  PDFs: text-based via a direct LLM extraction pass, scanned/image-only via
  page rasterization plus a vision-capable LLM call. Every extracted
  transaction flows through the exact same pipeline above — nothing about
  this input source bypasses any existing safety layer.

Four independent layers guarantee zero unauthorized postings. Each one is
proven by a test that actually tries to defeat it, not assumed to hold.

## What's mocked vs. real

- **Real**: LangGraph orchestration, Postgres persistence, Qdrant retrieval,
  the actual LLM calls, the token/audit/idempotency mechanics, the PDF
  extraction pipeline (both text and vision paths).
- **Mocked**: the ERP (a FastAPI stand-in, not a real accounting system), and
  all transaction/ledger/invoice/policy data (synthetic, seeded, versioned).


## Repo structure

```
backend/
  common/            # shared Pydantic models
  orchestration/      # LangGraph app, investigator, matcher, PDF ingestion, API
  erp/                # mock ERP — its own process, its own DB role
data/                 # synthetic generator, policy corpus, generated splits
frontend/             # Next.js review queue, dashboard, audit log viewer
tests/
scripts/              # eval, migration, and one-off utility scripts
```

## Running it locally

1. `docker compose up -d` (Postgres + Qdrant)
2. `uv sync --all-packages`
3. `uv run python scripts/init_db.py`
   `uv run python scripts/init_erp_db.py`
   `uv run python scripts/setup_erp_db_grants.py`
   `uv run python scripts/migrate_add_production_support.py`
4. `uv run python scripts/generate_keypair.py`
5. `uv run python data/generate_synthetic_data.py`
   `uv run python data/load_to_postgres.py`
   `uv run python data/load_policies_to_qdrant.py`
6. `uv run pytest -v` — should be fully green
7. Three terminals:
   - `uv run uvicorn recon_erp.app:app --port 8001 --app-dir backend/erp/src`
   - `uv run uvicorn recon_orchestration.api.app:app --port 8000 --reload --app-dir backend/orchestration/src`
   - `npm run dev` (inside `frontend/`)
