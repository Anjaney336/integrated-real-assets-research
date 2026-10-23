from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.data_loader import validate_panel, align_rates, synthetic_fixture, trailing_distribution_yield
from src.signals import ou_half_life, holm_accept, KalmanHedge, trailing_zscore, cointegration_diagnostics
from src.regime_hmm import RateRegime
from src.backtest import Config, execute, walk_forward_signals
from src.metrics import performance, deflated_sharpe, block_bootstrap

def simple_market(n=30):
    idx=pd.bdate_range('2025-01-01',periods=n)
    p=pd.DataFrame({'A':100.,'B':100.},index=idx)
    return p,p*1e7,p*0

def test_no_price_backfill():
    p,_,_=simple_market();p.iloc[:3,0]=np.nan
    assert validate_panel(p).iloc[:3,0].isna().all()

def test_bad_panel():
    p,_,_=simple_market()
    with pytest.raises(ValueError):validate_panel(pd.concat([p,p]))
    p.iloc[0,0]=0
    with pytest.raises(ValueError):validate_panel(p)

def test_rate_publication_and_staleness(tmp_path):
    file=tmp_path/'rates.csv'
    file.write_text('observation_date,available_date,yield_pct\n2025-01-01,2025-01-03,7\n')
    r=align_rates(file,pd.date_range('2025-01-01',periods=12))
    assert r.iloc[:2].isna().all() and r.iloc[2]==.07 and np.isnan(r.iloc[-1])

def test_distribution_announcement_not_future():
    idx=pd.to_datetime(['2024-01-02','2025-01-02','2025-01-03'])
    p=pd.DataFrame({'A':100.},index=idx)
    ev=pd.DataFrame({'ticker':['A','A'],'ex_date':['2024-01-01','2025-01-02'],
                     'available_date':['2024-01-01','2025-01-03'],'cash_per_unit':[1,4]})
    y=trailing_distribution_yield(ev,p)
    assert y.iloc[1,0]==0 and y.iloc[2,0]==.04

def test_ou_known_ar1():
    rng=np.random.default_rng(1);s=np.zeros(10000)
    for i in range(1,len(s)):s[i]=.9*s[i-1]+rng.normal()
    assert 5<ou_half_life(s)<8
    assert np.isinf(ou_half_life(np.ones(30)))

def test_holm():
    assert holm_accept([.001,.02,.2])==[True,True,False]
    assert holm_accept([.03,.04,.2])==[False,False,False]

def test_zscore_prior_window():
    s=pd.Series([1.,2.,3.,100.])
    assert trailing_zscore(s,3).iloc[-1]==98

def test_kalman_covariance_psd():
    k=KalmanHedge(np.array([0.,1.]),np.eye(2),.01)
    for x in np.linspace(4,6,30):
        k.update(x,x+.1)
        assert np.linalg.eigvalsh(k.covariance).min()>-1e-10

def test_cointegration_fixture():
    p,_,_,_=synthetic_fixture(504)
    d=cointegration_diagnostics(np.log(p.SYNTH_A),np.log(p.SYNTH_B))
    assert d['eg_p']<.05 and d['johansen_trace']>d['johansen_95']

def test_next_close_execution():
    p,v,w=simple_market();w.iloc[20:,0]=.4
    p.iloc[21:,0]=110;p.iloc[22:,0]=121
    c=replace(Config(),brokerage_bps=0,slippage_bps=0,other_fees_bps=0,stt_buy_bps=0,stt_sell_bps=0,borrow_annual=0)
    r=execute(p,v,w,c)
    assert r.iloc[21].net_return==0
    assert r.iloc[22].net_return==pytest.approx(.04)

def test_ledger_cost_identity():
    p,v,w=simple_market();w.iloc[20:,0]=.4
    r=execute(p,v,w,Config())
    assert r.iloc[-1]['nav']==pytest.approx(1e6+r.price_pnl.sum()-r.transaction_cost.sum()-r.borrow_cost.sum())
    assert r.transaction_cost.sum()>0

def test_short_gate_and_borrow_cost():
    p,v,w=simple_market();w.iloc[20:]=[.4,-.4]
    assert execute(p,v,w,Config()).turnover.sum()==0
    r=execute(p,v,w,replace(Config(),hypothetical_shorts=True))
    assert r.borrow_cost.sum()>0

def test_liquidity_uses_prior_adv():
    p,v,w=simple_market();v[:]=1000;w.iloc[20:]=[.4,-.4]
    r=execute(p,v,w,replace(Config(),hypothetical_shorts=True))
    assert r.turnover.max()<=20.00001
    v.iloc[21:]=1e9
    r2=execute(p,v,w,replace(Config(),hypothetical_shorts=True))
    assert r2.iloc[21].turnover==pytest.approx(r.iloc[21].turnover)

def test_missing_held_quote_rejected():
    p,v,w=simple_market();w.iloc[20:,0]=.4;p.iloc[23,0]=np.nan
    with pytest.raises(ValueError,match='Missing quote'):execute(p,v,w,Config())

def test_future_mutation_does_not_change_signals():
    p,v,r,y=synthetic_fixture(504)
    cfg=Config(train=252,test=63)
    a,_,_=walk_forward_signals(p,cfg)
    changed=p.copy();changed.iloc[430:]*=np.linspace(1,3,len(p)-430)[:,None]
    b,_,_=walk_forward_signals(changed,cfg)
    pd.testing.assert_frame_equal(a.iloc[:430],b.iloc[:430])

def test_hmm_forward_probability_and_causality():
    rng=np.random.default_rng(3);a=rng.normal(0,.001,300)
    h=RateRegime().fit(a[:200]);g=RateRegime().fit(a[:200])
    for x in a[200:250]:
        p,size,_=h.update(x);q,_,_=g.update(x)
        assert p.sum()==pytest.approx(1) and .5<=size<=1
        np.testing.assert_allclose(p,q)
    frozen=g.prob.copy()
    h.update(10.)
    np.testing.assert_array_equal(g.prob,frozen)

def test_hmm_known_emissions():
    from types import SimpleNamespace
    h=RateRegime();h.mean=0.;h.scale=1.
    h.model=SimpleNamespace(means_=np.array([[-1.],[1.]]),covars_=np.array([[[.1]],[[.1]]]),
                            transmat_=np.array([[.9,.1],[.1,.9]]))
    h.prob=np.array([.5,.5]);h.factors=np.array([1.,.5])
    p,size,_=h.update(-1.)
    assert p[0]>.99 and size>.99

def test_drawdown_includes_initial_capital():
    assert performance(np.array([-.1,0.]))['max_drawdown']==pytest.approx(.1)

def test_dsr_penalizes_trials():
    rng=np.random.default_rng(8);r=rng.normal(.0005,.01,500)
    a=deflated_sharpe(r,[-.05,.05])
    b=deflated_sharpe(r,list(np.linspace(-.1,.1,100)))
    assert b['probability']<a['probability']

def test_bootstrap_repeatable():
    r=np.random.default_rng(1).normal(0,.01,100)
    assert block_bootstrap(r,draws=50)==block_bootstrap(r,draws=50)

def test_zero_returns_metrics():
    assert performance(np.zeros(50))['sharpe'] is None
    assert deflated_sharpe(np.zeros(50),[0,0])['probability'] is None
