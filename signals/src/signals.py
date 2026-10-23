"""Train-only cointegration diagnostics and causal state-space signals."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.tsa.stattools import coint, adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen

def ou_half_life(spread: np.ndarray) -> float:
    """Discrete AR(1) estimate: exact half-life = -ln(2)/ln(phi).

    phi outside (0,1) is not a stable, nonoscillating OU discretization.
    It is rejected rather than taking abs() to manufacture mean reversion.
    """
    s = np.asarray(spread, dtype=float)
    if len(s)<20 or not np.isfinite(s).all() or np.std(s)<1e-10: return float('inf')
    phi = np.linalg.lstsq(np.column_stack([np.ones(len(s)-1),s[:-1]]),s[1:],rcond=None)[0][1]
    return float(-np.log(2)/np.log(phi)) if 0<phi<1 else float('inf')

def cointegration_diagnostics(y: np.ndarray, x: np.ndarray) -> dict:
    """Both tests use log-price levels; EG p-values drive Holm selection.

    Johansen is reported as a diagnostic, not an extra optimization criterion.
    Unit-root pretests are reported because I(1) is an assumption, not a fact.
    """
    if len(y)<100 or not np.isfinite(y).all() or not np.isfinite(x).all():
        raise ValueError('At least 100 complete finite observations required')
    alpha,beta = np.linalg.lstsq(np.column_stack([np.ones(len(x)),x]),y,rcond=None)[0]
    residual = y-alpha-beta*x
    eg = coint(y,x,trend='c',maxlag=1,autolag=None)
    jo = coint_johansen(np.column_stack([y,x]),det_order=0,k_ar_diff=1)
    return dict(alpha=float(alpha),beta=float(beta),eg_p=float(eg[1]),
                johansen_trace=float(jo.lr1[0]),johansen_95=float(jo.cvt[0,1]),
                adf_y_p=float(adfuller(y,maxlag=1,autolag=None)[1]),
                adf_x_p=float(adfuller(x,maxlag=1,autolag=None)[1]),
                half_life=ou_half_life(residual),residual_std=float(np.std(residual,ddof=1)))

def holm_accept(pvalues: list[float], alpha: float = .05) -> list[bool]:
    """Holm step-down controls training-window family-wise error."""
    p = np.asarray(pvalues)
    result = np.zeros(len(p),dtype=bool)
    for rank,idx in enumerate(np.argsort(p)):
        if p[idx] > alpha/(len(p)-rank): break
        result[idx]=True
    return result.tolist()

@dataclass
class KalmanHedge:
    """Random-walk intercept/slope with a causal one-observation update."""
    state: np.ndarray
    covariance: np.ndarray
    observation_variance: float
    process_variance: float = 1e-7

    def update(self, x: float, y: float) -> tuple[float,float,float]:
        h = np.array([1.,x])
        prior = self.covariance + np.eye(2)*self.process_variance
        innovation = y-h@self.state
        variance = float(h@prior@h+self.observation_variance)
        gain = prior@h/variance
        self.state = self.state+gain*innovation
        # Joseph form keeps covariance symmetric/PSD under finite precision.
        ident = np.eye(2)-np.outer(gain,h)
        self.covariance = ident@prior@ident.T+np.outer(gain,gain)*self.observation_variance
        return float(innovation),float(self.state[1]),float(np.sqrt(variance))

def trailing_zscore(series: pd.Series, window: int) -> pd.Series:
    """Current observed value versus strictly prior rolling mean and std."""
    hist = series.shift(1).rolling(window,min_periods=window)
    return (series-hist.mean())/hist.std(ddof=1).replace(0,np.nan)

def yield_spread_zscore(distribution_yield: pd.Series, gsec_yield: pd.Series,
                        window: int = 60) -> pd.Series:
    """Distribution yield less government-bond yield; NOT a property cap rate."""
    return trailing_zscore(distribution_yield-gsec_yield,window)
