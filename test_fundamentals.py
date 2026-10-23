import unittest
from fundamentals import available,nav_per_unit,snapshot

class FundamentalTests(unittest.TestCase):
    def test_unavailable_disclosure(self):
        with self.assertRaises(ValueError):snapshot('2026-06-30')
    def test_release_day(self):available('2026-07-30','2026-07-30')
    def test_nav_units(self):self.assertAlmostEqual(nav_per_unit(10,2,1,3,1000000),80)
    def test_reported_reconciliation(self):self.assertAlmostEqual(snapshot()['march_nav_per_unit'],491.616,places=3)
    def test_debt_rounding(self):self.assertEqual(snapshot()['net_debt_rounding_residual_million'],-1)
    def test_zero_units(self):
        with self.assertRaises(ValueError):nav_per_unit(1,0,0,0,0)

if __name__=='__main__':unittest.main()
