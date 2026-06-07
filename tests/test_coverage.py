"""Tests for the coverage check against data/coverage_data.csv."""
from datetime import date

from app.agent.coverage import COVERED, NOT_COVERED, UNKNOWN, check_coverage


def test_no_policy_number_is_unknown():
    result = check_coverage({"claim_id": "C1"})
    assert result["status"] == UNKNOWN


def test_paid_up_active_policy_is_covered():
    # PN-2: premium_dues_remaining=False, window 2023-01-01..2025-11-30
    result = check_coverage(
        {"policy_number": "PN-2", "date_of_loss": "2024-05-01"}, today=date(2024, 5, 1)
    )
    assert result["status"] == COVERED


def test_outstanding_dues_not_covered():
    # PN-3: premium_dues_remaining=True
    result = check_coverage({"policy_number": "PN-3", "date_of_loss": "2021-07-01"})
    assert result["status"] == NOT_COVERED
    assert "dues" in result["reason"].lower()


def test_loss_outside_window_not_covered():
    # PN-1 window ends 2022-12-31
    result = check_coverage({"policy_number": "PN-1", "date_of_loss": "2024-01-01"})
    assert result["status"] == NOT_COVERED
    assert "outside" in result["reason"].lower()


def test_unknown_policy_number():
    result = check_coverage({"policy_number": "PN-DOES-NOT-EXIST"})
    assert result["status"] == UNKNOWN


def test_missing_csv_returns_unknown(tmp_path):
    missing = tmp_path / "nope.csv"
    result = check_coverage({"policy_number": "PN-2"}, csv_path=str(missing))
    assert result["status"] == UNKNOWN


def test_custom_csv_is_read(tmp_path):
    csv_file = tmp_path / "cov.csv"
    csv_file.write_text(
        "policy_number,premium_dues_remaining,coverage_start_date,coverage_end_date\n"
        "X-1,False,2020-01-01,2030-01-01\n",
        encoding="utf-8",
    )
    result = check_coverage(
        {"policy_number": "X-1", "date_of_loss": "2025-01-01"}, csv_path=str(csv_file)
    )
    assert result["status"] == COVERED
