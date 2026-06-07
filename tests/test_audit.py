"""Tests for the decision audit trail."""
import json

import app.utils.audit as audit


def test_record_decision_appends_jsonl(tmp_path, monkeypatch):
    path = tmp_path / "decisions.jsonl"
    monkeypatch.setattr(audit, "_AUDIT_PATH", path)

    audit.record_decision({"claim_id": "C1", "final_decision": "APPROVED", "claim_amount": 100})
    audit.record_decision({"claim_id": "C2", "final_decision": "DENIED", "claim_amount": 200})

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["claim_id"] == "C1"
    assert first["final_decision"] == "APPROVED"
    assert "timestamp" in first


def test_record_decision_never_raises(monkeypatch):
    # An unwritable path must not propagate an error.
    monkeypatch.setattr(audit, "_AUDIT_PATH", audit.Path("/nonexistent-dir-xyz/d.jsonl"))
    audit.record_decision({"claim_id": "C3"})  # should not raise
