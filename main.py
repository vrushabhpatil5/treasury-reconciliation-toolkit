"""
CLI entry point for the treasury reconciliation toolkit.

Examples
--------
    python main.py recon
    python main.py recon --as-of 2026-07-10
    python main.py summary --by currency entity
    python main.py rollforward
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))

from reconciliation import (  # noqa: E402
    generate_exception_report,
    load_bank_statement,
    load_ledger,
    reconcile,
    rollforward_all,
    summarize,
)
from reconciliation.transaction_summary import load_transactions  # noqa: E402
from reconciliation.cash_rollforward import load_rollforward_data  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = Path(__file__).parent / "reports"


def cmd_recon(args: argparse.Namespace) -> None:
    ledger = load_ledger(DATA_DIR / "ledger.csv")
    bank = load_bank_statement(DATA_DIR / "bank_statement.csv")
    result = reconcile(ledger, bank)

    REPORTS_DIR.mkdir(exist_ok=True)
    full_path = REPORTS_DIR / "reconciliation_full.csv"
    result.to_csv(full_path, index=False)

    as_of = pd.Timestamp(args.as_of) if args.as_of else None
    exceptions = generate_exception_report(result, as_of=as_of)
    exceptions_path = REPORTS_DIR / "exceptions_aged.csv"
    exceptions.to_csv(exceptions_path, index=False)

    print(f"Reconciled {len(result)} lines.")
    print(result["status"].value_counts().to_string())
    print(f"\nFull results  -> {full_path}")
    print(f"Aged breaks   -> {exceptions_path}")


def cmd_summary(args: argparse.Namespace) -> None:
    txns = load_transactions(DATA_DIR / "wire_transactions.csv")
    REPORTS_DIR.mkdir(exist_ok=True)
    for dim in args.by:
        table = summarize(txns, dim)
        out_path = REPORTS_DIR / f"summary_by_{dim}.csv"
        table.to_csv(out_path, index=False)
        print(f"\n=== Total by {dim} ===")
        print(table.to_string(index=False))
        print(f"-> {out_path}")


def cmd_rollforward(args: argparse.Namespace) -> None:
    df = load_rollforward_data(DATA_DIR / "cash_rollforward.csv")
    result = rollforward_all(df)
    REPORTS_DIR.mkdir(exist_ok=True)
    out_path = REPORTS_DIR / "cash_rollforward_result.csv"
    result.to_csv(out_path, index=False)
    print(result.to_string(index=False))
    print(f"\n-> {out_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Treasury reconciliation toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    p_recon = sub.add_parser("recon", help="Reconcile ledger vs bank statement")
    p_recon.add_argument("--as-of", help="As-of date (YYYY-MM-DD) for aging breaks")
    p_recon.set_defaults(func=cmd_recon)

    p_summary = sub.add_parser("summary", help="Summarize wire transactions")
    p_summary.add_argument(
        "--by", nargs="+", default=["currency", "entity"], help="Dimensions to group by"
    )
    p_summary.set_defaults(func=cmd_summary)

    p_roll = sub.add_parser("rollforward", help="Compute cash rollforward per account")
    p_roll.set_defaults(func=cmd_rollforward)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
