"""
Cash rollforward / positioning.

closing_balance = opening_balance + sum(transactions)

The simplest reconciliation control there is, but the one that catches
booking errors before they compound into a bigger cash break later.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_rollforward_data(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def rollforward(opening_balance: float, transactions: list[float]) -> float:
    """Closing balance for a single account."""
    return opening_balance + sum(transactions)


def rollforward_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute closing balances for every account in a long-format
    DataFrame with columns: account, opening_balance, txn_number, amount.
    """
    results = []
    for account, group in df.groupby("account", sort=False):
        opening = group["opening_balance"].iloc[0]
        closing = rollforward(opening, group["amount"].tolist())
        results.append(
            {
                "account": account,
                "opening_balance": opening,
                "total_activity": closing - opening,
                "closing_balance": closing,
            }
        )
    return pd.DataFrame(results)
