# Fictional household: investment policy and goal-funding review

Educational case, not a real client, suitability assessment or personalised recommendation.

## Mandate and assumptions

- Investable wealth: INR20 lakh; emergency reserve held outside this model. Fixed year-end contribution: INR2.4 lakh. Goal: INR50 lakh in today's purchasing power in 10 years.
- Assumed inflation: 5%; separately stressed to 7%. No withdrawals during the horizon. No leverage or derivatives. Annual rebalancing; 0.5% annual fee and 0.1% gross trading-notional cost.
- Hypothetical risk brief: capital loss would matter; do not select a policy solely by the highest simulated funding rate. Risk willingness and capacity are deliberately not inferred from age or wealth.
- Constraints still requiring a real interview: income stability, debts, emergency liquidity, existing property concentration, tax residence/status, dependants, investment experience and restrictions. No policy is declared suitable without these facts.
- Governance: annual review and review after a material change in circumstances. Reconfirm goal, cash needs and risk capacity; document approval before implementing a changed allocation. No trades are executed by this research.

## Mathematics and accounting

Annual asset returns are exp(mu − 0.5 sigma² + sigma Z) − 1 with correlated standard normals. The mu values are lognormal drift assumptions, not arithmetic expected-return estimates. All four asset inputs and correlation matrix are in results/wealth_summary.json. Returns are independent across years, with fixed correlations and no calibrated market data.

After market returns and management fees, the year-end contribution enters cash. Target holdings are w × post-cost wealth. Solve W + c Σ|w_i W − pretrade_i| = pretrade wealth by bisection. This charges cost on both sides of a rebalance and explicitly reconciles wealth. Real terminal wealth = nominal wealth/(1+inflation)^10. Funding frequency = fraction of paths meeting the real goal; shortfall = max(goal − real wealth, 0).

## Recorded results

| Policy | Equity / bonds / REIT / cash | Goal funding | Median real wealth | 5th percentile real wealth |
|---|---|---:|---:|---:|
| defensive | 25 / 55 / 10 / 10% | 6.4% | INR37.53 lakh | INR27.96 lakh |
| balanced | 50 / 30 / 15 / 5% | 22.6% | INR39.18 lakh | INR24.39 lakh |
| growth | 70 / 15 / 10 / 5% | 29.1% | INR39.59 lakh | INR22.09 lakh |

## Client-facing conclusion

The illustrated plan has a material funding gap. More equity increases upside but does not make the goal secure and lowers poor-outcome wealth. Before choosing investments, discuss higher contributions, a longer horizon or a smaller goal, and confirm the household can tolerate losses. These simulations cannot tell us the client's willingness or capacity to take risk.

The early/late stress cases replace one year's returns with equity −35%, bonds −8%, REIT −30%, cash +2%. They test shock timing; they are not a pure permutation of an identical return sequence. The contribution-inclusive wealth chart must not be presented as investment performance. No tax, default, illiquidity, withdrawals, changing correlations or existing property exposure is modelled. A listed REIT is not interchangeable with directly owned property.

## Evidence and sources

Synthetic data source: wealth_policy.py in this repository; generated/accessed 24 October 2026, seed 20261024, 2,000 shared paths per policy. Exact assumptions and CSV hash: results/wealth_summary.json. Trial outcomes: results/wealth_trials.csv. Reproduce with python wealth_policy.py; run six accounting/input/reproducibility tests with python -m unittest test_wealth_policy -v.

IPS reference, accessed 24 October 2026: https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-iii-c . Used to frame objectives, constraints and reassessment; the case does not imply CFA affiliation or regulatory qualification.
