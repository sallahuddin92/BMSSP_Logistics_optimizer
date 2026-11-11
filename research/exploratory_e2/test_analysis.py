import collections,unittest
from quality import q
class AnalysisTests(unittest.TestCase):
 def test_signed_quantiles_not_clamped(self):
  self.assertEqual(q([-100,-10,0,1])['p50'],-10)
 def test_nearest_rank_p99_n60_is_maximum(self):
  self.assertEqual(q(list(range(60)))['p99'],59)
 def test_balanced_orders(self):
  orders=[[(n+r)%4 for n in [0,1,3,2]] for r in range(4)]
  for slot in range(4):self.assertEqual({o[slot] for o in orders},set(range(4)))
  pairs=collections.Counter((a,b) for o in orders for a,b in zip(o,o[1:]))
  self.assertEqual(len(pairs),12);self.assertTrue(all(n==1 for n in pairs.values()))
if __name__=='__main__':unittest.main()
