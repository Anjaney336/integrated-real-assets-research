from src.tail_diagnostics import quantile,rolling_tail
import pytest

def test_interpolated_quantile():assert quantile([0,10],.95)==9.5

def test_tail_forecast_excludes_current_and_future():
 a=[.001*i for i in range(30)];b=a.copy();b[20]=-.8
 x=rolling_tail(a,20)[0];y=rolling_tail(b,20)[0]
 assert x['var']==y['var'] and x['tail_mean']==y['tail_mean'] and y['breach']==1

def test_all_cash_ties():
 x=rolling_tail([0]*30,20)
 assert len(x)==10 and all(r['var']==0 and r['tail_mean']==0 and r['breach']==0 for r in x)

def test_tail_at_least_quantile():
 assert all(x['tail_mean']>=x['var'] for x in rolling_tail([(-1)**i*i/1000 for i in range(60)],20))

def test_scale_equivariance():
 a=[(-1)**i*i/1000 for i in range(60)]
 for x,y in zip(rolling_tail(a,20),rolling_tail([2*v for v in a],20)):
  assert y['var']==pytest.approx(2*x['var']) and y['breach']==x['breach']

def test_reject_nonfinite():
 with pytest.raises(ValueError):rolling_tail([float('nan')]*30,20)
