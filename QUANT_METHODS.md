# SQL, time-series statistics and reproducible statistical arbitrage

## What is implemented

This is an extension of the existing relative-value engine, not a new trading track record. SQL loading and diagnostics are demonstrated on a named synthetic fixture. The repository's separate historical results retain their own source manifests and limitations.

### SQL data engineering

`quant_data_audit.py` creates SQLite prices with a composite (date, symbol) primary key and a positive-price constraint. Parameterised inserts and a parameterised as-of query avoid string-built SQL values. A CTE and LAG window function compute returns partitioned by symbol, ordered by observation date. Missing observations are not filled. LAG means previous observed price: across a missing row it is a gap return, not necessarily one trading day's return. The execution panel pivots the original prices and retains missing cells.

`results/sql_audit/queries.sql` is the executed query. 3,024 records round-trip without changing prices. The SQL-fed backtest has zero maximum absolute daily-return difference from the direct-input backtest. Six new tests check date filtering, duplicates, missingness, bad prices, return calculations and future-data mutation. Observation-date filtering is not a point-in-time corporate-action or revision database.

### Regression and time-series diagnostics

Fit log(Y_t) = a + beta log(X_t) + e_t using only the initial 252 observations. The hedge residual is e_t; its mean-reversion properties require testing. High correlation or a high regression fit does not establish cointegration.

Existing `signals/src/signals.py` reports Engle–Granger (null: no cointegration), Johansen trace diagnostics and ADF level tests (null: unit root). The new audit adds ADF first-difference tests, Ljung–Box residual autocorrelation, ARCH-LM diagnostics and SciPy normality testing. A separate contemporaneous return regression uses statsmodels OLS with HAC standard errors, five lags. Its coefficient describes association, not predictive accuracy or causality.

The training example gives beta approximately 0.949, raw Engle–Granger p=0.0426 and Johansen trace 13.98 below its 5% critical value 15.49. Tests disagree. The raw p-value is not a selection decision: the existing walk-forward selector applies Holm correction to the pair family, and additionally checks hedge-ratio/half-life conditions. Failure to reject a unit root does not prove that a series is I(1).

Ljung–Box and ARCH-LM applied to fitted level residuals are exploratory diagnostics; serial dependence can distort interpretation of an ARCH test. Strong rejection is not automatically a signal. The audit reports these diagnostics and does not tune entry thresholds to them. Normality tests also do not establish IID errors.

### Stochastic-process mathematics

The fixture combines a common random walk with an AR(1) residual: e_t = 0.88 e_(t−1) + epsilon_t. An independent random walk acts as another candidate series. This construction deliberately includes a mean-reverting component and cannot demonstrate empirical alpha.

For an estimated AR(1) coefficient phi in (0,1), half-life = −ln(2)/ln(phi) observations. The OU connection is phi = exp(−kappa Δt), so kappa = −ln(phi)/Δt. Values outside (0,1) are not treated as a stable, nonoscillating OU discretisation. The example fitted half-life is about 6.63 observations; this is an estimate, not the known generating coefficient.

The existing Kalman hedge uses a random-walk intercept/slope state with a causal observation update and Joseph covariance form. Its assumptions and process variance are explicit. A changing hedge ratio is not proof of changing economic equilibrium.

### Statistical-arbitrage decision rule and execution

Existing engine: 252-observation training windows, 63-observation test blocks, pairwise cointegration screens with Holm correction, lagged spread signals, exposure caps and transaction/borrow costs. No eligible pair means cash. Train-only selection and future-mutation tests protect against look-ahead; hypothetical short availability remains an assumption.

Spread = log(Y) − a − beta log(X). A z-score scales spread/innovation by an estimated mean and volatility. The log-space hedge coefficient is not itself a share count; targets and the execution ledger handle dollar exposures, portfolio drift and fees. Read `signals/src/backtest.py` for timing and sizing.

The SQL audit's 756 post-training observations produce approximately +0.698% net cumulative return in the constructed synthetic fixture. This is not annualised, not an Indian-market result and not evidence of alpha. The existing negative historical results are not replaced by this demonstration. Holm controls the candidate family within a training window; it does not correct every repeated window or researcher choice.

## Git and reproducibility workflow

1. Change an implementation on a feature branch, with the hypothesis and expected invariant described in the commit/PR. Peer review is a workflow recommendation, not a claim that independent review occurred.
2. Run `python -m unittest test_quant_data_audit -v` and `python quant_data_audit.py`; the full existing reproduction command remains available.
3. `.github/workflows/sql-research.yml` runs checks on push and pull_request and uploads result artifacts. CI records GITHUB_SHA and GITHUB_RUN_ID, input hash and code hashes. Local runs leave Git identity null instead of claiming an unrelated enclosing checkout.
4. Compare selection logs, ledger and diagnostic outputs before accepting a research change. Dependency versions are pinned in requirements.txt. An accepted test run does not establish production readiness.

## Sources

- Synthetic generator: https://github.com/Anjaney336/integrated-real-assets-research/blob/main/signals/src/data_loader.py ; seed 336; generated/accessed 24 October 2026. Exact input hash in results/sql_audit/summary.json. No market-data scraping is required by this audit.
- statsmodels cointegration: https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.coint.html
- Multiple testing: https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html
- SciPy correlation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html
Documentation accessed 24 October 2026; installed package versions are pinned, and current documentation may describe a newer release. Definitions support methodology, not empirical performance claims.
