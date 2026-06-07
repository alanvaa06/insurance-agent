"""Tests for the LLM-backed tool functions using injected fakes."""
from app.agent.tools import (
    generate_policy_queries,
    generate_recommendation,
    retrieve_policy_text,
)
from tests.conftest import FakeLLM, FakeStore, queries_json, recommendation_json


def test_generate_queries_parses_array():
    llm = FakeLLM([queries_json("a", "b", "c")])
    queries = generate_policy_queries({"vendor_name": "X"}, llm=llm)
    assert queries == ["a", "b", "c"]


def test_generate_queries_accepts_object_with_queries_key():
    llm = FakeLLM(['{"queries": ["x", "y"]}'])
    assert generate_policy_queries({"vendor_name": "X"}, llm=llm) == ["x", "y"]


def test_generate_queries_falls_back_on_bad_output():
    llm = FakeLLM(["not json"])
    queries = generate_policy_queries({"vendor_name": "X"}, llm=llm)
    assert len(queries) >= 1  # deterministic fallback


def test_recommendation_normalizes_decision():
    llm = FakeLLM([recommendation_json("approve")])
    result = generate_recommendation({"claim_id": "C1"}, "policy", llm=llm)
    assert result["recommendation"] == "APPROVE"


def test_recommendation_ambiguous_routes_to_review():
    # Ambiguous model output should go to a human, not auto-deny/approve.
    llm = FakeLLM(['{"recommendation": "maybe", "reasoning": "unsure"}'])
    result = generate_recommendation({"claim_id": "C1"}, "policy", llm=llm)
    assert result["recommendation"] == "REVIEW"


def test_recommendation_system_error_routes_to_review():
    # A system error must not auto-deny the claimant.
    llm = FakeLLM(["totally not json and no braces"])
    result = generate_recommendation({"claim_id": "C1"}, "policy", llm=llm)
    assert result["recommendation"] == "REVIEW"


def test_retrieve_policy_text_joins_results():
    store = FakeStore("chunk text")
    text = retrieve_policy_text(["q1", "q2"], store=store)
    assert "chunk text" in text
    assert store.queries == ["q1", "q2"]
