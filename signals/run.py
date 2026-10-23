"""CLI: synthetic validation or locally cached Yahoo historical research."""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
from src.data_loader import synthetic_fixture, download_prices, align_rates
from src.backtest import Config,walk_forward_signals,execute
from src.metrics import performance,block_bootstrap,deflated_sharpe

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['demo','historical'],default='demo')
    parser.add_argument('--start',default='2019-01-01');parser.add_argument('--end',default='2026-10-22')
    parser.add_argument('--rates-csv',type=Path)
    parser.add_argument('--distribution-yields-csv',type=Path,help='Point-in-time decimal yields, date index and ticker columns')
    parser.add_argument('--hypothetical-shorts',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    out=args.output or Path('results')/args.mode;out.mkdir(parents=True,exist_ok=True)
    if args.mode=='demo':
        prices,values,rates,yields=synthetic_fixture()
        label='SYNTHETIC VALIDATION — NOT INDIAN MARKET PERFORMANCE'
    else:
        prices,values=download_prices(Path('data/raw'),args.start,args.end)
        # Index is never traded and its volume is not used as stock liquidity.
        prices=prices.drop(columns=['^CNXREALTY'],errors='ignore');values=values.reindex_like(prices)
        coverage=pd.DataFrame([{'ticker':c,'rows':int(prices[c].count()),
            'first':str(prices[c].first_valid_index()),'last':str(prices[c].last_valid_index())} for c in prices])
        coverage.to_csv(out/'coverage.csv',index=False)
        # Common observed endpoint avoids fabricating returns after a stale feed.
        last=min(prices[c].last_valid_index() for c in prices if prices[c].count()>=252)
        prices=prices.loc[:last].dropna(how='all');values=values.reindex_like(prices)
        rates=align_rates(args.rates_csv,prices.index) if args.rates_csv else None
        yields=pd.read_csv(args.distribution_yields_csv,index_col=0,parse_dates=True) if args.distribution_yields_csv else None
        label='HISTORICAL RESEARCH — HYPOTHETICAL BORROW / VENDOR ADJUSTED PRICES'
    cfg=Config(hypothetical_shorts=args.hypothetical_shorts)
    variants={};trial_metrics=[];base_log=None;base_trace=None;base_targets=None
    for entry in [1.5,2.,2.5]:
        c=replace(cfg,entry_z=entry)
        targets,log,trace=walk_forward_signals(prices,c,rates,yields)
        ledger=execute(prices,values,targets,c)
        # Exclude the training warm-up and include all subsequent zero/cash days.
        ledger=ledger.iloc[c.train:]
        variants[str(entry)]=ledger
        m=performance(ledger.net_return.to_numpy())
        trial_metrics.append(dict(entry_z=entry,**m))
        if entry==2.:base_log,base_trace,base_targets=log,trace,targets
    base=variants['2.0'];r=base.net_return.to_numpy()
    daily_srs=[m['sharpe']/np.sqrt(252) if m['sharpe'] is not None else float('nan') for m in trial_metrics]
    metrics=performance(r)
    summary=dict(label=label,mode=args.mode,period_start=str(base.index[0].date()),period_end=str(base.index[-1].date()),
                 config=asdict(cfg),rates_enabled=rates is not None,yield_spread_enabled=yields is not None,
                 metrics=metrics,bootstrap=block_bootstrap(r),dsr=deflated_sharpe(r,daily_srs),
                 trial_registry=trial_metrics,transaction_cost=float(base.transaction_cost.sum()),
                 borrow_cost=float(base.borrow_cost.sum()),turnover=float(base.turnover.sum()),
                 final_gross_exposure=float(base.gross_exposure.iloc[-1]),
                 selected_folds=int(base_log['selected'].sum()) if not base_log.empty else 0,
                 input_sha256=hashlib.sha256(prices.to_csv().encode()).hexdigest())
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    base.to_csv(out/'ledger.csv');base_log.to_csv(out/'selection_audit.csv',index=False)
    base_trace.to_csv(out/'signal_trace.csv',index=False)
    pd.DataFrame(trial_metrics).to_csv(out/'trial_registry.csv',index=False)
    pd.DataFrame({k:v.net_return for k,v in variants.items()}).to_csv(out/'variant_returns.csv')
    cost_rows=[]
    for slip in [5.,10.,25.]:
        ledger=execute(prices,values,base_targets,replace(cfg,slippage_bps=slip)).iloc[cfg.train:]
        cost_rows.append(dict(slippage_bps=slip,**performance(ledger.net_return.to_numpy())))
    pd.DataFrame(cost_rows).to_csv(out/'cost_sensitivity.csv',index=False)
    # Count the two additional cost variants too; the 10bp base is not counted twice.
    daily_srs += [m['sharpe']/np.sqrt(252) if m['sharpe'] is not None else float('nan')
                  for m in cost_rows if m['slippage_bps']!=10.]
    summary['dsr']=deflated_sharpe(r,daily_srs)
    summary['cost_sensitivity']=cost_rows
    summary['trial_count_including_cost_stress']=5
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    plot(base,base_trace,out,label)
    print(json.dumps(summary,indent=2))

def plot(ledger: pd.DataFrame,trace: pd.DataFrame,out: Path,label: str) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    r=ledger.net_return
    w=(1+r).cumprod();dd=w/np.maximum.accumulate(np.r_[1.,w.to_numpy()])[1:]-1
    rolling=r.rolling(63).mean()/r.rolling(63).std()*np.sqrt(252)
    fig,axs=plt.subplots(3,1,figsize=(11,9),sharex=True,constrained_layout=True)
    fig.suptitle(label+'\nPredeclared entry z = 2.0; net of stated frictions',fontsize=12,fontweight='bold')
    axs[0].plot(w.index,w,color='#156d68');axs[0].axhline(1,color='#999999',ls='--',lw=.7);axs[0].set_ylabel('Growth of 1 INR')
    axs[1].fill_between(dd.index,dd*100,0,color='#b56a44',alpha=.7);axs[1].set_ylabel('Drawdown (%)')
    axs[2].plot(rolling.index,rolling,color='#315b88');axs[2].set_ylabel('63-day Sharpe')
    if not trace.empty and (trace.regime>=0).any():
        t=trace.set_index(pd.to_datetime(trace.date)).reindex(ledger.index)
        for ax in axs:
            lo,hi=ax.get_ylim()
            ax.fill_between(t.index,lo,hi,where=t.regime_size.fillna(1)<.75,color='#d6a663',alpha=.12)
        axs[0].text(.01,.95,'Shading: filtered rate-risk size < 0.75',transform=axs[0].transAxes,va='top',fontsize=8)
    for ax in axs:ax.grid(alpha=.2)
    fig.savefig(out/'tear_sheet.png',dpi=150);fig.savefig(out/'tear_sheet.svg');plt.close(fig)

if __name__=='__main__':main()
