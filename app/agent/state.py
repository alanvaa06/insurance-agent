"""State schema for the LangGraph workflow."""
from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class ClaimState(TypedDict, total=False):
    """State passed between nodes in the LangGraph workflow."""

    # Input
    claim_json: str

    # Parsed claim data
    claim_id: Optional[str]
    invoice_items: Optional[List[Dict[str, Any]]]
    vendor_name: Optional[str]
    claim_amount: Optional[float]
    policy_holder: Optional[str]
    policy_number: Optional[str]
    date_of_loss: Optional[str]

    # Validation
    is_valid: Optional[bool]
    validation_reason: Optional[str]

    # Coverage
    coverage_status: Optional[str]
    coverage_reason: Optional[str]

    # Policy retrieval
    policy_queries: Optional[List[str]]
    retrieved_policy_text: Optional[str]

    # Recommendation
    recommendation: Optional[str]
    recommendation_reasoning: Optional[str]

    # Price check
    price_check_result: Optional[str]

    # Final decision
    final_decision: Optional[str]
    final_reasoning: Optional[str]

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
    invoice_items: List[Dict[str, Any]] = Field(..., description="List of claimed items")
    total_amount: float = Field(..., description="Total claim amount")
