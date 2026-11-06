"""Static amendment tests; negative controls never execute diagnostic workloads."""
from collections import Counter, defaultdict
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
spec=importlib.util.spec_from_file_location('ordering_static_validator',HERE/'validate_amendment.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
NEGATIVE_RESULTS=[]


class AmendmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=v.strict_read(REPO/'docs/task15_tail_attribution_protocol_v1.1.0.json')
        cls.protocol=v.strict_read(REPO/'docs/task15_tail_attribution_protocol_v1.2.0.json')

    def repair(self,protocol):
        protocol['design']['resolved_diagnostic_order_sha256']=v.digest(protocol['design']['resolved_diagnostic_order'])
        protocol['identity']['sha256']=v.protocol_digest(protocol)

    def expect(self,code,protocol,repair=True):
        if repair:self.repair(protocol)
        with self.assertRaises(v.Invalid) as caught:
            v.verify_order(protocol,self.parent)
        self.assertEqual(caught.exception.code,code)
        NEGATIVE_RESULTS.append({'case':self.id(),'expected':code,'observed':caught.exception.code,
                                 'outer_hashes_repaired':repair,'measurement_data':False})

    def mutate(self):
        p=deepcopy(self.protocol)
        return p,p['design']['resolved_diagnostic_order']

    def test_01_complete_amendment_and_preservation(self):
        report=v.verify_files(REPO)
        self.assertEqual(report['diagnostic_entries'],52)
        self.assertEqual(report['diagnostic_units'],100)
        self.assertEqual(report['blocks_by_session'],{0:26,1:24,2:26,3:24})
        self.assertEqual(report['total_units'],228)
        self.assertEqual(report['structural_query_records'],138696)
        self.assertEqual(report['protected_git_objects']['research/task15_harness'],v.HARNESS_TREE)
        self.assertFalse(report['execution_authorized'])
        self.assertFalse(report['promotion_authorized'])

    def test_02_missing_companion(self):
        p,r=self.mutate();r['entries']=[e for e in r['entries'] if e['diagnostic_entry_id']!='C-stack-0']
        self.expect('MISSING_COMPANION',p)

    def test_03_duplicate_companion(self):
        p,r=self.mutate();r['entries'].append(deepcopy(next(e for e in r['entries'] if e['lane']=='COMPANION')))
        self.expect('DUPLICATE_COMPANION',p)

    def test_04_companion_wrong_session(self):
        p,r=self.mutate();next(e for e in r['entries'] if e['lane']=='COMPANION')['diagnostic_session']=1
        self.expect('SESSION_ASSIGNMENT',p)

    def test_05_main_reordered(self):
        p,r=self.mutate();r['entries'][0],r['entries'][1]=r['entries'][1],r['entries'][0]
        self.expect('MAIN_ORDER',p)

    def test_06_reversed_condition_order(self):
        p,r=self.mutate();r['entries'][0]['condition_order'].reverse()
        self.expect('CONDITION_ORDER',p)
        p,r=self.mutate();r['condition_blocks'][0],r['condition_blocks'][1]=r['condition_blocks'][1],r['condition_blocks'][0]
        self.expect('CONDITION_ORDER',p)

    def test_07_incorrect_trial_reference(self):
        p,r=self.mutate();r['entries'][0]['schedule_ref']='S00-P2-T03'
        self.expect('SCHEDULE_REFERENCE',p)

    def test_08_altered_p2_order(self):
        p,r=self.mutate();row=next(e for e in p['design']['base_schedule'] if e['protocol']=='P2')
        region=row['regions'][0];orders=row['P2_pair_orders_by_region'][region]
        orders[0]='BA' if orders[0]=='AB' else 'AB'
        p['design']['schedule_sha256']=v.digest(p['design']['base_schedule'])
        self.expect('P2_QUERY_ORDER',p)

    def test_09_stale_cross_lane_hash(self):
        p,r=self.mutate();p['design']['resolved_diagnostic_order_sha256']='0'*64
        p['identity']['sha256']=v.protocol_digest(p)
        self.expect('ORDER_HASH',p,repair=False)

    def test_10_stale_protocol_hash(self):
        p,r=self.mutate();p['identity']['sha256']='0'*64
        self.expect('PROTOCOL_HASH',p,repair=False)

    def test_11_query_identity_namespace_cannot_change(self):
        p,r=self.mutate();r['query_identity_policy']['namespace_protocol_sha256']='0'*64
        self.expect('QUERY_ID_NAMESPACE',p)

    def test_12_scientific_rules_are_parent_identical(self):
        paths=[('statistics',),('acceptance',),('hypotheses',),('measurement_boundaries',),
               ('calibration',),('inputs',),('binaries',),('exclusion_rules',),('cohorts',)]
        for path in paths:
            with self.subTest(path=path):
                p,r=self.mutate();p[path[0]]={'forbidden_scientific_change':True}
                self.expect('SCIENTIFIC_FIELDS_CHANGED',p)

    def test_13_no_authorization_or_changed_source_lanes(self):
        for field in ('execution_authorized','promotion_authorized'):
            p,r=self.mutate();p[field]=True;self.expect('AUTHORIZATION',p)
        p,r=self.mutate();p['design']['allocator_stack_companions'][0]['diagnostic_session']=1
        self.expect('SOURCE_LANE_CHANGED',p)
        p,r=self.mutate();p['design']['diagnostic_schedule'].reverse()
        self.expect('SOURCE_LANE_CHANGED',p)

    def test_14_companion_placement_sequence_and_provenance(self):
        p,r=self.mutate();r['entries'][12],r['entries'][13]=r['entries'][13],r['entries'][12]
        self.expect('COMPANION_ORDER',p)
        p,r=self.mutate();r['entries'][0]['sequence_index']=99;self.expect('ENTRY_SEQUENCE',p)
        p,r=self.mutate();r['entries'][0]['source_lane_index']=999;self.expect('ENTRY_METADATA',p)
        p,r=self.mutate();r['entries'].insert(0,r['entries'].pop(12))
        for i,e in enumerate(r['entries'][:14]):e['sequence_index']=i
        self.expect('CROSS_LANE_ORDER',p)

    def test_15_legacy_query_ids_occurrences_and_primary_units(self):
        # Read-only use of unchanged v1.1 harness, as an independent compatibility oracle.
        sys.path.insert(0,str(REPO/'research/task15_harness'))
        from task15_harness.protocol import load_protocol
        from task15_harness.planning import compile_plan,query_records
        old=load_protocol(REPO);plan=compile_plan(old)
        expected=defaultdict(list)
        for q in query_records(old,plan):
            expected[q['trial_id']].append((q['query_id'],q['trial_id'],q['phase'],q['region'],q['execution_index'],
                q['original_position'],q['source_id'],q['source_occurrence'],q['variant']))
        resolved=defaultdict(list)
        serialized_units=[]
        for record in v.static_jobs(self.protocol):
            if not serialized_units or record[1]!=serialized_units[-1]:serialized_units.append(record[1])
            resolved[record[1]].append(record)
        # Equal dictionaries of ORDERED per-unit queries: detects loss, changes, duplicates and per-unit reorders.
        self.assertEqual(dict(resolved),dict(expected))
        old_primary=[u['id'] for u in plan['units'] if u['session_kind']=='PRIMARY']
        self.assertEqual(len(old_primary),128)
        self.assertEqual(serialized_units[:128],old_primary)
        new_diagnostic=[b['unit_id'] for b in self.protocol['design']['resolved_diagnostic_order']['condition_blocks']]
        self.assertEqual(serialized_units[128:],new_diagnostic)
        self.assertEqual(len(serialized_units),228)
        self.assertEqual(sum(map(len,resolved.values())),138696)
        self.assertEqual(old.identity,v.PARENT_HASH)  # production loader still v1.1.0


if __name__=='__main__':
    unittest.main(verbosity=2)
