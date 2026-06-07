"""Policy coverage checks backed by data/coverage_data.csv.

The CSV records, per policy, whether premium dues are outstanding and the
coverage window. A claim is only checked when it references a policy number;
claims without one return status ``UNKNOWN`` and never block a decision on their
own (they are surfaced for the adjudicator instead).
"""
import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.utils.config import config
from app.utils.logger import logger

# Accepted aliases for the policy identifier across claim schemas.
_POLICY_KEYS = ("policy_number", "policy_id", "policy_no", "policyNumber")
# Accepted aliases for the date the loss occurred.
_LOSS_DATE_KEYS = ("date_of_loss", "loss_date", "incident_date", "dateOfLoss")

COVERED = "COVERED"
NOT_COVERED = "NOT_COVERED"
UNKNOWN = "UNKNOWN"


def _get_first(data: Dict[str, Any], keys) -> Optional[Any]:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def _parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "y")


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def load_coverage_table(csv_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Load the coverage CSV into a dict keyed by policy_number."""
    path = Path(csv_path or config.coverage_csv_path)
    table: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        logger.warning(f"Coverage CSV not found: {path}")
        return table

    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            policy = (row.get("policy_number") or "").strip()
            if policy:
                table[policy] = row
    logger.info(f"Loaded {len(table)} policies from coverage table")
    return table


def check_coverage(
    claim_data: Dict[str, Any],
    csv_path: Optional[str] = None,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Check a claim's policy against the coverage table.

    Returns ``{"status", "reason", "policy_number"}`` where status is one of
    COVERED / NOT_COVERED / UNKNOWN.
    """
    policy_number = _get_first(claim_data, _POLICY_KEYS)
    if not policy_number:
        return {
            "status": UNKNOWN,
            "reason": "No policy number on claim; coverage not verified.",
            "policy_number": None,
        }

    policy_number = str(policy_number).strip()
    table = load_coverage_table(csv_path)
    record = table.get(policy_number)
    if record is None:
        return {
            "status": UNKNOWN,
            "reason": f"Policy '{policy_number}' not found in coverage table.",
            "policy_number": policy_number,
        }

    # Outstanding premium dues void coverage.
    if _parse_bool(record.get("premium_dues_remaining")):
        return {
            "status": NOT_COVERED,
            "reason": f"Policy '{policy_number}' has outstanding premium dues.",
            "policy_number": policy_number,
        }

    # Loss must fall within the coverage window (when both dates are available).
    loss_date = _parse_date(_get_first(claim_data, _LOSS_DATE_KEYS))
    start = _parse_date(record.get("coverage_start_date"))
    end = _parse_date(record.get("coverage_end_date"))
    reference_day = today or date.today()
    check_day = loss_date or reference_day

    if start and end and not (start <= check_day <= end):
        return {
            "status": NOT_COVERED,
            "reason": (
                f"Loss date {check_day} is outside coverage window "
                f"{start} to {end}."
            ),
            "policy_number": policy_number,
        }

    return {
        "status": COVERED,
        "reason": f"Policy '{policy_number}' is active and paid up.",
        "policy_number": policy_number,
    }
