"""Causal historical-loss diagnostics for the published strategy, not REIT-wide risk."""
from pathlib import Path
import csv,json,math,hashlib

def quantile(values,p):
    if not values or not 0<=p<=1:raise ValueError('invalid quantile')
    x=sorted(values);i=(len(x)-1)*p;l=int(i);h=min(l+1,len(x)-1)
    return x[l]+(x[h]-x[l])*(i-l)

def rolling_tail(returns,window=252,confidence=.95):
    if type(window) is not int or window<20 or not .5<confidence<1:raise ValueError('invalid settings')
    if any(not math.isfinite(x) or x<=-1 for x in returns):raise ValueError('invalid simple return')
    output=[]
    for i in range(window,len(returns)):
        losses=[-x for x in returns[i-window:i]]
        var=quantile(losses,confidence);tail=[x for x in losses if x>=var]
        output.append({'index':i,'var':var,'tail_mean':sum(tail)/len(tail),'loss':-returns[i],'breach':int(-returns[i]>var)})
    return output

def report(returns):
    rows=rolling_tail(returns)
    active=[x for x in returns if x!=0]
    return {'observations':len(returns),'zero_return_days':len(returns)-len(active),'forecast_days':len(rows),'breaches':sum(r['breach'] for r in rows),'breach_frequency':sum(r['breach'] for r in rows)/len(rows) if rows else None,'last_forecast':rows[-1] if rows else None,'worst_daily_return':min(returns) if returns else None}


def main():
    root=Path(__file__).resolve().parents[1];path=root/'results/historical/ledger.csv'
    with path.open() as f:ledger=list(csv.DictReader(f))
    returns=[float(r['net_return']) for r in ledger];result=report(returns)
    # Explicit loop avoids counting delimiter fragments when measuring flat-return spells.
    longest=run=0
    for x in returns:run=run+1 if x==0 else 0;longest=max(longest,run)
    result['longest_zero_run']=longest
    result.update({'source':'Published derived historical strategy ledger; underlying vendor-adjusted Yahoo Finance data','source_url':'https://github.com/Anjaney336/india-realestate-quant-backtest/blob/main/results/historical/ledger.csv','underlying_source':'https://finance.yahoo.com/','access_date':'2026-10-24','ledger_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'settings':{'trailing_observations':252,'confidence':.95,'quantile':'linear interpolation','tail_mean':'mean losses >= quantile, ties included','breach':'realized loss strictly greater than forecast VaR'},'interpretation':'Strategy-return risk only, not a REIT valuation or a capital-charge model. Zero-return periods can collapse the trailing distribution; retain these days and report clustering. Tail mean with ties is a diagnostic, not exact fixed-mass Expected Shortfall. No calibration pass/fail or forward predictive validity is claimed.'})
    out=root/'results/risk';out.mkdir(exist_ok=True)
    (out/'tail_diagnostics.json').write_text(json.dumps(result,indent=2))
    rows=rolling_tail(returns)
    with (out/'rolling_tail.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['date','var','tail_mean','loss','breach']);w.writeheader()
        for x in rows:w.writerow({'date':ledger[x['index']]['date'],**{k:v for k,v in x.items() if k!='index'}})
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
