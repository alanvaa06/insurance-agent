"""Decision audit trail.

Appends one JSON line per finalized claim to logs/decisions.jsonl. Best-effort:
audit logging must never break claim processing, so all errors are swallowed
after being logged.
"""
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.utils.logger import logger

_AUDIT_PATH = Path("logs") / "decisions.jsonl"
_lock = threading.Lock()


def record_decision(state: dict[str, Any]) -> None:
    """Append a structured audit record for a finalized claim."""
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "claim_id": state.get("claim_id"),
        "final_decision": state.get("final_decision"),
        "coverage_status": state.get("coverage_status"),
        "price_check_result": state.get("price_check_result"),
        "recommendation": state.get("recommendation"),
        "claim_amount": state.get("claim_amount"),
    }
    try:
        with _lock:
            _AUDIT_PATH.parent.mkdir(exist_ok=True)
            with open(_AUDIT_PATH, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
    except OSError as e:
        logger.warning(f"Could not write decision audit record: {e}")
