import unittest
from experiments import execute,market,paired_interval
class ExecutionTests(unittest.TestCase):
 def test_hand_calculation(self):
  x=execute([{'mid':100,'spread':1,'depth':[10,10,10]}],'immediate',parent=10,fee_bps=0)
  self.assertEqual(x['implementation_shortfall_bps'],100);self.assertEqual(x['vwap'],101)
 def test_no_overfill_and_monotonic(self):
  for seed in range(20):
   for p in ['immediate','twap']:
    x=execute(market(seed),p);q=[r['filled'] for r in x['trace']]
    self.assertEqual(q,sorted(q));self.assertLessEqual(max(q),100)
 def test_missed_execution_opportunity(self):
  x=execute([{'mid':100,'spread':2,'depth':[10]*3},{'mid':105,'spread':2,'depth':[10]*3}],'twap',parent=10,fee_bps=0,limit_offset=0)
  self.assertEqual(x['filled'],0);self.assertEqual(x['opportunity_ticks'],50);self.assertEqual(x['implementation_shortfall_bps'],500)
 def test_constant_market_cost(self):
  rows=[{'mid':10000,'spread':1,'depth':[200]*3}]*20
  a=execute(rows,'immediate');b=execute(rows,'twap')
  self.assertAlmostEqual(a['implementation_shortfall_bps'],b['implementation_shortfall_bps'])
 def test_fee_monotonicity(self):
  for p in ['twap','immediate']:
   self.assertGreater(execute(market(4),p,fee_bps=10)['implementation_shortfall_bps'],execute(market(4),p,fee_bps=0)['implementation_shortfall_bps'])
 def test_pairing_zero_interval(self):
  self.assertEqual(paired_interval([0]*100),{'mean':0,'lower_95':0,'upper_95':0})
 def test_reproducibility(self):
  self.assertEqual(market(4),market(4));self.assertEqual(execute(market(4),'twap'),execute(market(4),'twap'))
 def test_invalid_policy(self):
  with self.assertRaises(ValueError):execute(market(4),'magic')
if __name__=='__main__':unittest.main()
