"""Public-filing reconciliation with an explicit information-availability gate."""
from datetime import date
from pathlib import Path
import json
import math

SOURCES=[{'name':'Embassy FY2026 earnings/valuation package','url':'https://www.embassyofficeparks.com/wp-content/uploads/2026/06/press_release__-_final.pdf','observation_date':'2026-03-31','release_date':'2026-04-27','access_date':'2026-10-22','page':38},{'name':'Embassy Q1 FY2027 supplemental databook','url':'https://www.embassyofficeparks.com/wp-content/uploads/2026/09/se_filing_-__press_release_and_earnings_presentation.pdf','observation_date':'2026-06-30','release_date':'2026-07-30','access_date':'2026-10-22','pages':[55,67,68]}]

def available(as_of,release_date):
    if date.fromisoformat(release_date)>date.fromisoformat(as_of):
        raise ValueError('disclosure unavailable at decision date')

def nav_per_unit(gav,assets,liabilities,debt,units):
    if not all(math.isfinite(x) for x in [gav,assets,liabilities,debt,units]) or units<=0:
        raise ValueError('invalid NAV inputs')
    return (gav+assets-liabilities-debt)*1e7/units

def snapshot(as_of='2026-10-24'):
    for source in SOURCES:available(as_of,source['release_date'])
    nav=nav_per_unit(70540,5202,6757,22385,947893743)
    return {'as_of':as_of,'march_nav_per_unit':nav,'june_price':438.04,'cross_date_discount':1-438.04/nav,'net_debt_rounding_residual_million':233491-14697-218795,'principal_minus_amortized_debt_million':234039-233491,'sources':SOURCES,'warning':'March NAV and June price are not contemporaneous. July disclosure cannot be used for a June backtest. This snapshot does not create a tradable convergence signal.'}

def main():
    result=snapshot();out=Path(__file__).parent/'results'
    (out/'fundamentals.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
