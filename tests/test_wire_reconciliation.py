import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reconciliation import generate_exception_report, load_bank_statement, load_ledger, reconcile

DATA_DIR = Path(__file__).parent.parent / "data"

# Ground truth taken from the "Ex1 Solution" tab of the source workbook.
EXPECTED_STATUS = {
    "WT-1001": "Match",
    "WT-1002": "Match",
    "WT-1003": "Match",
    "WT-1004": "Match",
    "WT-1005": "Amount Mismatch",
    "WT-1006": "Match",
    "WT-1007": "Match",
    "WT-1008": "Match",
    "WT-1009": "Currency Mismatch",
    "WT-1010": "Match",
    "WT-1011": "Match",
    "WT-1012": "Match",
    "WT-1013": "Match",
    "WT-1014": "Not Found in Ledger",  # bank-only line
    "BF-2001": "Not Found in Bank",  # ledger-only line (bank fee)
}


@pytest.fixture
def recon_result() -> pd.DataFrame:
    ledger = load_ledger(DATA_DIR / "ledger.csv")
    bank = load_bank_statement(DATA_DIR / "bank_statement.csv")
    return reconcile(ledger, bank)


def test_row_count_covers_both_sides(recon_result):
    # 14 ledger + 14 bank lines, 13 shared refs -> 15 unique keys
    assert len(recon_result) == 15


@pytest.mark.parametrize("ref,expected_status", list(EXPECTED_STATUS.items()))
def test_matches_workbook_solution(recon_result, ref, expected_status):
    row = recon_result.loc[recon_result["ref"] == ref]
    assert not row.empty, f"{ref} missing from reconciliation output"
    assert row.iloc[0]["status"] == expected_status


def test_exception_report_excludes_matches(recon_result):
    exceptions = generate_exception_report(recon_result, as_of=pd.Timestamp("2026-07-10"))
    assert "Match" not in exceptions["status"].values
    assert len(exceptions) == 4  # WT-1005, WT-1009, WT-1014, BF-2001


def test_exception_report_has_age_bucket(recon_result):
    exceptions = generate_exception_report(recon_result, as_of=pd.Timestamp("2026-07-10"))
    assert set(exceptions["age_bucket"]) <= {"0-1 days", "2-5 days", "5+ days"}
