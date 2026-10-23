# Real Assets: Fundamentals & Relative Value

[Open the research dashboard](https://anjaney336.github.io/portfolio/research/integrated-real-assets-research/) · [Earlier component methodology](docs/PRE_CONSOLIDATION.md)

## Research question and scope
Brings the Embassy REIT/Manyata memo and Excel model into the listed-property research repository. A disclosure-availability gate keeps fundamental analysis separate from historical signals when the information was not yet public.

## Results
Reported values reconcile to INR491.616 NAV per unit. The apparent 10.90% discount uses different dates and is not a tradable signal. The historical relative-value baseline remains negative after costs.

## Calculation conventions
NAV/unit = (GAV + other assets − other liabilities − gross debt) / units, with explicit crore-to-INR conversion. A decision date earlier than any required release date is rejected. Historical signal, expected-shortfall overlay and synthetic execution outputs remain separately identified.

## Data and sources
Embassy FY2026 valuation package: observation 31 March 2026, release 27 April. Q1 FY2027 supplemental databook: observation 30 June, release 30 July. Accessed 22 October 2026; complete URLs and pages in fundamentals.py and the memo.

## Reproduce
Python 3.12. Install `requirements.txt`, then run `python reproduce.py`. Default tests/research run offline; historical runs need the local authorized cache. New entry point: `fundamentals.py`. Add `--prices /path/to/prices.csv` for historical strategy/derivative experiments.

## Verification
59 tests across the consolidated reproduction command. CI runs the same command. See ENGINEERING.md for boundaries and release checks. The dashboard displays bundled reports; change its view selector to compare analyses, and download CSV/JSON evidence.

## Limits
The dated Embassy case is not a current valuation. It is not joined into old signals with hindsight. Historical short availability and execution remain assumptions; overlay scaling is not a full order-level rerun.

## Lineage and authorship
Consolidates existing research modules; original repositories remain as history. This is AI-assisted portfolio research, not code represented as deployed at a financial institution.

## Wealth-policy extension

[Read the fictional household IPS and goal-funding review](WEALTH_POLICY.md). Three assumed allocations, 2,000 shared paths, fees, rebalancing, inflation and shock-timing stress. Six new tests. This is a synthetic planning case, not a client recommendation.

## SQL and statistical research workflow

[SQL, statsmodels/SciPy, stochastic processes, hypothesis tests and Git lineage](QUANT_METHODS.md). Run `python quant_data_audit.py` for a synthetic SQL-to-backtest parity audit; see the dedicated GitHub Actions workflow for commit-linked outputs.
