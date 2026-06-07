"""State schema for the LangGraph workflow."""
from typing import Any, TypedDict


class ClaimState(TypedDict, total=False):
    """State passed between nodes in the LangGraph workflow."""

    # Input
    claim_json: str

    # Parsed claim data
    claim_id: str | None
    invoice_items: list[dict[str, Any]] | None
    vendor_name: str | None
    claim_amount: float | None
    policy_holder: str | None
    policy_number: str | None
    date_of_loss: str | None

    # Validation
    is_valid: bool | None
    validation_reason: str | None

    # Coverage
    coverage_status: str | None
    coverage_reason: str | None

    # Policy retrieval
    policy_queries: list[str] | None
    retrieved_policy_text: str | None

    # Recommendation
    recommendation: str | None
    recommendation_reasoning: str | None

    # Price check
    price_check_result: str | None

    # Final decision
    final_decision: str | None
    final_reasoning: str | None

    # Flow control / logging
    current_step: str
