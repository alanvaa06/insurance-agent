"""End-to-end workflow tests.

Runs each shipped test case through the compiled LangGraph with a fake LLM and
fake vector store, asserting the final decision matches
test_cases/test_case_expected_results.png.
"""
import json

import pytest

import app.agent.tools as tools
from app.agent.graph import create_claims_processing_graph
from tests.conftest import (
    FakeLLM,
    FakeStore,
    load_test_case,
    queries_json,
    recommendation_json,
)


def run_case(monkeypatch, case_file, recommendation_decision, policy_text=""):
    """Run one claim through the graph with scripted LLM output."""
    fake_llm = FakeLLM(
        [
            queries_json("coverage for repairs", "amount limits"),
            recommendation_json(recommendation_decision),
        ]
    )
    monkeypatch.setattr(tools, "get_llm", lambda *a, **k: fake_llm)
    monkeypatch.setattr(
        tools, "get_policy_store", lambda: FakeStore(policy_text or "Standard coverage.")
    )

    graph = create_claims_processing_graph()
    claim = load_test_case(case_file)
    state = graph.invoke({"claim_json": json.dumps(claim), "current_step": "init"})
    return state


def test_t1_low_risk_approved(monkeypatch):
    state = run_case(monkeypatch, "T1_Sarah_Mitchell.json", "APPROVE")
    assert state["final_decision"] == "APPROVED"


def test_t2_high_amount_requires_review(monkeypatch):
    # $12,000 >= threshold -> review regardless of recommendation
    state = run_case(monkeypatch, "T2_Michael_Chen.json", "APPROVE")
    assert state["final_decision"] == "REQUIRES_REVIEW"


def test_t3_invalid_short_circuits(monkeypatch):
    # Invalid -> never reaches the LLM nodes
    state = run_case(monkeypatch, "T3.json", "APPROVE")
    assert state["final_decision"] == "INVALID"


def test_t4_unauthorized_vendor_denied(monkeypatch):
    state = run_case(
        monkeypatch,
        "T4_Jennifer_Rodriguez.json",
        "DENY",
        policy_text="Only OEM parts from approved vendors are covered.",
    )
    assert state["final_decision"] == "DENIED"


def test_t5_policy_limit_requires_review(monkeypatch):
    # $22,000 >= threshold -> review
    state = run_case(monkeypatch, "T5_David_Thompson.json", "APPROVE")
    assert state["final_decision"] == "REQUIRES_REVIEW"


@pytest.mark.parametrize(
    "case_file,decision,expected",
    [
        ("T1_Sarah_Mitchell.json", "APPROVE", "APPROVED"),
        ("T2_Michael_Chen.json", "APPROVE", "REQUIRES_REVIEW"),
        ("T3.json", "APPROVE", "INVALID"),
        ("T4_Jennifer_Rodriguez.json", "DENY", "DENIED"),
        ("T5_David_Thompson.json", "APPROVE", "REQUIRES_REVIEW"),
    ],
)
def test_all_expected_results(monkeypatch, case_file, decision, expected):
    state = run_case(monkeypatch, case_file, decision)
    assert state["final_decision"] == expected


def test_malformed_json_returns_invalid(monkeypatch):
    # Garbage input must flow through to INVALID, not crash the graph.
    fake_llm = FakeLLM([])
    monkeypatch.setattr(tools, "get_llm", lambda *a, **k: fake_llm)
    monkeypatch.setattr(tools, "get_policy_store", lambda: FakeStore())
    graph = create_claims_processing_graph()
    state = graph.invoke({"claim_json": "not json at all", "current_step": "init"})
    assert state["final_decision"] == "INVALID"
    assert state["is_valid"] is False
    assert fake_llm.prompts == []


def test_missing_claim_json_does_not_crash(monkeypatch):
    fake_llm = FakeLLM([])
    monkeypatch.setattr(tools, "get_llm", lambda *a, **k: fake_llm)
    monkeypatch.setattr(tools, "get_policy_store", lambda: FakeStore())
    graph = create_claims_processing_graph()
    state = graph.invoke({"current_step": "init"})
    assert state["final_decision"] == "INVALID"


def test_not_covered_short_circuits_without_llm(monkeypatch):
    # A claim on a policy with outstanding dues (PN-3) is denied without ever
    # invoking the LLM.
    fake_llm = FakeLLM([])  # empty: any LLM call would surface as wrong output
    monkeypatch.setattr(tools, "get_llm", lambda *a, **k: fake_llm)
    monkeypatch.setattr(tools, "get_policy_store", lambda: FakeStore("unused"))

    graph = create_claims_processing_graph()
    claim = {
        "claim_id": "CLM-NC-1",
        "policy_holder": "Jane Doe",
        "vendor_name": "Garage",
        "policy_number": "PN-3",  # premium_dues_remaining = True
        "date_of_loss": "2021-07-01",
        "total_amount": 500.0,
    }
    state = graph.invoke({"claim_json": json.dumps(claim), "current_step": "init"})
    assert state["final_decision"] == "DENIED"
    assert state["coverage_status"] == "NOT_COVERED"
    assert fake_llm.prompts == []  # no LLM calls were made
