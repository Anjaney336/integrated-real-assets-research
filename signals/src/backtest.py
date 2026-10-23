"""Walk-forward research signals and self-financing close-to-close ledger."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
import math
import numpy as np
import pandas as pd
from .data_loader import validate_panel
from .signals import cointegration_diagnostics, holm_accept, KalmanHedge, yield_spread_zscore
from .regime_hmm import RateRegime

@dataclass(frozen=True)
class Config:
    train: int = 252
    test: int = 63
    entry_z: float = 2.
    exit_z: float = .25
    stop_z: float = 4.
    max_gross: float = .8
    max_leg: float = .5
    initial_nav: float = 1_000_000.
    participation: float = .01
    brokerage_bps: float = 3.
    slippage_bps: float = 10.
    other_fees_bps: float = 2.
    stt_buy_bps: float = 10.
    stt_sell_bps: float = 10.
    borrow_annual: float = .06
    hypothetical_shorts: bool = False

    def validate(self) -> None:
        if self.train<100 or self.test<1: raise ValueError('Invalid walk-forward windows')
        if not 0<=self.exit_z<self.entry_z<self.stop_z: raise ValueError('Invalid thresholds')
        if not 0<self.max_gross<=1 or not 0<self.max_leg<=1: raise ValueError('Invalid leverage limits')
        if self.initial_nav<=0 or not 0<self.participation<=1: raise ValueError('Invalid capital/liquidity')
        vals=[self.brokerage_bps,self.slippage_bps,self.other_fees_bps,self.stt_buy_bps,self.stt_sell_bps,self.borrow_annual]
        if any(not np.isfinite(x) or x<0 for x in vals): raise ValueError('Invalid friction assumptions')

def walk_forward_signals(prices: pd.DataFrame, cfg: Config, rates: pd.Series | None = None,
                         distribution_yields: pd.DataFrame | None = None) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    """Fit on [t-train,t), generate signals on [t,t+test); no full-sample selection.

    Each rebalance evaluates all available pairs, applies Holm EG correction,
    rejects implausible hedge ratios/half-lives and selects smallest EG p-value.
    No pair meeting the screen means cash. Johansen remains a reported diagnostic.
    """
    cfg.validate(); prices=validate_panel(prices)
    targets=pd.DataFrame(0.,index=prices.index,columns=prices.columns)
    logs=[]; trace=[]
    yz={}
    if distribution_yields is not None:
        if rates is None: raise ValueError('Yield spread requires rate series')
        for col in prices:
            yz[col]=yield_spread_zscore(distribution_yields[col].reindex(prices.index),rates.reindex(prices.index))
    for begin in range(cfg.train,len(prices),cfg.test):
        end=min(begin+cfg.test,len(prices)); train=prices.iloc[begin-cfg.train:begin]
        diagnostics=[]
        for y,x in combinations(prices.columns,2):
            if train[[y,x]].isna().any().any(): continue
            try:
                d=cointegration_diagnostics(np.log(train[y].to_numpy()),np.log(train[x].to_numpy()))
                diagnostics.append(dict(y=y,x=x,**d))
            except (ValueError,np.linalg.LinAlgError): continue
        accepted=holm_accept([d['eg_p'] for d in diagnostics]) if diagnostics else []
        eligible=[]
        for d,passed in zip(diagnostics,accepted):
            d.update(train_start=str(train.index[0].date()),train_end=str(train.index[-1].date()),
                     test_start=str(prices.index[begin].date()),holm_pass=passed,selected=False)
            if passed and .2<d['beta']<5 and 2<=d['half_life']<=60 and d['residual_std']>1e-6:
                eligible.append(d)
        hmm=None
        if rates is not None:
            r=rates.reindex(prices.index)
            changes=r.iloc[begin-cfg.train:begin].diff().dropna()
            # Missing rates cannot be silently replaced with synthetic rates.
            if r.iloc[begin-cfg.train:begin].isna().any(): eligible=[]
            else:
                try: hmm=RateRegime().fit(changes.to_numpy())
                except ValueError: eligible=[]
        if not eligible:
            logs.extend(diagnostics)
            continue
        chosen=min(eligible,key=lambda d:d['eg_p']);chosen['selected']=True
        logs.extend(diagnostics)
        y,x=chosen['y'],chosen['x']
        k=KalmanHedge(np.array([chosen['alpha'],chosen['beta']]),np.eye(2)*1e-5,
                      chosen['residual_std']**2)
        side=0;held=0
        for pos in range(begin,end):
            date=prices.index[pos]
            if prices.loc[date,[y,x]].isna().any():
                side=0
                continue
            innovation,beta,_=k.update(float(np.log(prices.loc[date,x])),float(np.log(prices.loc[date,y])))
            z=innovation/chosen['residual_std']
            factor=1.;state=-1
            if hmm is not None:
                diff=r.iloc[pos]-r.iloc[pos-1]
                if not np.isfinite(diff): side=0;continue
                _,factor,state=hmm.update(float(diff))
            if not .2<beta<5: side=0
            elif side and (abs(z)<cfg.exit_z or abs(z)>cfg.stop_z or held>=math.ceil(2*chosen['half_life'])):
                side=0;held=0
            elif not side and cfg.entry_z<=abs(z)<cfg.stop_z:
                side=-int(np.sign(z));held=0
            if side:
                held+=1
                if distribution_yields is not None:
                    long_ticker=y if side>0 else x
                    spread_z=yz[long_ticker].iloc[pos]
                    factor*=float(.75+.25*np.tanh(spread_z)) if np.isfinite(spread_z) else 0.
                weights=np.array([side,-side*beta],float)
                weights*=cfg.max_gross/np.abs(weights).sum()*factor
                weights*=min(1.,cfg.max_leg/np.abs(weights).max())
                targets.loc[date,[y,x]]=weights
            trace.append(dict(date=str(date.date()),y=y,x=x,z=float(z),beta=float(beta),
                              side=side,regime=state,regime_size=factor))
    return targets,pd.DataFrame(logs),pd.DataFrame(trace)

def execute(prices: pd.DataFrame, traded_value: pd.DataFrame, targets: pd.DataFrame,
            cfg: Config, borrow_available: pd.DataFrame | None = None) -> pd.DataFrame:
    """Signal at close t -> trade at close t+1 -> first price P&L on t+2.

    Dollar holdings drift with price; turnover uses drifted holdings, not target
    differences. Common participation scaling preserves relative trade sizes.
    Missing held quotes fail closed rather than pretending a zero return.
    Cash earns zero; annual borrow charge uses calendar-day gaps / 365.
    """
    cfg.validate();p=validate_panel(prices)
    if not p.index.equals(targets.index) or list(p.columns)!=list(targets.columns):
        raise ValueError('Targets must align exactly')
    if not np.isfinite(targets.to_numpy()).all(): raise ValueError('Invalid targets')
    if (targets.abs().sum(axis=1)>cfg.max_gross+1e-9).any() or (targets.abs()>cfg.max_leg+1e-9).any().any():
        raise ValueError('Target exceeds exposure limits')
    v=traded_value.reindex_like(p)
    if borrow_available is not None:
        borrow_available=borrow_available.reindex(index=p.index,columns=p.columns).fillna(False)
    if (v<0).any().any(): raise ValueError('Negative traded value')
    adv=v.rolling(20,min_periods=20).mean().shift(1)
    returns=p.pct_change(fill_method=None)
    holdings=np.zeros(p.shape[1]);nav=cfg.initial_nav;rows=[]
    for t,date in enumerate(p.index):
        old_nav=nav
        ret=returns.iloc[t].to_numpy(float)
        held=np.abs(holdings)>1e-8
        if (~np.isfinite(ret[held])).any(): raise ValueError(f'Missing quote on held position: {date}')
        days=(date-p.index[t-1]).days if t else 0
        borrow=float(-np.minimum(holdings,0).sum()*cfg.borrow_annual*days/365)
        pnl=float(np.sum(holdings*np.nan_to_num(ret)))
        holdings*=1+np.nan_to_num(ret)
        nav+=pnl-borrow
        if nav<=0: raise ValueError('NAV exhausted')
        desired=targets.iloc[t-1].to_numpy(float).copy() if t else np.zeros(p.shape[1])
        if (desired<0).any() and not cfg.hypothetical_shorts:
            available=(borrow_available.iloc[t-1].reindex(p.columns).fillna(False).to_numpy(bool)
                       if borrow_available is not None and t else np.zeros(p.shape[1],bool))
            if ((desired<0)&~available).any(): desired[:]=0  # Reject whole pair, not only hedge.
        delta=desired*nav-holdings
        caps=adv.iloc[t].fillna(0).to_numpy()*cfg.participation
        caps[~np.isfinite(p.iloc[t].to_numpy())]=0
        need=np.abs(delta)>1e-8
        fill=min(1.,float(np.min(caps[need]/np.abs(delta[need])))) if need.any() else 1.
        delta*=fill
        turnover=float(np.abs(delta).sum())
        buy=float(np.maximum(delta,0).sum());sell=float(-np.minimum(delta,0).sum())
        cost=(turnover*(cfg.brokerage_bps+cfg.slippage_bps+cfg.other_fees_bps)+
              buy*cfg.stt_buy_bps+sell*cfg.stt_sell_bps)/10000
        holdings+=delta;nav-=cost
        if nav<=0: raise ValueError('Costs exhausted NAV')
        rows.append(dict(date=date,nav=nav,net_return=nav/old_nav-1,price_pnl=pnl,
                         transaction_cost=cost,borrow_cost=borrow,turnover=turnover,
                         gross_exposure=float(np.abs(holdings).sum()/nav),fill_fraction=fill))
    return pd.DataFrame(rows).set_index('date')
