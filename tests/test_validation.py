"""Tests for deterministic claim validation."""
from app.agent.tools import validate_claim


def test_valid_claim():
    result = validate_claim(
        {
            "claim_id": "C1",
            "policy_holder": "Jane",
            "vendor_name": "Garage",
            "claim_amount": 100.0,
        }
    )
    assert result["is_valid"] is True


def test_missing_policy_holder():
    result = validate_claim(
        {"claim_id": "C1", "policy_holder": "", "vendor_name": "Garage", "claim_amount": 100}
    )
    assert result["is_valid"] is False
    assert "policy_holder" in result["reason"]


def test_zero_amount_invalid():
    result = validate_claim(
        {"claim_id": "C1", "policy_holder": "Jane", "vendor_name": "Garage", "claim_amount": 0}
    )
    assert result["is_valid"] is False
    assert "amount" in result["reason"].lower()


def test_t3_empty_holder_and_zero_amount_invalid():
    # Mirrors test_cases/T3.json -> expected INVALID
    result = validate_claim(
        {
            "claim_id": "CLM-2026-AUTO-003",
            "policy_holder": "",
            "vendor_name": "Unknown Auto Shop",
            "claim_amount": 0.0,
        }
    )
    assert result["is_valid"] is False
