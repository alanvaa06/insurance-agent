"""Tests for the no-API-key demo mode: stub LLM, keyword retriever, and a real
end-to-end run of the workflow with no secrets."""
import json

import pytest

from app.agent.stub_llm import StubLLM
from app.database.vector_store import KeywordPolicyStore, extract_pdf_chunks
from app.utils.config import config
from tests.conftest import load_test_case

# --- StubLLM ---

def test_stub_returns_query_array():
    out = StubLLM().invoke("... Return ONLY a JSON array of query strings: ...")
    assert isinstance(json.loads(out.content), list)


def test_stub_denies_on_claim_red_flags():
    prompt = 'Items: ["Budget brand tires, not on approved list"]\nRelevant Policy Information:\nclean'
    out = json.loads(StubLLM().invoke(prompt).content)
    assert out["recommendation"] == "DENY"


def test_stub_approves_clean_claim():
    prompt = 'Items: ["OEM brake pads"]\nRelevant Policy Information:\nstandard coverage'
    out = json.loads(StubLLM().invoke(prompt).content)
    assert out["recommendation"] == "APPROVE"


def test_stub_ignores_red_flags_in_policy_text():
    # Red-flag words in the policy section must not flip a clean claim to DENY.
    prompt = 'Items: ["OEM brake pads"]\nRelevant Policy Information:\nnon-OEM parts are excluded'
    out = json.loads(StubLLM().invoke(prompt).content)
    assert out["recommendation"] == "APPROVE"


# --- Keyword retriever over the real policy PDF ---

def test_extract_pdf_chunks_reads_policy():
    chunks = extract_pdf_chunks(config.policy_pdf_path)
    assert len(chunks) > 0


def test_keyword_store_retrieves_text():
    store = KeywordPolicyStore()
    store.populate_from_pdf()
    assert store.count() > 0
    result = store.retrieve("coverage and exclusions", top_k=3)
    assert isinstance(result, str) and result


# --- End-to-end demo workflow (no patching, no API key) ---

@pytest.mark.skipif(
    config.is_api_key_configured(),
    reason="An API key is set; demo mode is off in this environment.",
)
@pytest.mark.parametrize(
    "case_file,expected",
    [
        ("T1_Sarah_Mitchell.json", "APPROVED"),
        ("T2_Michael_Chen.json", "REQUIRES_REVIEW"),
        ("T3.json", "INVALID"),
        ("T4_Jennifer_Rodriguez.json", "DENIED"),
        ("T5_David_Thompson.json", "REQUIRES_REVIEW"),
    ],
)
def test_demo_pipeline_end_to_end(case_file, expected):
    # Uses the real StubLLM + KeywordPolicyStore over data/policy.pdf.
    from app.agent.graph import create_claims_processing_graph

    graph = create_claims_processing_graph()
    claim = load_test_case(case_file)
    state = graph.invoke({"claim_json": json.dumps(claim), "current_step": "init"})
    assert state["final_decision"] == expected
