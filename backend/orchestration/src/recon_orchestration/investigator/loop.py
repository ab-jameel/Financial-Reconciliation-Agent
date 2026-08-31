# backend/orchestration/src/recon_orchestration/investigator/loop.py
import asyncio
import json
import os
from datetime import date as Date
from decimal import Decimal
import litellm

from recon_orchestration.investigator.policy_store import retrieve_policy, NoPolicyInEffectError
from recon_orchestration.investigator.tools import (
    search_related_transactions, compute_date_delta, compute_amount_delta, TOOL_SCHEMAS,
)

MODEL = os.environ.get("LLM_MODEL")  # set to your provider's exact current model string —
                                       # check litellm/your provider's docs rather than hardcoding one here
MAX_REACT_ITERATIONS = 6  # safety cap: force a stop rather than loop indefinitely on a confused model


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
    return {"error": f"unknown tool {name}"}


async def _rewoo_initial_gather(transaction: dict, ledger_candidates: list[dict]) -> dict:
    """Plan the obvious first-round fetches upfront and run them concurrently,
    rather than looping one tool call at a time for information we already
    know we'll need regardless of what the model decides."""
    exception_topic_query = {
        "amount_mismatch": "materiality threshold",
        "date_mismatch": "materiality threshold",
        "currency_issue": "materiality threshold",
        "duplicate": "duplicate handling",
        "missing_invoice": "materiality threshold",
        "policy_sensitive": "materiality threshold",
    }.get(transaction["label_exception_type"], "materiality threshold")

    def _policy():
        try:
            return retrieve_policy(exception_topic_query, Date.fromisoformat(transaction["date"]))
        except NoPolicyInEffectError as e:
            return {"error": str(e)}

    policy_result, related_result = await asyncio.gather(
        asyncio.to_thread(_policy),
        asyncio.to_thread(search_related_transactions, transaction["reference"], transaction["dataset_split"], transaction["id"]),
    )
    return {"policy": policy_result, "related_transactions": related_result}


async def investigate(transaction: dict, ledger_candidates: list[dict], rejection_reason: str | None) -> dict:
    initial_evidence = await _rewoo_initial_gather(transaction, ledger_candidates)

    system_prompt = (
        "You are investigating a bank-to-ledger reconciliation exception. "
        "Gather evidence using the available tools, then produce a final JSON "
        "object: {\"confidence\": float 0-1, \"explanation\": string, \"disposition\": string}. "
        "Never claim authority to post anything yourself — you only propose."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps({
            "transaction": transaction, "ledger_candidates": ledger_candidates,
            "initial_evidence": initial_evidence, "rejection_reason": rejection_reason,
        }, default=str)},
    ]

    for _ in range(MAX_REACT_ITERATIONS):
        response = litellm.completion(model=MODEL, messages=messages, tools=TOOL_SCHEMAS)
        msg = response.choices[0].message

        if not getattr(msg, "tool_calls", None):
            try:
                tentative = json.loads(msg.content)
            except (json.JSONDecodeError, TypeError):
                tentative = {"confidence": 0.0, "explanation": "Investigator failed to produce parseable output.", "disposition": "unresolved"}
            break

        messages.append(msg.model_dump())
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            result = _dispatch_tool(call.function.name, args, transaction)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})
    else:
        tentative = {"confidence": 0.0, "explanation": f"Exceeded {MAX_REACT_ITERATIONS} investigation steps without a conclusion.", "disposition": "unresolved"}

    return await _reflect(transaction, tentative)


async def _reflect(transaction: dict, tentative: dict) -> dict:
    """Re-fetches the authoritative policy version itself — does not trust
    whatever the ReAct loop happened to see or remember — and asks the model
    to check its tentative conclusion against it before finalizing."""
    try:
        policy = retrieve_policy("materiality threshold", Date.fromisoformat(transaction["date"]))
    except NoPolicyInEffectError as e:
        policy = {"error": str(e)}

    reflection_prompt = (
        "Here is your tentative conclusion and the authoritative policy text "
        "actually in effect for this transaction's date. Revise your confidence "
        "or explanation if the policy contradicts your conclusion. Respond with "
        "the same JSON shape: confidence, explanation, disposition."
    )
    messages = [
        {"role": "system", "content": reflection_prompt},
        {"role": "user", "content": json.dumps({"tentative": tentative, "authoritative_policy": policy}, default=str)},
    ]
    response = litellm.completion(model=MODEL, messages=messages)
    try:
        final = json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        final = tentative  # Reflection call itself failed to parse — fall back rather than crash the case
    final["policy_checked"] = policy
    return final