"""Train-window Gaussian HMM with FORWARD-ONLY held-out inference."""
from __future__ import annotations
import numpy as np
from scipy.special import logsumexp
from hmmlearn.hmm import GaussianHMM

class RateRegime:
    def __init__(self, states: int = 2, seed: int = 336):
        if states not in (2,3): raise ValueError('Use 2 or 3 states')
        self.states,self.seed = states,seed

    def fit(self, changes: np.ndarray) -> 'RateRegime':
        a=np.asarray(changes,float)
        if len(a)<100 or not np.isfinite(a).all() or a.std()<1e-10:
            raise ValueError('Insufficient variation in training rate changes')
        self.mean,self.scale=float(a.mean()),float(a.std())
        x=((a-self.mean)/self.scale).reshape(-1,1)
        self.model=GaussianHMM(n_components=self.states,covariance_type='diag',n_iter=200,
                               tol=1e-4,random_state=self.seed,min_covar=1e-3).fit(x)
        self.order=np.argsort(self.model.means_[:,0])
        # Lower mean change is named falling-yield, not a causal policy label.
        self.factors=np.empty(self.states)
        self.factors[self.order]=np.linspace(1.,.5,self.states)
        self.prob=self.model.startprob_.copy()
        for value in a: self.update(float(value))
        return self

    def update(self, change: float) -> tuple[np.ndarray,float,int]:
        if not np.isfinite(change): raise ValueError('Finite rate change required')
        x=(change-self.mean)/self.scale
        mu=self.model.means_[:,0]
        variance=self.model.covars_.reshape(self.states,-1)[:,0]
        predictive=self.prob@self.model.transmat_
        logp=np.log(np.maximum(predictive,1e-300))-.5*(np.log(2*np.pi*variance)+(x-mu)**2/variance)
        self.prob=np.exp(logp-logsumexp(logp))
        return self.prob.copy(),float(self.prob@self.factors),int(np.argmax(self.prob))
