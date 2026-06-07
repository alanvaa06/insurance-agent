"""Tests for deterministic claim parsing."""
from app.agent.tools import parse_claim
from tests.conftest import load_test_case


def test_parse_maps_total_amount_to_claim_amount():
    parsed = parse_claim('{"claim_id": "C1", "total_amount": 550.0}')
    assert parsed["claim_amount"] == 550.0
    assert parsed["claim_id"] == "C1"


def test_parse_sums_invoice_items_when_no_total():
    claim = '{"claim_id": "C2", "invoice_items": [{"amount": 100}, {"amount": 50}]}'
    assert parse_claim(claim)["claim_amount"] == 150.0


def test_parse_handles_alternate_schema_fields():
    # ema_claim_data.json style: claim_number / claimant_name / estimated_repair_cost
    parsed = parse_claim(
        '{"claim_number": "CLAIM-1", "claimant_name": "Ema",'
        ' "estimated_repair_cost": 15000.0, "policy_number": "PL-1"}'
    )
    assert parsed["claim_id"] == "CLAIM-1"
    assert parsed["policy_holder"] == "Ema"
    assert parsed["claim_amount"] == 15000.0
    assert parsed["policy_number"] == "PL-1"


def test_parse_coerces_currency_string():
    parsed = parse_claim('{"claim_id": "C3", "total_amount": "$1,400.00"}')
    assert parsed["claim_amount"] == 1400.0


def test_parse_invalid_json_returns_error():
    assert "error" in parse_claim("{not valid json")


def test_parse_real_test_cases():
    expected_amounts = {
        "T1_Sarah_Mitchell.json": 500.0,
        "T2_Michael_Chen.json": 12000.0,
        "T3.json": 0.0,
        "T4_Jennifer_Rodriguez.json": 1400.0,
        "T5_David_Thompson.json": 22000.0,
    }
    for name, amount in expected_amounts.items():
        import json

        parsed = parse_claim(json.dumps(load_test_case(name)))
        assert parsed["claim_amount"] == amount, name
