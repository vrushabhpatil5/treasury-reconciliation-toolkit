# Treasury Reconciliation Toolkit

A small Python toolkit that automates the three reconciliation tasks that
come up constantly in fund accounting, treasury, and middle-office
operations roles — the ones usually done by hand with VLOOKUP/INDEX-MATCH,
PivotTables, and a rollforward tab in Excel:

1. **Wire / cash reconciliation** — match an internal ledger against a bank
   or custodian statement, and classify every line as a clean match or a
   specific type of break.
2. **Transaction summary** — total activity by currency, entity, or any
   other dimension (the SUMIFS/PivotTable step).
3. **Cash rollforward** — opening balance + the week's transactions =
   closing balance, per account.

The goal isn't novelty — it's showing the actual daily mechanics of an
operations/reconciliation seat, done in code instead of a spreadsheet, with
tests that prove it's correct.

## Why this exists

This started as an Excel practice test for treasury-analyst interviews
(the `Ex1`/`Ex2`/`Ex3` scenarios below). The sample data and expected
results in this repo are taken directly from that workbook, so the tests
are checked against known-correct, hand-verified answers rather than
invented numbers.

## What it catches

The wire reconciliation engine does a **full outer join** on the reference
key, not a one-directional lookup, so it surfaces both directions of break:

| Status | Meaning |
|---|---|
| `Match` | Ref, currency, and amount agree on both sides |
| `Amount Mismatch` | Same ref, same currency, different amount |
| `Currency Mismatch` | Same ref, different currency |
| `Not Found in Bank` | Ledger has the line, bank statement doesn't |
| `Not Found in Ledger` | Bank has the line, ledger doesn't (e.g. an unbooked bank fee) |

A plain VLOOKUP from ledger → bank only ever catches the first three; it
silently misses anything that only exists on the bank side. This is the
same gap real reconciliations have to account for.

## Project layout

```
treasury-reconciliation-toolkit/
├── data/                       # sample CSVs (from the source workbook)
│   ├── ledger.csv
│   ├── bank_statement.csv
│   ├── wire_transactions.csv
│   └── cash_rollforward.csv
├── src/reconciliation/
│   ├── wire_reconciliation.py  # match + break classification + aged exception report
│   ├── transaction_summary.py  # groupby summaries by any dimension
│   └── cash_rollforward.py     # opening balance -> closing balance
├── tests/                      # pytest, checked against the workbook's own solutions
├── reports/                    # generated output lands here (gitignored)
├── app.py                      # Streamlit dashboard
└── main.py                     # CLI
```

## Usage

### Dashboard (Streamlit)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens a browser-based dashboard with three tabs:

- **Wire Reconciliation** — summary metrics (total lines, matches, breaks,
  match rate), a color-coded results table (green = match, yellow = amount/
  currency mismatch, red = missing from one side), a status filter, and an
  aged-exceptions view with a breaks-by-age chart and CSV download.
- **Transaction Summary** — totals by currency/entity with bar charts, plus
  the raw transaction log.
- **Cash Rollforward** — opening → closing balance per account, with a
  chart and CSV download.

You can either use the bundled sample data or upload your own ledger/bank/
transactions/rollforward CSVs from the sidebar (same column layout as the
files in `data/`).

### CLI

```bash
pip install -r requirements.txt

# Reconcile ledger vs bank statement, write full results + aged exceptions
python main.py recon --as-of 2026-07-10

# Summarize wire transactions by currency and entity
python main.py summary --by currency entity

# Cash rollforward per account
python main.py rollforward
```

Each command prints a summary to the console and writes a CSV to `reports/`.

Sample `recon` output:

```
Reconciled 15 lines.
status
Match                  11
Amount Mismatch         1
Currency Mismatch       1
Not Found in Bank       1
Not Found in Ledger     1
```

## Tests

```bash
pip install -r requirements.txt
pytest
```

All expected values in `tests/` are pulled directly from the solved
version of the source workbook — this isn't just testing that the code
runs, it's testing that it reproduces a hand-verified reconciliation.

## Extending it

Ideas for taking this further:
- Swap the CSV inputs for a live feed (custodian SFTP drop, API pull) on a
  schedule.
- Add a tolerance band by currency instead of one global tolerance.
- Turn the aged-exceptions CSV into a small dashboard (Streamlit/FastAPI)
  for reviewing and annotating breaks instead of reading a flat file.
- Add multi-leg matching for intercompany transfers that show up as two
  separate ledger entries.

## About

Built as an educational/portfolio project to practice reconciliation
workflows relevant to fund accounting, treasury, and middle-office
operations roles. Sample data is fictional (originally drawn from a
practice workbook), not real financial data.

Connect with me on [LinkedIn](https://www.linkedin.com/in/vrushabh-patil-finance/) —
happy to talk through the design or take feedback.
