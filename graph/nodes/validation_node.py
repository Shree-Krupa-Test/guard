# graph/nodes/validation_node.py
#
# Validation Node
# ───────────────
# 1. Hallucination Check  — does the response follow logically from the prompt?
# 2. Source Grounding     — (RAG) is the response grounded in provided context?
# 3. Self-Correction Loop — if either check fails, retry once with a corrective prompt.
#
# BUG FIX: Source grounding logic was incorrectly showing "skipped_no_context"
# even when context_chunks were provided. The else branch was catching
# grounded=False + confidence=HIGH and treating it as no context.
# Fixed with explicit 3-way logic: has_context / no_context / low_confidence.

from services.azure_openai import call_llm
from policies.hallucination_checker import validate_response
from policies.source_grounding import check_source_grounding
from policies.pii_redactor import redact_pii


async def _self_correct(prompt: str, bad_response: str, reason: str) -> str:
    correction_prompt = f"""
The following response was flagged as potentially inaccurate or ungrounded.

Original Question: {prompt}

Flagged Response: {bad_response}

Issue: {reason}

Please provide a corrected, accurate, and well-grounded response to the original question.
Be concise and factual. Only use information from the provided context if available.
"""
    corrected, _ = await call_llm(correction_prompt)
    return corrected


async def validation_node(state: dict):

    print("[Validation Node] Running response validation...")

    if not state.get("allowed", True):
        return state

    prompt         = state.get("prompt", "")
    response       = state.get("response", "")
    context_chunks = state.get("context_chunks", [])

    if not response:
        state["policy_decisions"].append({
            "node":   "validation_node",
            "rule":   "VALIDATION",
            "action": "skipped_no_response"
        })
        return state

    # ──────────────────────────────────────────────────────
    # Step 1: Hallucination Check
    # ──────────────────────────────────────────────────────
    is_valid = await validate_response(prompt, response)

    if not is_valid:

        print("[Validation Node] Hallucination detected — attempting self-correction...")

        corrected          = await _self_correct(prompt, response,
                                "The response does not logically follow from the original question.")
        is_corrected_valid = await validate_response(prompt, corrected)

        if is_corrected_valid:
            print("[Validation Node] Self-correction succeeded.")
            state["response"] = redact_pii(corrected)
            state["policy_decisions"].append({
                "node": "validation_node", "rule": "HALLUCINATION_CHECK",
                "action": "self_corrected"
            })
        else:
            print("[Validation Node] Self-correction failed — blocking.")
            state["allowed"] = False
            state["violations"].append("HALLUCINATION_DETECTED")
            state["policy_decisions"].append({
                "node": "validation_node", "rule": "HALLUCINATION_CHECK",
                "action": "blocked"
            })
            state["response"] = "Response flagged as potentially inaccurate after self-correction attempt."
            return state
    else:
        state["policy_decisions"].append({
            "node": "validation_node", "rule": "HALLUCINATION_CHECK",
            "action": "allowed"
        })

    # ──────────────────────────────────────────────────────
    # Step 2: Source Grounding Check
    #
    # FIX: Explicit 3-way logic:
    #   A) No context chunks provided   → skipped_no_context
    #   B) Context provided + grounded  → allowed
    #   C) Context provided + LOW conf  → self-correct → low_confidence flag
    #   D) Context provided + ungrounded (HIGH conf) → flag ungrounded
    # ──────────────────────────────────────────────────────

    # Case A: No context chunks — skip grounding entirely
    if not context_chunks:
        state["grounding_result"] = {
            "grounded":   True,
            "confidence": "HIGH",
            "reason":     "No context chunks provided — grounding check skipped."
        }
        state["policy_decisions"].append({
            "node":   "validation_node",
            "rule":   "SOURCE_GROUNDING",
            "action": "skipped_no_context"
        })
        print("[Validation Node] No context chunks — grounding skipped.")
        print("[Validation Node] Validation complete.")
        return state

    # Cases B / C / D: Context chunks provided — run grounding check
    print(f"[Validation Node] Running grounding check with {len(context_chunks)} context chunks...")
    grounding = await check_source_grounding(prompt, state["response"], context_chunks)
    state["grounding_result"] = grounding
    print(f"[Validation Node] Grounding: {grounding['confidence']} — {grounding['reason']}")

    # Case C: LOW confidence → attempt self-correction
    if not grounding["grounded"] and grounding["confidence"] == "LOW":

        print("[Validation Node] Low confidence — attempting grounding self-correction...")

        corrected       = await _self_correct(
            prompt, state["response"],
            f"Response not grounded in provided context. {grounding['reason']}"
        )
        grounding_retry = await check_source_grounding(prompt, corrected, context_chunks)

        if grounding_retry["grounded"]:
            print("[Validation Node] Grounding self-correction succeeded.")
            state["response"]         = redact_pii(corrected)
            state["grounding_result"] = grounding_retry
            state["policy_decisions"].append({
                "node": "validation_node", "rule": "SOURCE_GROUNDING",
                "action": "self_corrected"
            })
        else:
            print("[Validation Node] Grounding self-correction failed — LOW_CONFIDENCE flag.")
            state["violations"].append("LOW_CONFIDENCE_RESPONSE")
            state["policy_decisions"].append({
                "node": "validation_node", "rule": "SOURCE_GROUNDING",
                "action": "low_confidence"
            })

    # Case D: Grounded=False but confidence HIGH → flag as ungrounded, don't hard block
    elif not grounding["grounded"] and grounding["confidence"] == "HIGH":
        print("[Validation Node] Response ungrounded — flagging LOW_CONFIDENCE_RESPONSE.")
        state["violations"].append("LOW_CONFIDENCE_RESPONSE")
        state["policy_decisions"].append({
            "node":   "validation_node",
            "rule":   "SOURCE_GROUNDING",
            "action": "ungrounded"
        })

    # Case B: Grounded — all good
    else:
        state["policy_decisions"].append({
            "node":   "validation_node",
            "rule":   "SOURCE_GROUNDING",
            "action": "allowed"
        })

    print("[Validation Node] Validation complete.")
    return state