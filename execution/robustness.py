from pathlib import Path
import csv,json,statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiments import market,execute,paired_interval
out=Path(__file__).parent/'results';rows=[]
for depth_scale in [.5,1.,2.]:
 for fee in [0,1,5]:
  diffs=[];fills=[]
  for seed in range(100):
   path=market(seed)
   for x in path:x['depth']=[max(1,int(d*depth_scale)) for d in x['depth']]
   a=execute(path,'immediate',fee_bps=fee);b=execute(path,'twap',fee_bps=fee)
   diffs.append(b['implementation_shortfall_bps']-a['implementation_shortfall_bps']);fills.append((a['fill_rate'],b['fill_rate']))
  rows.append({'depth_scale':depth_scale,'fee_bps':fee,**paired_interval(diffs),'immediate_fill_rate':statistics.mean(x[0] for x in fills),'twap_fill_rate':statistics.mean(x[1] for x in fills)})
with (out/'robustness.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
fig,ax=plt.subplots(figsize=(9,4))
for fee in [0,1,5]:
 z=[x for x in rows if x['fee_bps']==fee];ax.errorbar([x['depth_scale'] for x in z],[x['mean'] for x in z],yerr=[[x['mean']-x['lower_95'] for x in z],[x['upper_95']-x['mean'] for x in z]],marker='o',capsize=3,label=f'{fee} bp fee')
ax.axhline(0,color='gray');ax.set(xlabel='Assumed displayed depth multiplier',ylabel='TWAP minus immediate shortfall (bp)',title='Synthetic execution robustness — 100 paired paths per cell');ax.legend();fig.tight_layout();fig.savefig(out/'robustness.svg');print('9 parameter cells / 1,800 policy executions; conditional paired intervals published')
