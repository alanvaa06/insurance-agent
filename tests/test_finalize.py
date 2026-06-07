"""Tests for the deterministic final-decision logic."""
from app.agent.tools import APPROVED, DENIED, REQUIRES_REVIEW, finalize_decision


def test_approve_when_recommended_and_normal_amount():
    result = finalize_decision("APPROVE", "meets policy", "WITHIN_NORMAL_RANGE")
    assert result["final_decision"] == APPROVED


def test_deny_when_recommendation_deny():
    result = finalize_decision("DENY", "vendor not authorized", "WITHIN_NORMAL_RANGE")
    assert result["final_decision"] == DENIED


def test_high_amount_forces_review_even_if_approved():
    result = finalize_decision("APPROVE", "looks fine", "HIGH_AMOUNT_FLAGGED")
    assert result["final_decision"] == REQUIRES_REVIEW


def test_not_covered_forces_denied_over_everything():
    result = finalize_decision(
        "APPROVE",
        "looks fine",
        "HIGH_AMOUNT_FLAGGED",
        coverage_status="NOT_COVERED",
        coverage_reason="dues outstanding",
    )
    assert result["final_decision"] == DENIED
    assert result["final_reasoning"] == "dues outstanding"
