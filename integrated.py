"""Connect published signal returns, causal tail-risk control and execution stress."""
from pathlib import Path
import csv,json,math,statistics,hashlib,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'execution'))
from experiments import market,execute

def throttle(returns,window=252,budget=.005):
 if window<2 or budget<=0 or not all(math.isfinite(x) and x>-1 for x in returns):raise ValueError('invalid risk inputs')
 weights=[]
 for t in range(len(returns)):
  if t<window:weights.append(1.);continue
  losses=sorted([-x for x in returns[t-window:t]],reverse=True);es=max(0.,statistics.mean(losses[:max(1,math.ceil(.05*window))]));weights.append(min(1.,budget/max(es,1e-8)))
 return weights

def overlay(returns,weights,extra_bps=0):
 if len(returns)!=len(weights) or extra_bps<0:raise ValueError('invalid overlay')
 previous=1.;out=[]
 for r,w in zip(returns,weights):
  if not 0<=w<=1:raise ValueError('invalid scale')
  out.append((1+w*r)*(1-abs(w-previous)*extra_bps/10000)-1);previous=w
 return out

def metrics(r):
 nav=np.cumprod(1+np.array(r));peak=np.maximum.accumulate(np.r_[1,nav])[1:]
 return {'total_return':float(nav[-1]-1),'max_drawdown':float(np.min(nav/peak-1)),'annualized_vol':float(np.std(r,ddof=1)*np.sqrt(252))}

def run():
 source=ROOT/'signals/results/historical/ledger.csv';rows=list(csv.DictReader(source.open()));returns=[float(r['net_return']) for r in rows];scale=throttle(returns);trials=[]
 for seed in range(100):
  for policy in ['immediate','twap']:
   x=execute(market(seed),policy);trials.append(dict(seed=seed,policy=policy,shortfall_bps=x['implementation_shortfall_bps'],fill_rate=x['fill_rate']))
 # Execution simulator is a conditional stress layer, not historical fill calibration.
 scenarios={str(bp):metrics(overlay(returns,scale,bp)) for bp in [0,5,10,25]};out=ROOT/'results'
 with (out/'integrated_ledger.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['date','published_net_return','lagged_risk_scale','overlay_net_return_10bp']);w.writerows(zip([r['date'] for r in rows],returns,scale,overlay(returns,scale,10)))
 with (out/'execution_bridge.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=trials[0]);w.writeheader();w.writerows(trials)
 report={'observations':len(rows),'baseline':metrics(returns),'risk_overlay_cost_scenarios':scenarios,'scaled_days':sum(w<1 for w in scale),'execution_stress_runs':len(trials),'sources':[{'name':'Published listed-property strategy ledger; Yahoo-based upstream prices','link':'https://github.com/Anjaney336/india-realestate-quant-backtest/blob/main/results/historical/ledger.csv','access_date':'2026-10-24','sha256':hashlib.sha256(source.read_bytes()).hexdigest()},{'name':'Synthetic execution snapshots','link':'https://github.com/Anjaney336/quant-execution-lab/blob/main/experiments.py','access_date':'2026-10-24'}],'assumptions':{'ES_window':252,'tail_fraction':.05,'daily_tail_budget':.005,'warmup_scale':1.,'extra_cost_bps':[0,5,10,25]},'limitations':'Counterfactual return-scaling overlay, not an order-level rerun. Baseline already includes costs; extra costs apply to scale changes. Execution snapshots are synthetic and not calibrated to Indian property stocks. No claim of profitable alpha.'}
 (out/'summary.json').write_text(json.dumps(report,indent=2));fig,axs=plt.subplots(2,1,figsize=(10,6),sharex=True)
 axs[0].plot(np.cumprod(1+np.array(returns)),label='Published baseline');axs[0].plot(np.cumprod(1+np.array(overlay(returns,scale,10))),label='ES overlay + 10bp scale cost');axs[0].set(ylabel='Growth of 1',title='Signals → causal tail risk → cost stress');axs[0].legend();axs[1].plot(scale);axs[1].set(ylabel='Risk scale',xlabel='Historical evaluation observation');fig.tight_layout();fig.savefig(out/'integrated.svg');print(json.dumps(report,indent=2))
if __name__=='__main__':run()
