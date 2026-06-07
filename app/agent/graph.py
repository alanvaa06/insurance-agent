"""LangGraph workflow for insurance claims processing.

Flow:
    parse -> validate --(valid)--> coverage_check -> generate_queries
          -> retrieve_policy -> recommendation -> price_check -> finalize -> END
                     \\--(invalid)--> invalid_claim -> END

Mechanical nodes are deterministic; only query generation and the
recommendation call the LLM (see app.agent.tools).
"""
import threading
from typing import Literal

from langgraph.graph import END, StateGraph

from app.agent.coverage import NOT_COVERED, check_coverage
from app.agent.state import ClaimState
from app.agent.tools import (
    INVALID,
    finalize_decision,
    generate_policy_queries,
    generate_recommendation,
    parse_claim,
    retrieve_policy_text,
    validate_claim,
)
from app.utils.audit import record_decision
from app.utils.config import config
from app.utils.logger import logger

# === NODES ===

def parse_claim_node(state: ClaimState) -> ClaimState:
    logger.info("NODE parse_claim")
    result = parse_claim(state["claim_json"])
    state["claim_id"] = result.get("claim_id")
    state["policy_holder"] = result.get("policy_holder")
    state["vendor_name"] = result.get("vendor_name")
    state["invoice_items"] = result.get("invoice_items")
    state["claim_amount"] = result.get("claim_amount")
    state["policy_number"] = result.get("policy_number")
    state["date_of_loss"] = result.get("date_of_loss")
    state["current_step"] = "parsed"
    return state


def validate_claim_node(state: ClaimState) -> ClaimState:
    logger.info("NODE validate_claim")
    result = validate_claim(
        {
            "claim_id": state.get("claim_id"),
            "policy_holder": state.get("policy_holder"),
            "vendor_name": state.get("vendor_name"),
            "claim_amount": state.get("claim_amount"),
        }
    )
    state["is_valid"] = result.get("is_valid", False)
    state["validation_reason"] = result.get("reason", "")
    state["current_step"] = "validated"
    return state


def coverage_check_node(state: ClaimState) -> ClaimState:
    logger.info("NODE coverage_check")
    result = check_coverage(
        {
            "policy_number": state.get("policy_number"),
            "date_of_loss": state.get("date_of_loss"),
        }
    )
    state["coverage_status"] = result.get("status")
    state["coverage_reason"] = result.get("reason")
    state["current_step"] = "coverage_checked"
    return state


def generate_queries_node(state: ClaimState) -> ClaimState:
    logger.info("NODE generate_queries")
    state["policy_queries"] = generate_policy_queries(
        {
            "vendor_name": state.get("vendor_name"),
            "invoice_items": state.get("invoice_items"),
            "claim_amount": state.get("claim_amount"),
        }
    )
    state["current_step"] = "queries_generated"
    return state


def retrieve_policy_node(state: ClaimState) -> ClaimState:
    logger.info("NODE retrieve_policy")
    state["retrieved_policy_text"] = retrieve_policy_text(state["policy_queries"])
    state["current_step"] = "policy_retrieved"
    return state


def recommendation_node(state: ClaimState) -> ClaimState:
    logger.info("NODE recommendation")
    result = generate_recommendation(
        {
            "claim_id": state.get("claim_id"),
            "vendor_name": state.get("vendor_name"),
            "claim_amount": state.get("claim_amount"),
            "invoice_items": state.get("invoice_items"),
        },
        state.get("retrieved_policy_text", ""),
    )
    state["recommendation"] = result.get("recommendation")
    state["recommendation_reasoning"] = result.get("reasoning")
    state["current_step"] = "recommendation_generated"
    return state


def price_check_node(state: ClaimState) -> ClaimState:
    logger.info("NODE price_check")
    amount = state.get("claim_amount") or 0
    threshold = config.high_amount_threshold
    if amount >= threshold:
        state["price_check_result"] = "HIGH_AMOUNT_FLAGGED"
        logger.warning(f"High claim amount: ${amount} (>= ${threshold})")
    else:
        state["price_check_result"] = "WITHIN_NORMAL_RANGE"
    state["current_step"] = "price_checked"
    return state


def finalize_decision_node(state: ClaimState) -> ClaimState:
    logger.info("NODE finalize_decision")
    result = finalize_decision(
        recommendation=state.get("recommendation"),
        recommendation_reasoning=state.get("recommendation_reasoning", ""),
        price_check_result=state.get("price_check_result", ""),
        coverage_status=state.get("coverage_status"),
        coverage_reason=state.get("coverage_reason", ""),
    )
    state["final_decision"] = result.get("final_decision")
    state["final_reasoning"] = result.get("final_reasoning")
    state["current_step"] = "completed"
    record_decision(state)
    return state


def invalid_claim_node(state: ClaimState) -> ClaimState:
    logger.info("NODE invalid_claim")
    state["final_decision"] = INVALID
    state["final_reasoning"] = state.get("validation_reason", "Claim failed validation.")
    state["current_step"] = "completed"
    record_decision(state)
    return state


# === EDGES ===

def should_continue_after_validation(state: ClaimState) -> Literal["continue", "invalid"]:
    return "continue" if state.get("is_valid") else "invalid"


def route_after_coverage(state: ClaimState) -> Literal["denied", "continue"]:
    # A claim with no active coverage is denied without spending LLM calls on
    # policy retrieval and a recommendation.
    return "denied" if state.get("coverage_status") == NOT_COVERED else "continue"


# === BUILD ===

def create_claims_processing_graph():
    """Build and compile the LangGraph workflow."""
    logger.info("Building LangGraph workflow")
    workflow = StateGraph(ClaimState)

    workflow.add_node("parse_claim", parse_claim_node)
    workflow.add_node("validate_claim", validate_claim_node)
    workflow.add_node("coverage_check", coverage_check_node)
    workflow.add_node("generate_queries", generate_queries_node)
    workflow.add_node("retrieve_policy", retrieve_policy_node)
    workflow.add_node("recommend", recommendation_node)
    workflow.add_node("price_check", price_check_node)
    workflow.add_node("finalize_decision", finalize_decision_node)
    workflow.add_node("invalid_claim", invalid_claim_node)

    workflow.set_entry_point("parse_claim")
    workflow.add_edge("parse_claim", "validate_claim")
    workflow.add_conditional_edges(
        "validate_claim",
        should_continue_after_validation,
        {"continue": "coverage_check", "invalid": "invalid_claim"},
    )
    workflow.add_conditional_edges(
        "coverage_check",
        route_after_coverage,
        {"continue": "generate_queries", "denied": "finalize_decision"},
    )
    workflow.add_edge("generate_queries", "retrieve_policy")
    workflow.add_edge("retrieve_policy", "recommend")
    workflow.add_edge("recommend", "price_check")
    workflow.add_edge("price_check", "finalize_decision")
    workflow.add_edge("finalize_decision", END)
    workflow.add_edge("invalid_claim", END)

    compiled = workflow.compile()
    logger.info("LangGraph workflow compiled")
    return compiled


_claims_graph = None
_claims_graph_lock = threading.Lock()


def get_claims_graph():
    """Return a lazily-compiled, process-wide claims graph (thread-safe)."""
    global _claims_graph
    if _claims_graph is None:
        with _claims_graph_lock:
            if _claims_graph is None:
                _claims_graph = create_claims_processing_graph()
    return _claims_graph
