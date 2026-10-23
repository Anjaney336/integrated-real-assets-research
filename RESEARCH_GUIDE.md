# Real Assets: Fundamentals & Relative Value — calculation and decision guide

Do public fundamentals and historical relative-value signals support the same investment decision?

## Reconcile the filing

Convert crore to INR and reconcile gross asset value, other assets, liabilities, gross debt and units. NAV per unit is approximately INR491.62 for the dated filing case.

## Respect publication dates

A March valuation and June market price do not form a same-date discount. Required disclosures must be available on the decision date. The apparent 10.90% cross-date discount is context, not an actionable backtest signal.

## Evaluate the signal separately

Compare the costed baseline with the expected-shortfall risk overlay on the same observations. The baseline remains negative; a smaller drawdown does not establish alpha.

## Connect to a decision

Use the memo for fundamental diligence and the ledger for statistical diagnostics. Do not retrospectively join later filings into earlier trades.

## Calculation

NAV/unit = (gross asset value + other assets − other liabilities − gross debt) × 10,000,000 / units; information release date ≤ decision date.

## Graph interpretation

### Relative-value risk overlay

Compare return and drawdown paths on the same observations. The overlay changes exposure and costs; a smaller drawdown can come with less participation. This is a risk-control experiment, not evidence of positive excess return.

### Historical annual diagnostics

Annual diagnostics show variation across calendar periods. Inspect weak years as well as strong ones. A few favourable periods cannot establish a stable relative-value edge.

## Review evidence

fundamentals.py · test_fundamentals.py · embassy_case/ · results/integrated_ledger.csv

Demonstrates: Public-filings diligence, information timing, relative-value research and tail-risk analysis.

All values are existing recorded outputs. No new performance experiment was run for this presentation update. Refer to the README and result JSON for data sources, access dates, units and limitations.
