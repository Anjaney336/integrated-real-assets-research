import unittest,sqlite3
import numpy as np,pandas as pd
from quant_data_audit import database,panel,diagnostics
from src.data_loader import synthetic_fixture
class SQLTests(unittest.TestCase):
    def test_roundtrip_and_lag(self):
        p=synthetic_fixture(n=300)[0]
        with database(p) as c:
            q,r=panel(c,str(p.index[-1].date()))
            np.testing.assert_array_equal(p,q.reindex(columns=p.columns))
            a=r[r.symbol=='SYNTH_A'].simple_return.to_numpy()
            np.testing.assert_allclose(a[1:],p.SYNTH_A.pct_change().to_numpy()[1:])
    def test_primary_key(self):
        p=synthetic_fixture(n=300)[0]
        with database(p) as c:
            with self.assertRaises(sqlite3.IntegrityError):c.execute('INSERT INTO prices VALUES(?,?,?)',(str(p.index[0].date()),'SYNTH_A',100))
    def test_as_of(self):
        p=synthetic_fixture(n=300)[0]
        with database(p) as c:q,_=panel(c,str(p.index[99].date()))
        self.assertEqual(len(q),100)
    def test_missing_not_filled(self):
        p=synthetic_fixture(n=300)[0];p.iloc[5,0]=np.nan
        with database(p) as c:q,_=panel(c,str(p.index[-1].date()))
        self.assertTrue(pd.isna(q.iloc[5,0]))
    def test_future_data_does_not_change_training(self):
        p=synthetic_fixture(n=300)[0];q=p.copy();q.iloc[252:]*=2
        self.assertEqual(diagnostics(p),diagnostics(q))
    def test_bad_prices(self):
        p=synthetic_fixture(n=300)[0];p.iloc[3,0]=-1
        with self.assertRaises(ValueError):database(p)
