"""
Wire / cash reconciliation engine.

Mirrors the manual process an operations analyst runs in Excel with
INDEX/MATCH: line up an internal ledger against a bank (or custodian)
statement on a reference key, then classify each pair as a clean match
or one of a fixed set of break types.

Break types
-----------
Match               - ref, currency, and amount all agree
Amount Mismatch     - ref and currency agree, amount does not
Currency Mismatch   - ref agrees, currency does not
Not Found in Bank   - ledger line has no corresponding bank line
Not Found in Ledger - bank line has no corresponding ledger line
                      (e.g. a bank fee that was never booked internally)
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["ref", "date", "description", "currency", "amount"]


def load_ledger(path: str | Path) -> pd.DataFrame:
    """Load the internal ledger (or custodian/GL side) from a CSV file."""
    return _load_side(path)


def load_bank_statement(path: str | Path) -> pd.DataFrame:
    """Load the bank (or external) statement side from a CSV file."""
    return _load_side(path)


def _load_side(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"])
    return df[REQUIRED_COLUMNS]


def _classify(row: pd.Series, amount_tolerance: float) -> str:
    if row["_merge"] == "left_only":
        return "Not Found in Bank"
    if row["_merge"] == "right_only":
        return "Not Found in Ledger"

    if row["currency_ledger"] != row["currency_bank"]:
        return "Currency Mismatch"

    if not math.isclose(
        row["amount_ledger"], row["amount_bank"], abs_tol=amount_tolerance
    ):
        return "Amount Mismatch"

    return "Match"


def reconcile(
    ledger: pd.DataFrame,
    bank: pd.DataFrame,
    key: str = "ref",
    amount_tolerance: float = 0.005,
) -> pd.DataFrame:
    """
    Reconcile two sides of a cash/wire ledger keyed on ``key``.

    Performs a full outer join so that both "in ledger, not in bank" and
    "in bank, not in ledger" breaks surface — a plain VLOOKUP from ledger
    into bank only catches the first kind.

    Returns a DataFrame with one row per unique key and a ``status``
    column holding one of the break types described in the module
    docstring.
    """
    merged = ledger.merge(
        bank,
        on=key,
        how="outer",
        suffixes=("_ledger", "_bank"),
        indicator=True,
    )

    merged["status"] = merged.apply(lambda r: _classify(r, amount_tolerance), axis=1)

    # A single, presentable date/description/amount/currency for reporting,
    # falling back to whichever side actually has the line.
    merged["date"] = merged["date_ledger"].fillna(merged["date_bank"])
    merged["description"] = merged["description_ledger"].fillna(
        merged["description_bank"]
    )

    ordered_cols = [
        key,
        "date",
        "description",
        "currency_ledger",
        "amount_ledger",
        "currency_bank",
        "amount_bank",
        "status",
    ]
    return merged[ordered_cols].sort_values(key).reset_index(drop=True)


def generate_exception_report(
    recon_df: pd.DataFrame,
    as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Filter a reconciliation result down to the breaks an analyst needs to
    clear, and bucket them by age — the "aged breaks" view used in daily
    ops/middle-office reviews.
    """
    as_of = as_of or pd.Timestamp.today().normalize()

    exceptions = recon_df[recon_df["status"] != "Match"].copy()
    exceptions["age_days"] = (as_of - exceptions["date"]).dt.days

    def bucket(days: float) -> str:
        if days <= 1:
            return "0-1 days"
        if days <= 5:
            return "2-5 days"
        return "5+ days"

    exceptions["age_bucket"] = exceptions["age_days"].apply(bucket)
    return exceptions.sort_values("age_days", ascending=False).reset_index(drop=True)
