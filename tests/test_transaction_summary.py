import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reconciliation.transaction_summary import load_transactions, summarize

DATA_DIR = Path(__file__).parent.parent / "data"

# Ground truth taken from the "Ex2 Solution" tab of the source workbook.
EXPECTED_BY_CURRENCY = {
    "USD": 176093.90,
    "EUR": 104438.56,
    "GBP": 171053.76,
    "INR": 92382.75,
}

EXPECTED_BY_ENTITY = {
    "Diamond India": 145892.45,
    "Diamond UK": 196821.31,
    "Diamond US": 201255.21,
}


@pytest.fixture
def txns():
    return load_transactions(DATA_DIR / "wire_transactions.csv")


def test_summary_by_currency_matches_workbook(txns):
    result = summarize(txns, "currency").set_index("currency")["total"]
    for ccy, expected in EXPECTED_BY_CURRENCY.items():
        assert result[ccy] == pytest.approx(expected, abs=0.01)


def test_summary_by_entity_matches_workbook(txns):
    result = summarize(txns, "entity").set_index("entity")["total"]
    for entity, expected in EXPECTED_BY_ENTITY.items():
        assert result[entity] == pytest.approx(expected, abs=0.01)


def test_summary_total_equals_grand_total(txns):
    by_currency = summarize(txns, "currency")["total"].sum()
    by_entity = summarize(txns, "entity")["total"].sum()
    assert by_currency == pytest.approx(by_entity, abs=0.01)
    assert by_currency == pytest.approx(txns["amount_usd_eq"].sum(), abs=0.01)
