# Engineering review

## Scope
This is an offline research system. The dashboard reads published calculation outputs; it does not trade, connect to a broker or promise investment returns. Model assumptions and data dates are part of each report.

## Boundaries
- Validate inputs before calculations; reject infeasible portfolios, dates or capacities.
- Keep source records and generated outputs distinct. Historical source prices are not redistributed.
- Keep historical replay separate from synthetic CI fixtures and do not select favourable output runs for publication.
- Treat timestamps as information-availability constraints, not merely chart labels.
- Preserve calculation ledgers and reconciliation residuals for debugging.

## Release checks
Run `python reproduce.py` from a clean Python 3.12 environment after installing requirements.txt. CI executes the same command. Inspect JSON assumptions and regenerate dashboard assets after changing results. All calculations use floating-point arithmetic with explicit tolerances; trading prices in the order-book module use integer ticks.

## Research-to-production gaps
No independently licensed institutional feed, broker integration, production risk limits, service monitoring, access controls, market-impact calibration, disaster recovery or external professional sign-off is present. These projects demonstrate selected engineering practices; they are not represented as systems deployed by an MNC. A production rollout would need those controls and independent review.

## Ownership
Prepared for Anjaney Malhotra with AI coding assistance. The author should reproduce and explain every claim, test and modelling assumption in interviews.
