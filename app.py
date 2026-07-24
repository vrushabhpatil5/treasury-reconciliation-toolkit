"""
Streamlit dashboard for the Treasury Reconciliation Toolkit.

Run with:
    streamlit run app.py

Three views, one per module in src/reconciliation:
  - Wire Reconciliation : ledger vs bank, color-coded breaks, aged exceptions
  - Transaction Summary  : totals by currency / entity, with charts
  - Cash Rollforward     : opening -> closing balance per account
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from reconciliation import (  # noqa: E402
    generate_exception_report,
    load_bank_statement,
    load_ledger,
    reconcile,
    rollforward_all,
    summarize,
)
from reconciliation.cash_rollforward import load_rollforward_data  # noqa: E402
from reconciliation.transaction_summary import load_transactions  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"

STATUS_COLORS = {
    "Match": "#d4edda",
    "Amount Mismatch": "#fff3cd",
    "Currency Mismatch": "#fff3cd",
    "Not Found in Bank": "#f8d7da",
    "Not Found in Ledger": "#f8d7da",
}

st.set_page_config(
    page_title="Treasury Reconciliation Toolkit",
    page_icon="\U0001F4CA",
    layout="wide",
)


def style_status(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    def _color(val: str) -> str:
        bg = STATUS_COLORS.get(val, "")
        # Force black text: the pastel backgrounds are light regardless of
        # whether the app is rendered in Streamlit's light or dark theme,
        # and the dark theme's default white text is unreadable on them.
        return f"background-color: {bg}; color: #000000;"

    return df.style.map(_color, subset=["status"])


def load_csv_or_upload(
    label: str, default_path: Path, uploaded_file, loader
) -> pd.DataFrame:
    if uploaded_file is not None:
        return loader(uploaded_file)
    return loader(default_path)


# ---------------------------------------------------------------- sidebar --
st.sidebar.title("Treasury Reconciliation Toolkit")
st.sidebar.caption(
    "Wire reconciliation, transaction summary, and cash rollforward — "
    "the daily checks behind fund accounting / treasury / middle-office work."
)

st.sidebar.divider()
st.sidebar.subheader("Data")
st.sidebar.caption("Uses the bundled sample data by default. Upload your own CSVs to override.")

ledger_file = st.sidebar.file_uploader("Ledger CSV", type="csv", key="ledger")
bank_file = st.sidebar.file_uploader("Bank statement CSV", type="csv", key="bank")
txn_file = st.sidebar.file_uploader("Transactions CSV", type="csv", key="txns")
rollforward_file = st.sidebar.file_uploader("Cash rollforward CSV", type="csv", key="rollforward")

st.sidebar.divider()
as_of = st.sidebar.date_input("As-of date (for aging breaks)", value=date(2026, 7, 10))

# --------------------------------------------------------------- header ---
st.title("\U0001F4CA Treasury Reconciliation Toolkit")
st.caption(
    "Automates the ledger-vs-bank matching, transaction summaries, and cash "
    "rollforward normally done by hand in Excel with VLOOKUP, PivotTables, "
    "and a rollforward tab."
)

tab_recon, tab_summary, tab_rollforward = st.tabs(
    ["\U0001F50D Wire Reconciliation", "\U0001F4C8 Transaction Summary", "\U0001F4B5 Cash Rollforward"]
)

# ----------------------------------------------------- Wire Reconciliation --
with tab_recon:
    ledger = load_csv_or_upload("Ledger", DATA_DIR / "ledger.csv", ledger_file, load_ledger)
    bank = load_csv_or_upload(
        "Bank statement", DATA_DIR / "bank_statement.csv", bank_file, load_bank_statement
    )
    result = reconcile(ledger, bank)
    exceptions = generate_exception_report(result, as_of=pd.Timestamp(as_of))

    total = len(result)
    matches = int((result["status"] == "Match").sum())
    breaks = total - matches
    match_rate = (matches / total * 100) if total else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total lines", total)
    c2.metric("Clean matches", matches)
    c3.metric("Breaks", breaks, delta=f"-{breaks}" if breaks else None, delta_color="inverse")
    c4.metric("Match rate", f"{match_rate:.0f}%")

    st.divider()

    st.subheader("Reconciliation results")
    status_options = sorted(result["status"].unique())
    selected_statuses = st.multiselect(
        "Filter by status", options=status_options, default=status_options
    )
    filtered = result[result["status"].isin(selected_statuses)]
    st.dataframe(style_status(filtered), width="stretch", hide_index=True)

    st.subheader(f"Aged exceptions (as of {as_of})")
    if exceptions.empty:
        st.success("No open breaks — everything matched.")
    else:
        age_counts = exceptions["age_bucket"].value_counts().reindex(
            ["0-1 days", "2-5 days", "5+ days"], fill_value=0
        )
        col_table, col_chart = st.columns([2, 1])
        with col_table:
            st.dataframe(style_status(exceptions), width="stretch", hide_index=True)
        with col_chart:
            st.caption("Breaks by age")
            st.bar_chart(age_counts)

        csv_bytes = exceptions.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download aged exceptions (CSV)",
            data=csv_bytes,
            file_name="exceptions_aged.csv",
            mime="text/csv",
        )

# -------------------------------------------------------- Transaction Summary --
with tab_summary:
    txns = load_csv_or_upload(
        "Transactions", DATA_DIR / "wire_transactions.csv", txn_file, load_transactions
    )

    st.subheader("Totals by dimension")
    dims = [c for c in ["currency", "entity", "counterparty"] if c in txns.columns]
    chosen_dims = st.multiselect("Group by", options=dims, default=dims[:2])

    cols = st.columns(len(chosen_dims)) if chosen_dims else [st]
    for col, dim in zip(cols, chosen_dims):
        table = summarize(txns, dim)
        with col:
            st.caption(f"By {dim}")
            st.dataframe(table, width="stretch", hide_index=True)
            st.bar_chart(table.set_index(dim)["total"])

    st.divider()
    st.subheader("Raw transactions")
    st.dataframe(txns, width="stretch", hide_index=True)

# -------------------------------------------------------------- Cash Rollforward --
with tab_rollforward:
    rf_df = load_csv_or_upload(
        "Cash rollforward", DATA_DIR / "cash_rollforward.csv", rollforward_file, load_rollforward_data
    )
    result_rf = rollforward_all(rf_df)

    st.subheader("Opening → closing balance by account")
    st.dataframe(result_rf, width="stretch", hide_index=True)

    chart_df = result_rf.set_index("account")[["opening_balance", "closing_balance"]]
    st.bar_chart(chart_df)

    csv_bytes = result_rf.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download rollforward result (CSV)",
        data=csv_bytes,
        file_name="cash_rollforward_result.csv",
        mime="text/csv",
    )
