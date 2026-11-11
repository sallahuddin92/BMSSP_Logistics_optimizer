"""Small guards for scientific summary definitions and immutable input parsing."""
import unittest
from experiment import quantiles
class AnalysisTests(unittest.TestCase):
 def test_nearest_rank_tails_and_even_p50(self):
  self.assertEqual(quantiles(list(range(1,51))),{'p50':25,'p95':48,'p99':50})
 def test_quantiles_order_independent(self):
  self.assertEqual(quantiles([8,2,4,1]),quantiles([1,2,4,8]))
if __name__=='__main__':unittest.main()
