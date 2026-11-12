"""Real retained fixture checks; never records traces or fabricates road events."""
import copy,json,unittest
from availability import ROOT,sha
from analyze import readlines
from trace_data import table,mapping,overlap_states,mapped,bounds
class EvidenceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.events,_=table(ROOT/'probe-os-signpost.xml');cls.states,_=table(ROOT/'probe-thread-state.xml')
  cls.anchors=[r for r in readlines(ROOT/'probe-query-spans.jsonl') if r['kind']=='anchor']
 def test_real_reference_resolution(self):
  anchors=[r for r in self.events if r.get('name')=='E3ClockAnchor']
  self.assertEqual(len(anchors),6);self.assertEqual({r['process'] for r in anchors},{312})
  self.assertEqual({r['thread'] for r in anchors},{6935332})
 def test_affine_mapping_respects_every_independent_bracket(self):
  m=mapping(self.anchors,self.events)
  for a in m['anchors']:
   self.assertLessEqual(mapped(m,a['raw_before_ns']),a['trace_ns'])
   self.assertGreaterEqual(mapped(m,a['raw_after_ns']),a['trace_ns'])
   lo,hi=bounds(m,a['raw_before_ns'])
   self.assertLessEqual(lo,mapped(m,a['raw_before_ns']));self.assertGreaterEqual(hi,mapped(m,a['raw_before_ns']))
 def test_missing_anchor_invalidates_join(self):
  bad=copy.deepcopy(self.anchors);bad[-1]['anchor_id']=99999
  with self.assertRaises(AssertionError):mapping(bad,self.events)
 def test_pid_mismatch_invalidates_join(self):
  bad=copy.deepcopy(self.anchors);bad[-1]['pid']+=1
  with self.assertRaises(AssertionError):mapping(bad,self.events)
 def test_probe_blocking_is_observed_without_starvation_relabeling(self):
  m=mapping(self.anchors,self.events)
  span=next(r for r in readlines(ROOT/'probe-query-spans.jsonl') if r['kind']=='probe_span')
  joined=overlap_states(self.states,span['pid'],span['thread_id'],mapped(m,span['wall_start_ns']),mapped(m,span['wall_end_ns']))
  self.assertAlmostEqual(joined['state_coverage_fraction'],1.)
  self.assertGreater(joined['state_ns']['Blocked'],30_000_000)
  self.assertLess(joined['state_ns']['Runnable'],10_000)
  self.assertIn('Interrupted',joined['state_ns']);self.assertIn('Preempted',joined['state_ns'])
  self.assertIsNone(joined['loss_counter'])
 def test_incomplete_primary_does_not_manufacture_attribution(self):
  dispatch=readlines(ROOT/'primary-dispatch.jsonl');done=readlines(ROOT/'primary-completion.jsonl')
  self.assertEqual(len(dispatch),5);self.assertEqual(len(done),4)
  self.assertFalse((ROOT/'primary-complete.json').exists())
  samples=readlines(ROOT/'raw-wall-cpu-observations.jsonl')
  self.assertEqual(len(samples),100);self.assertEqual(sum(r['trace_on'] for r in samples),20)
  verdict=json.loads((ROOT/'technical-verdict.json').read_text())
  self.assertEqual(verdict['valid_primary_scheduler_joins'],0)
  self.assertEqual(verdict['H1_assessment'],'STILL_INCONCLUSIVE')
  self.assertTrue(all(r['classification']=='INSUFFICIENT_EVIDENCE' and not r['supporting_scheduler_or_hardware_events'] for r in readlines(ROOT/'spike-classification.jsonl')))
  failure=next(r for r in readlines(ROOT/'commands.jsonl') if r['name']=='E3-b0-seremban-medium-on-A2')
  self.assertEqual(failure['limit_reason'],'TRACE_STORAGE_LIMIT')
 def test_baseline_and_h1_source_hashes(self):
  identity=json.loads((ROOT/'build-identities.json').read_text())
  for v in ['A','B']:
   for path,expected in identity['variants'][v]['source_hashes'].items():self.assertEqual(sha(ROOT/('source-'+v)/path),expected)
   for record in identity['variants'][v]['executables'].values():self.assertEqual(sha(record['path']),record['sha256'])
if __name__=='__main__':unittest.main()
