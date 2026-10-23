import unittest
from integrated import throttle,overlay
class IntegratedTests(unittest.TestCase):
 def test_causality(self):
  r=[.01,-.01]*300;s=r.copy();s[400:]=[-.5]*200;self.assertEqual(throttle(r)[:401],throttle(s)[:401])
 def test_identity(self):self.assertEqual(overlay([.01,-.02],[1,1]),[.010000000000000009,-.020000000000000018])
 def test_zero_risk(self):self.assertTrue(all(w==1 for w in throttle([0]*600)))
 def test_risk_cap(self):self.assertAlmostEqual(throttle([-.02]*300)[-1],.25)
 def test_cost_direction(self):self.assertLess(overlay([.01],[.5],10)[0],overlay([.01],[.5],0)[0])
 def test_invalid(self):
  with self.assertRaises(ValueError):overlay([.1],[1.1])
if __name__=='__main__':unittest.main()
