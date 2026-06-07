"""Claim-processing operations.

Mechanical steps (parsing, validation, final decision) are deterministic Python
so they are predictable, free, and unit-testable. Only the two genuinely
semantic steps -- generating policy search queries and the policy-grounded
recommendation -- call the LLM. The LLM is injected so tests can supply a fake.
"""
import json
import re
from typing import Any, Dict, List, Optional

from app.agent.llm import get_llm
from app.agent.prompts import (
    GENERATE_POLICY_QUERIES_PROMPT,
    GENERATE_RECOMMENDATION_PROMPT,
)
from app.database.vector_store import get_policy_store
from app.utils.logger import logger

# --- Claim field aliases (support multiple claim schemas) ---
_AMOUNT_KEYS = ("claim_amount", "total_amount", "estimated_repair_cost", "amount")
_HOLDER_KEYS = ("policy_holder", "claimant_name", "policyholder", "insured_name")
_CLAIM_ID_KEYS = ("claim_id", "claim_number", "claimId")


def extract_json(text: str) -> Any:
    """Extract a JSON value from an LLM response that may wrap it in prose/markdown.

    Uses a brace/bracket-matching scan so nested objects are not truncated the
    way a non-greedy regex would.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip a ```json ... ``` fence if present.
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            text = fence.group(1).strip()

    # Scan for the first balanced { } or [ ] block.
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        if start == -1:
            continue
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == open_ch:
                    depth += 1
                elif ch == close_ch:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start : i + 1])
                        except json.JSONDecodeError:
                            break
    raise ValueError(f"Could not extract JSON from: {text[:200]}")


def _first(data: Dict[str, Any], keys) -> Optional[Any]:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def _coerce_amount(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # Strip currency symbols / thousands separators from strings.
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def parse_claim(claim_json: str) -> Dict[str, Any]:
    """Parse a claim JSON string into a normalized dict.

    Deterministic -- no LLM. Maps the several field-name variants used across
    claim schemas onto canonical keys.
    """
    logger.info("TOOL parse_claim: normalizing claim")
    try:
        raw = json.loads(claim_json) if isinstance(claim_json, str) else dict(claim_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"parse_claim: invalid claim JSON: {e}")
        return {"error": f"Invalid claim JSON: {e}"}

    items = raw.get("invoice_items") or []
    amount = _first(raw, _AMOUNT_KEYS)
    if amount is None and items:
        amount = sum(_coerce_amount(i.get("amount")) for i in items if isinstance(i, dict))

    parsed = {
        "claim_id": _first(raw, _CLAIM_ID_KEYS),
        "policy_holder": _first(raw, _HOLDER_KEYS),
        "vendor_name": raw.get("vendor_name"),
        "invoice_items": items,
        "claim_amount": _coerce_amount(amount),
        "policy_number": raw.get("policy_number"),
        "date_of_loss": raw.get("date_of_loss"),
    }
    logger.info(f"parse_claim: claim_id={parsed['claim_id']} amount={parsed['claim_amount']}")
    return parsed


def validate_claim(claim_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate required fields. Deterministic -- no LLM.

    Valid when: claim_id, policy_holder and vendor_name are non-empty and the
    claim amount is greater than zero.
    """
    logger.info("TOOL validate_claim: checking required fields")
    missing = []
    if not _nonempty(claim_data.get("claim_id")):
        missing.append("claim_id")
    if not _nonempty(claim_data.get("policy_holder")):
        missing.append("policy_holder")
    if not _nonempty(claim_data.get("vendor_name")):
        missing.append("vendor_name")

    amount = _coerce_amount(claim_data.get("claim_amount"))
    reasons = []
    if missing:
        reasons.append(f"Missing required field(s): {', '.join(missing)}.")
    if amount <= 0:
        reasons.append("Claim amount must be greater than 0.")

    if reasons:
        reason = " ".join(reasons)
        logger.warning(f"validate_claim: INVALID -- {reason}")
        return {"is_valid": False, "reason": reason}

    logger.info("validate_claim: VALID")
    return {"is_valid": True, "reason": ""}


def _nonempty(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def generate_policy_queries(claim_data: Dict[str, Any], llm=None) -> List[str]:
    """Generate 2-3 policy search queries (LLM)."""
    logger.info("TOOL generate_policy_queries")
    llm = llm or get_llm()
    try:
        prompt = GENERATE_POLICY_QUERIES_PROMPT.format(
            vendor_name=claim_data.get("vendor_name", "N/A"),
            invoice_items=json.dumps(claim_data.get("invoice_items", [])),
            claim_amount=claim_data.get("claim_amount", 0),
        )
        response = llm.invoke(prompt)
        queries = extract_json(response.content)
        if isinstance(queries, dict):
            queries = queries.get("queries", [])
        queries = [str(q) for q in queries if str(q).strip()]
        logger.info(f"generate_policy_queries: produced {len(queries)} queries")
        return queries
    except Exception as e:
        logger.error(f"generate_policy_queries failed: {e}")
        # Fall back to a sensible default query so retrieval still runs.
        return [
            f"coverage for {claim_data.get('vendor_name', 'repairs')}",
            "claim amount limits and exclusions",
        ]


def retrieve_policy_text(queries: List[str], store=None) -> str:
    """Retrieve and concatenate relevant policy passages from the vector store."""
    logger.info("TOOL retrieve_policy_text")
    store = store or get_policy_store()
    results = []
    for query in queries:
        text = store.retrieve(query, top_k=3)
        if text:
            results.append(text)
    combined = "\n\n---\n\n".join(results)
    logger.info(f"retrieve_policy_text: {len(combined)} chars from {len(results)} queries")
    return combined


def generate_recommendation(
    claim_data: Dict[str, Any], policy_text: str, llm=None
) -> Dict[str, Any]:
    """Recommend APPROVE / DENY grounded in retrieved policy text (LLM)."""
    logger.info("TOOL generate_recommendation")
    llm = llm or get_llm()
    try:
        prompt = GENERATE_RECOMMENDATION_PROMPT.format(
            claim_id=claim_data.get("claim_id", "N/A"),
            vendor_name=claim_data.get("vendor_name", "N/A"),
            claim_amount=claim_data.get("claim_amount", 0),
            invoice_items=json.dumps(claim_data.get("invoice_items", [])),
            policy_text=(policy_text or "No policy text retrieved.")[:2000],
        )
        response = llm.invoke(prompt)
        recommendation = extract_json(response.content)
        decision = str(recommendation.get("recommendation", "")).upper()
        if decision not in ("APPROVE", "DENY"):
            # Ambiguous model output: send to a human rather than guess. Denying
            # outright would risk a wrongful denial.
            decision = "REVIEW"
        recommendation["recommendation"] = decision
        logger.info(f"generate_recommendation: {decision}")
        return recommendation
    except Exception as e:
        logger.error(f"generate_recommendation failed: {e}")
        # A system error (outage, rate limit, bad key) must not auto-deny a
        # claimant. Route to manual review instead.
        return {
            "recommendation": "REVIEW",
            "reasoning": f"Automated evaluation unavailable ({e}); routed for manual review.",
        }


# Decision constants
APPROVED = "APPROVED"
DENIED = "DENIED"
REQUIRES_REVIEW = "REQUIRES_REVIEW"
INVALID = "INVALID"


def finalize_decision(
    recommendation: str,
    recommendation_reasoning: str,
    price_check_result: str,
    coverage_status: Optional[str] = None,
    coverage_reason: str = "",
) -> Dict[str, Any]:
    """Combine signals into a final decision. Deterministic -- no LLM.

    Rules (in order):
      1. Coverage explicitly NOT_COVERED  -> DENIED
      2. Price flagged as high amount     -> REQUIRES_REVIEW
      3. Recommendation DENY              -> DENIED
      4. Recommendation APPROVE           -> APPROVED
      5. Anything else (REVIEW/unknown)   -> REQUIRES_REVIEW
    """
    logger.info("TOOL finalize_decision")
    rec = str(recommendation or "").upper()

    if coverage_status == "NOT_COVERED":
        return {"final_decision": DENIED, "final_reasoning": coverage_reason}

    if price_check_result == "HIGH_AMOUNT_FLAGGED":
        return {
            "final_decision": REQUIRES_REVIEW,
            "final_reasoning": (
                "Claim amount exceeds the auto-approval threshold and requires "
                f"manual review. {recommendation_reasoning}"
            ).strip(),
        }

    if rec == "DENY":
        return {"final_decision": DENIED, "final_reasoning": recommendation_reasoning}

    if rec == "APPROVE":
        return {"final_decision": APPROVED, "final_reasoning": recommendation_reasoning}

    # Ambiguous or unavailable recommendation: never silently approve.
    return {"final_decision": REQUIRES_REVIEW, "final_reasoning": recommendation_reasoning}
