"""SQL-to-backtest parity and training-only statistical diagnostics."""
from pathlib import Path
import sqlite3,json,hashlib,os,sys
import numpy as np
import pandas as pd
import scipy,statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox,het_arch
from statsmodels.tsa.stattools import adfuller
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).parent/'signals'))
from src.data_loader import synthetic_fixture,validate_panel
from src.signals import cointegration_diagnostics
from src.backtest import Config,walk_forward_signals,execute

SQL='''WITH ordered AS (
 SELECT date,symbol,price,
 LAG(price) OVER(PARTITION BY symbol ORDER BY date) AS previous_price
 FROM prices WHERE date <= :as_of
)
SELECT date,symbol,price,price/previous_price-1.0 AS simple_return
FROM ordered ORDER BY date,symbol;'''

def database(frame):
    p=validate_panel(frame);c=sqlite3.connect(':memory:')
    c.execute('CREATE TABLE prices(date TEXT NOT NULL,symbol TEXT NOT NULL,price REAL NOT NULL CHECK(price>0),PRIMARY KEY(date,symbol))')
    rows=[(str(date.date()),symbol,float(price)) for date,row in p.iterrows() for symbol,price in row.items() if pd.notna(price)]
    with c:c.executemany('INSERT INTO prices VALUES(?,?,?)',rows)
    return c

def panel(c,as_of):
    records=pd.read_sql_query(SQL,c,params={'as_of':as_of})
    p=records.pivot(index='date',columns='symbol',values='price');p.index=pd.to_datetime(p.index)
    return p,records

def diagnostics(prices,train=252):
    p=prices.iloc[:train];x=np.log(p.iloc[:,1].to_numpy());y=np.log(p.iloc[:,0].to_numpy())
    fit=sm.OLS(y,sm.add_constant(x)).fit();resid=fit.resid
    # HAC describes contemporaneous return association; it is not a predictive signal.
    rx=np.diff(x);ry=np.diff(y);hac=sm.OLS(ry,sm.add_constant(rx)).fit(cov_type='HAC',cov_kwds={'maxlags':5})
    eg=cointegration_diagnostics(y,x)
    return dict(training_start=str(p.index[0].date()),training_end=str(p.index[-1].date()),training_rows=len(p),
        log_level_ols={'intercept':float(fit.params[0]),'beta':float(fit.params[1])},cointegration=eg,
        returns_hac={'beta':float(hac.params[1]),'standard_error':float(hac.bse[1]),'pvalue':float(hac.pvalues[1]),'maxlags':5,'interpretation':'contemporaneous descriptive regression; not forecast performance'},
        adf_first_differences={'x_p':float(adfuller(rx,maxlag=1,autolag=None)[1]),'y_p':float(adfuller(ry,maxlag=1,autolag=None)[1])},
        residual_ljung_box_p=float(acorr_ljungbox(resid,lags=[10],return_df=True).lb_pvalue.iloc[0]),
        residual_arch_lm_p=float(het_arch(resid,nlags=5)[1]),
        scipy_normaltest_residual_p=float(stats.normaltest(resid).pvalue),
        pearson_return_correlation=float(stats.pearsonr(rx,ry).statistic))

def main():
    root=Path(__file__).parent;out=root/'results/sql_audit';out.mkdir(exist_ok=True)
    p,values,_,_=synthetic_fixture();c=database(p);q,records=panel(c,str(p.index[-1].date()));q=q.reindex(columns=p.columns)
    np.testing.assert_allclose(p.to_numpy(),q.to_numpy(),rtol=0,atol=0)
    cfg=Config(hypothetical_shorts=True)
    targets,selection,trace=walk_forward_signals(q,cfg);ledger=execute(q,values,targets,cfg)
    direct_targets,_,_=walk_forward_signals(p,cfg);direct=execute(p,values,direct_targets,cfg)
    delta=float(np.max(np.abs(ledger.net_return-direct.net_return)))
    if delta!=0:raise AssertionError('SQL backtest parity failed')
    d=diagnostics(q);selection.to_csv(out/'selection.csv',index=False);ledger.to_csv(out/'ledger.csv');records.to_csv(out/'sql_returns.csv',index=False)
    (out/'queries.sql').write_text(SQL)
    curve=(1+ledger.net_return.iloc[cfg.train:]).cumprod()
    sourcefiles=['quant_data_audit.py','signals/src/data_loader.py','signals/src/signals.py','signals/src/backtest.py']
    report=dict(source={'name':'Synthetic fixture: common random walk plus AR(1) residual and independent random walk','url':'https://github.com/Anjaney336/integrated-real-assets-research/blob/main/signals/src/data_loader.py','access_date':'2026-10-24','seed':336,'observations':1008,'assets':3,'ar1_phi_assumed':.88},
        sql={'rows':len(records),'primary_key':['date','symbol'],'missing_policy':'no interpolation/backfill; missing rows omitted and remain missing on pivot','as_of':str(p.index[-1].date()),'ledger_max_absolute_difference':delta},
        diagnostics=d,backtest={'net_total_return':float(curve.iloc[-1]-1),'evaluation_rows':len(curve),'assumed_shorts':True,'note':'Synthetic known-structure fixture; not empirical alpha. All fees/borrow use existing Config assumptions.'},
        lineage={'git_commit':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID'),'context':'CI commit when available; local runs leave Git identity null rather than borrowing an unrelated parent repository SHA','input_sha256':hashlib.sha256(p.to_csv().encode()).hexdigest(),'code_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sourcefiles},'numpy':np.__version__,'scipy':scipy.__version__},
        limitations='Diagnostic p-values are reported, not tuned into new entry rules. Ljung-Box null is no serial correlation; ARCH null is no conditional heteroskedasticity. Normality is not required for all model uses. Holm in the existing selector controls the pair family per training window, not all researcher choices or repeated windows. SQL as-of is observation-date filtering, not a historical-vintage database.')
    (out/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    y=np.log(q.iloc[:252,0]);x=np.log(q.iloc[:252,1]);a=d['log_level_ols'];spread=y-a['intercept']-a['beta']*x
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    axes[0].plot(spread);axes[0].set(title='Training-only fitted log spread',ylabel='Residual log-price units');axes[0].tick_params(axis='x',rotation=30)
    axes[1].plot(curve);axes[1].set(title='SQL-fed synthetic backtest; costs included',ylabel='Growth of 1');axes[1].tick_params(axis='x',rotation=30)
    fig.tight_layout();fig.savefig(out/'sql_research.svg');plt.close(fig);c.close()
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
