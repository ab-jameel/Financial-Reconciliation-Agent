# backend/orchestration/src/recon_orchestration/investigator/loop.py
import asyncio
import json
import os
from datetime import date as Date
from decimal import Decimal
import litellm

from recon_common.models import ExceptionType
from recon_orchestration.investigator.tracing import extract_cost
from recon_orchestration.investigator.policy_store import retrieve_policy, NoPolicyInEffectError
from recon_orchestration.investigator.tools import (
    search_related_transactions, compute_date_delta, compute_amount_delta, TOOL_SCHEMAS, check_invoice_exists
)
from recon_orchestration.utils.json_extract import extract_json_object as _extract_json_object

MODEL = os.environ.get("LLM_MODEL")
MAX_REACT_ITERATIONS = 6  # safety cap: force a stop rather than loop indefinitely on a confused model
VALID_DISPOSITIONS = [e.value for e in ExceptionType]

"""
def _extract_json_object(text: str) -> dict:
    Models often prepend reasoning prose before the final JSON answer,
    even when told not to. Try the whole string first (fast path); if that
    fails, scan for the LAST balanced {...} block in the text and parse
    that instead of discarding an otherwise-correct answer.
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    candidates = []
    for start in range(len(text)):
        if text[start] != "{":
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start:i + 1])
                    break
    for candidate in reversed(candidates):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("no valid JSON object found in text", text, 0)
"""
    
def _dispatch_tool(name: str, args: dict, transaction: dict) -> dict:
    if name == "retrieve_policy":
        try:
            return retrieve_policy(args["query"], Date.fromisoformat(transaction["date"]))
        except NoPolicyInEffectError as e:
            return {"error": str(e)}
    if name == "search_related_transactions":
        return {"related": search_related_transactions(
            args["reference"], transaction["dataset_split"], transaction["id"],
        )}
    if name == "compute_date_delta":
        return {"days": compute_date_delta(Date.fromisoformat(args["date_a"]), Date.fromisoformat(args["date_b"]))}
    if name == "compute_amount_delta":
        return {"delta": str(compute_amount_delta(Decimal(args["amount_a"]), Decimal(args["amount_b"])))}
    if name == "check_invoice_exists":
        return check_invoice_exists(args["invoice_number"], transaction["dataset_split"])
    return {"error": f"unknown tool {name}"}


async def _rewoo_initial_gather(transaction: dict, ledger_candidates: list[dict]) -> dict:
    """Plan the obvious first-round fetches upfront and run them concurrently,
    rather than looping one tool call at a time for information we already
    know we'll need regardless of what the model decides."""
    def _policy(query):
        try:
            return retrieve_policy(query, Date.fromisoformat(transaction["date"]))
        except NoPolicyInEffectError as e:
            return {"error": str(e)}

    unique_invoices = {le.get("invoice_number") for le in ledger_candidates if le.get("invoice_number")}

    materiality, duplicate_policy, settlement_timing, related, *invoice_results = await asyncio.gather(
        asyncio.to_thread(_policy, "materiality threshold"),
        asyncio.to_thread(_policy, "duplicate handling"),
        asyncio.to_thread(_policy, "settlement timing"),
        asyncio.to_thread(search_related_transactions, transaction["reference"], transaction["dataset_split"], transaction["id"]),
        *[asyncio.to_thread(check_invoice_exists, inv, transaction["dataset_split"]) for inv in unique_invoices],
    )
    return {
        "materiality_policy": materiality, "duplicate_policy": duplicate_policy,
        "settlement_timing_policy": settlement_timing, "related_transactions": related,
        "invoice_checks": invoice_results,
    }

DISPOSITION_POLICY_TOPIC = {
    "duplicate": "duplicate handling",
    "date_mismatch": "settlement timing",
    # everything else still maps to the general materiality-threshold policy
}

DISPOSITION_DEFINITIONS = """
Disposition definitions — use the evidence to pick exactly one:
- clean_match: amount, date, currency, and reference all agree; no real discrepancy.
- amount_mismatch: ledger amount differs from transaction amount beyond a trivial rounding/fee variance.
- date_mismatch: ledger date differs from transaction date by more than a few days (check the settlement timing policy).
- currency_issue: ledger entry is recorded in a different currency than the transaction.
- duplicate: this transaction's reference/amount/date matches a ledger entry another transaction appears to have already claimed — check search_related_transactions for evidence, don't assume it.
- missing_invoice: the ledger entry's invoice_number does not exist in invoice records — check the invoice_checks evidence (or call check_invoice_exists directly) before concluding clean_match just because amount/date/currency/reference all agree.
- policy_sensitive: the discrepancy is close enough to a materiality threshold that whether it counts as material depends specifically on which policy version applies. Use this — not clean_match or amount_mismatch — whenever the version determination is the deciding factor, since a human reviewer needs to know the verdict was version-dependent, not just what the verdict was.
"""

async def investigate(transaction: dict, ledger_candidates: list[dict], rejection_reason: str | None) -> dict:
    safe_transaction = {k: v for k, v in transaction.items() if k != "label_exception_type"}
    initial_evidence = await _rewoo_initial_gather(safe_transaction, ledger_candidates)

    system_prompt = (
        "You are investigating a bank-to-ledger reconciliation exception. "
        "Gather evidence using the available tools. Your FINAL message must be "
        "ONLY the JSON object — no prose before or after it. Put your reasoning "
        "inside the \"explanation\" field itself: "
        "{\"confidence\": float 0-1, \"explanation\": string, "
        f"\"disposition\": one of {VALID_DISPOSITIONS}}}.\n{DISPOSITION_DEFINITIONS}\n"
        "Never claim authority to post anything yourself — you only propose."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps({
            "transaction": safe_transaction, "ledger_candidates": ledger_candidates,
            "initial_evidence": initial_evidence, "rejection_reason": rejection_reason,
        }, default=str)},
    ]

    total_cost = 0.0
    for _ in range(MAX_REACT_ITERATIONS):
        response = litellm.completion(
            model=MODEL, messages=messages, tools=TOOL_SCHEMAS,
            metadata={"case_id": transaction["id"], "step": "react"},
        )
        total_cost += extract_cost(response)
        msg = response.choices[0].message

        if not getattr(msg, "tool_calls", None):
            try:
                tentative = _extract_json_object(msg.content)
            except json.JSONDecodeError:
                tentative = {"confidence": 0.0, "explanation": "Investigator failed to produce parseable output.", "disposition": "unresolved"}
            break

        messages.append(msg.model_dump())
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            result = _dispatch_tool(call.function.name, args, transaction)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})
    else:
        tentative = {"confidence": 0.0, "explanation": f"Exceeded {MAX_REACT_ITERATIONS} investigation steps without a conclusion.", "disposition": "unresolved"}

    final = await _reflect(safe_transaction, tentative)
    final["_llm_cost_usd"] = total_cost + final.pop("_reflect_cost_usd", 0.0)
    return final

async def _reflect(transaction: dict, tentative: dict) -> dict:
    """Re-fetches the authoritative policy version itself — does not trust
    whatever the ReAct loop happened to see or remember — and asks the model
    to check its tentative conclusion against it before finalizing."""
    topic = DISPOSITION_POLICY_TOPIC.get(tentative.get("disposition"), "materiality threshold")
    try:
        policy = retrieve_policy(topic, Date.fromisoformat(transaction["date"]))
    except NoPolicyInEffectError as e:
        policy = {"error": str(e)}

    reflection_prompt = (
        "Here is your tentative conclusion and the authoritative policy text "
        "actually in effect for this transaction's date. Revise your confidence "
        "or explanation if the policy contradicts your conclusion. Respond with "
        "the same JSON shape: confidence, explanation, and disposition, where "
        f"disposition must be one of {VALID_DISPOSITIONS}."
    )
    messages = [
        {"role": "system", "content": reflection_prompt},
        {"role": "user", "content": json.dumps({"tentative": tentative, "authoritative_policy": policy}, default=str)},
    ]
    response = litellm.completion(
        model=MODEL, messages=messages,
        metadata={"case_id": transaction["id"], "step": "reflection"},
    )
    reflect_cost = extract_cost(response)
    try:
        final = _extract_json_object(response.choices[0].message.content)
    except json.JSONDecodeError:
        final = tentative
    final["policy_checked"] = policy
    final["_reflect_cost_usd"] = reflect_cost
    return final