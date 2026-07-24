"""
Transaction summary / aggregation.

Python equivalent of the SUMIFS-by-dimension or PivotTable an analyst
builds to check totals by currency, entity, counterparty, etc. before
they get booked or reported.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_transactions(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


def summarize(
    df: pd.DataFrame,
    by: str | list[str],
    amount_col: str = "amount_usd_eq",
) -> pd.DataFrame:
    """
    Sum ``amount_col`` grouped by one or more dimensions.

    Equivalent to =SUMIFS(amount_range, dim_range, dim_value) repeated for
    every distinct value of ``dim``, or a PivotTable with ``by`` in Rows
    and ``amount_col`` in Values.
    """
    cols = [by] if isinstance(by, str) else by
    result = (
        df.groupby(cols, as_index=False)[amount_col]
        .sum()
        .rename(columns={amount_col: "total"})
        .sort_values(cols)
        .reset_index(drop=True)
    )
    return result


def summarize_multi(
    df: pd.DataFrame,
    dimensions: list[str],
    amount_col: str = "amount_usd_eq",
) -> dict[str, pd.DataFrame]:
    """Convenience wrapper: one summary table per dimension in ``dimensions``."""
    return {dim: summarize(df, dim, amount_col) for dim in dimensions}
