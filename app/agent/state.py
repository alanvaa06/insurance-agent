"""State schema for the LangGraph workflow."""
from typing import Any, TypedDict

from pydantic import BaseModel, ConfigDict, Field


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


class ClaimInput(BaseModel):
    """User-submitted claim structure (UI / API validation)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "claim_id": "CLM-2026-001",
                "policy_holder": "John Doe",
                "vendor_name": "AutoFix Garage",
                "invoice_items": [
                    {"item": "Engine Repair", "amount": 500.00},
                    {"item": "Oil Change", "amount": 50.00},
                ],
                "total_amount": 550.00,
            }
        }
    )

    claim_id: str = Field(..., description="Unique claim identifier")
    policy_holder: str = Field(..., description="Name of policy holder")
    vendor_name: str = Field(..., description="Service provider name")
    invoice_items: list[dict[str, Any]] = Field(..., description="List of claimed items")
    total_amount: float = Field(..., description="Total claim amount")
