import unittest
import numpy as np
from wealth_policy import paths,evaluate
class WealthTests(unittest.TestCase):
    def test_zero_return_cashflows(self):
        z=evaluate(np.zeros((2,3,4)),[0,0,0,1],initial=100,contribution=10,goal_real=150,inflation=0,fee=0,cost=0)
        np.testing.assert_allclose(z['real_terminal'],130)
        self.assertEqual(z['summary']['mean_real_shortfall'],20)
    def test_fee_recurrence(self):
        z=evaluate(np.zeros((1,2,4)),[0,0,0,1],initial=100,contribution=0,inflation=0,fee=.1,cost=0)
        self.assertAlmostEqual(z['real_terminal'][0],81)
    def test_cost_and_conservation(self):
        z=evaluate(np.zeros((1,1,4)),[1,0,0,0],initial=0,contribution=100,inflation=0,fee=0,cost=.01)
        self.assertAlmostEqual(z['real_terminal'][0],99/1.01)
    def test_inflation(self):
        r=np.zeros((1,1,4));z=evaluate(r,[0,0,0,1],initial=110,contribution=0,inflation=.1,fee=0,cost=0)
        self.assertAlmostEqual(z['real_terminal'][0],100)
    def test_seed(self):np.testing.assert_array_equal(paths(n=2),paths(n=2))
    def test_invalid(self):
        with self.assertRaises(ValueError):evaluate(np.zeros((1,1,4)),[1,1,0,0])
        with self.assertRaises(ValueError):evaluate(np.full((1,1,4),-1),[1,0,0,0])
