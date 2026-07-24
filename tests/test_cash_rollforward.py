import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reconciliation.cash_rollforward import load_rollforward_data, rollforward, rollforward_all

DATA_DIR = Path(__file__).parent.parent / "data"

# Ground truth taken from the "Ex3 Solution" tab of the source workbook.
EXPECTED_CLOSING = {
    "USD Operating": 335429.25,
    "EUR Operating": 13249.50,
    "GBP Operating": 46899.80,
}


def test_rollforward_single_account():
    assert rollforward(182430, [12500, -84200, -3300.75, 250000, -22000]) == pytest.approx(
        335429.25
    )


def test_rollforward_all_matches_workbook():
    df = load_rollforward_data(DATA_DIR / "cash_rollforward.csv")
    result = rollforward_all(df).set_index("account")["closing_balance"]
    for account, expected in EXPECTED_CLOSING.items():
        assert result[account] == pytest.approx(expected, abs=0.01)
