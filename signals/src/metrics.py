"""Return diagnostics, block-bootstrap intervals and selection correction."""
from __future__ import annotations
import math
import numpy as np
from scipy.stats import norm, skew, kurtosis

def performance(returns: np.ndarray, periods: int = 252) -> dict:
    r=np.asarray(returns,float)
    if len(r)<2 or not np.isfinite(r).all() or (r<=-1).any():
        raise ValueError('Finite returns above -100% required')
    wealth=np.r_[1.,np.cumprod(1+r)]
    drawdown=wealth/np.maximum.accumulate(wealth)-1
    cagr=float(wealth[-1]**(periods/len(r))-1)
    sd=r.std(ddof=1)
    downside=np.sqrt(np.mean(np.minimum(r,0)**2))
    maxdd=float(-drawdown.min())
    return dict(observations=len(r),total_return=float(wealth[-1]-1),cagr=cagr,
                sharpe=float(r.mean()/sd*np.sqrt(periods)) if sd>1e-12 else None,
                sortino=float(r.mean()/downside*np.sqrt(periods)) if downside>1e-12 else None,
                max_drawdown=maxdd,calmar=cagr/maxdd if maxdd>1e-12 else None,
                volatility=float(sd*np.sqrt(periods)))

def deflated_sharpe(returns: np.ndarray, trial_sharpes_daily: list[float]) -> dict:
    """Bailey/Lopez de Prado 2014: daily SR units, Pearson kurtosis.

    The caller must supply EVERY evaluated strategy variant, including discarded
    ones. Correlated variants and serially correlated returns weaken calibration.
    This is a diagnostic under the paper's approximation, not proof of alpha.
    """
    r=np.asarray(returns,float); trials=np.asarray(trial_sharpes_daily,float)
    if len(r)<30 or len(trials)<2 or not np.isfinite(trials).all() or r.std(ddof=1)<1e-12:
        return {'probability':None,'reason':'Need variable returns and >=2 trials with defined Sharpe; never replace an undefined trial with zero'}
    sr=float(r.mean()/r.std(ddof=1)); n=len(trials); gamma=np.euler_gamma
    benchmark=float(trials.std(ddof=1)*((1-gamma)*norm.ppf(1-1/n)+gamma*norm.ppf(1-1/(n*math.e))))
    denominator=1-skew(r,bias=False)*sr+(kurtosis(r,fisher=False,bias=False)-1)*sr**2/4
    if denominator<=0: return {'probability':None,'reason':'Invalid estimated SR variance'}
    z=(sr-benchmark)*np.sqrt(len(r)-1)/np.sqrt(denominator)
    return dict(probability=float(norm.cdf(z)),daily_sr=sr,expected_max_daily_sr=benchmark,
                trials=n,assumption='Approximate independent-trial / IID-return calibration')

def block_bootstrap(returns: np.ndarray, draws: int = 1000, block: int = 20,
                    seed: int = 336) -> dict:
    """Circular moving-block bootstrap preserves within-block dependence."""
    r=np.asarray(returns,float)
    if not 1<=block<=len(r) or draws<10: raise ValueError('Invalid bootstrap configuration')
    rng=np.random.default_rng(seed); stats=[]
    for _ in range(draws):
        starts=rng.integers(0,len(r),math.ceil(len(r)/block))
        idx=np.concatenate([(s+np.arange(block))%len(r) for s in starts])[:len(r)]
        m=performance(r[idx]); stats.append([m['cagr'],m['sharpe'],m['max_drawdown']])
    a=np.asarray(stats,float)
    return {k:[float(v) if np.isfinite(v) else None for v in np.nanquantile(a[:,i],[.025,.5,.975])]
            for i,k in enumerate(['cagr','sharpe','max_drawdown'])}
