"""Tiny fake/disposable fixtures only; no original native solve or road oracle query."""
import copy
import io
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from contextlib import redirect_stdout
from production_adapter import AdapterError,production_gate
from production_adapter.graphs import parse_graph
from roadcheck.io import sha
from roadcheck.oracle import dijkstra,vector_identity
from roadcheck.inputs import Budget,selection,REGIONS
from roadcheck.validation import validate,InvalidResult
from smoke.campaign import protocol
from smoke.contract import safe_diagnostics
from production_adapter.fingerprints import COUNTERS,FRONTIER,PROFILES

DATA=b'6 7\n0\n1\n2\n3\n4\n5\n1 0 1 1\n2 0 1 2\n3 1 2 1\n4 0 2 2\n5 2 3 1\n6 0 4 7\n7 4 3 1\n'
DISTANCES=[0.0,1.0,2.0,3.0,7.0,math.inf]

def diag():
    d={k:0 for k in COUNTERS}
    d.update(label_nodes_created=1,label_nodes_materialized=1,query_seconds=12345.678,preprocessing_seconds=87654.321,
             implementation='BMSSP2025Engine::solve',frontier={k:0 for k in FRONTIER},profile={k:{'calls':0,'inclusive_seconds':0.0,'exclusive_seconds':0.0} for k in PROFILES})
    return d

class Result:
    algorithm='native_bmssp_2025';source=0
    def __init__(self,graph):self.graph=graph
    def belongs_to(self,graph):return graph is self.graph
    @property
    def distances(self):return list(DISTANCES)
    @property
    def diagnostics(self):return diag()
    def path(self,target):
        vs,es={1:([0,1],[1]),2:([0,2],[4]),3:([0,2,3],[4,5]),5:([],[])}[target]
        return {'reachable':target!=5,'distance':DISTANCES[target],'vertices':vs,'edges':es}

class Tests(unittest.TestCase):
    def setup(self):
        g=parse_graph(DATA,sha(DATA),synthetic=True)
        chosen={'source_id':0,'path_targets':[1,2,3,5]}
        vector,h=vector_identity(DISTANCES)
        return g,chosen,{'vertices':list(g.vertices),'distances_le_hex':vector,'distance_sha256':h}
    def test_independent_oracle_parallel_directed_unreachable(self):
        g,_,_=self.setup()
        self.assertEqual(dijkstra(g,0),DISTANCES)
        self.assertEqual(dijkstra(g,3),[math.inf,math.inf,math.inf,0.0,math.inf,math.inf])
    def test_good_full_vector_and_four_paths(self):
        g,c,o=self.setup();r=validate(Result(g),g,g,c,o)
        self.assertTrue(r['valid']);self.assertEqual(r['native_sha256'],o['distance_sha256'])
        self.assertTrue(all(p['valid'] for p in r['paths']))
    def test_equal_cost_alternative_allowed(self):
        class Alternate(Result):
            def path(self,target):
                p=super().path(target)
                if target==2:p.update(vertices=[0,1,2],edges=[1,3])
                return p
        g,c,o=self.setup();self.assertTrue(validate(Alternate(g),g,g,c,o)['valid'])
    def test_every_exact_bit_mismatch_preserved(self):
        class Bad(Result):
            @property
            def distances(self):return [0.0,1.0000000000000002,2.0000000000000004,3.0,7.0,math.inf]
        g,c,o=self.setup()
        with self.assertRaises(InvalidResult) as caught:validate(Bad(g),g,g,c,o)
        r=caught.exception.evidence
        self.assertEqual([d['vertex'] for d in r['distance_mismatches']],[1,2])
        self.assertEqual(r['first_differing_vertex']['vertex'],1)
        self.assertNotEqual(r['native_sha256'],r['oracle_sha256'])
        self.assertEqual(len(r['paths']),4)
        self.assertIsNotNone(r['diagnostics_without_timing'])
    def test_reverse_edge_rejected(self):
        class Bad(Result):
            def path(self,target):
                p=super().path(target)
                if target==1:p['edges']=[7]
                return p
        g,c,o=self.setup()
        with self.assertRaises(InvalidResult) as caught:validate(Bad(g),g,g,c,o)
        self.assertIn('DIRECTED_EDGE_ORIENTATION',json.dumps(caught.exception.evidence))
    def test_wrong_source_and_storage(self):
        g,c,o=self.setup()
        for result,storage in [(Result(g),object()),(SimpleNamespace(source=1),g)]:
            with self.assertRaises(InvalidResult):validate(result,storage,g,c,o)
    def test_profiles_and_required_counters(self):
        for kind in ['profile','missing','materialization']:
            class Bad(Result):
                @property
                def diagnostics(self):
                    d=diag()
                    if kind=='profile':d['profile']['base_case']['calls']=1
                    if kind=='missing':del d['recursive_calls']
                    if kind=='materialization':d['label_nodes_materialized']=3
                    return d
            g,c,o=self.setup()
            with self.subTest(kind=kind),self.assertRaises(InvalidResult):validate(Bad(g),g,g,c,o)
    def test_oracle_hash_mutation_rejected(self):
        g,c,o=self.setup();o['distance_sha256']='f'*64
        with self.assertRaises(InvalidResult):validate(Result(g),g,g,c,o)
    def test_invalid_special_values(self):
        for value in [float('nan'),float('-inf'),-1.0,True]:
            with self.assertRaises(AdapterError):vector_identity([value])
        self.assertNotEqual(vector_identity([0.0]),vector_identity([-0.0]))
    def test_budget_fixed_source_order_and_overflow(self):
        p=protocol();b=Budget(p)
        for region in REGIONS:b.claim(region,int(p['inputs'][region]['source_positions'][0]))
        with self.assertRaisesRegex(AdapterError,'BUDGET_EXHAUSTED'):b.claim(REGIONS[0],0)
        with self.assertRaisesRegex(AdapterError,'FIXED_SOURCE_ORDER'):Budget(p).claim(REGIONS[0],0)
        b=Budget(p);b.failed=True
        with self.assertRaises(AdapterError):b.claim(REGIONS[0],int(p['inputs'][REGIONS[0]]['source_positions'][0]))
    def test_source_hash_mutation(self):
        p=protocol();p['inputs'][REGIONS[0]]['source_positions'][0]='0'
        with self.assertRaisesRegex(AdapterError,'SOURCE_LIST_IDENTITY'):selection(p,REGIONS[0])
    def test_original_selection_ordinal_zero(self):
        p=protocol()
        for region in REGIONS:
            s=selection(p,region)
            self.assertEqual(s['original_position'],0);self.assertEqual(s['source_occurrence'],1)
            self.assertEqual(str(s['source_id']),p['inputs'][region]['source_positions'][0])
    def test_timing_fields_discarded(self):
        g,c,o=self.setup();text=json.dumps(validate(Result(g),g,g,c,o))
        for name in ['query_seconds','preprocessing_seconds','inclusive_seconds','exclusive_seconds','12345.678','87654.321']:self.assertNotIn(name,text)
    def test_forbidden_command_overrides(self):
        import run
        for args in [['benchmark'],['collect'],['profile'],['calibrate'],['run-fixed','--graph','/fake'],['run-fixed','--source','0'],['run-fixed','--executable','/fake']]:
            with redirect_stdout(io.StringIO()):self.assertEqual(run.main(args),2)
    def test_existing_gate_disabled(self):
        with self.assertRaisesRegex(AdapterError,'PRODUCTION_EXECUTION_DISABLED'):production_gate()
    def test_child_rejects_wrong_claim_before_import(self):
        from roadcheck.campaign import fixed_child
        with tempfile.TemporaryDirectory() as directory:
            Path(directory,'baseline.launch.json').write_text(json.dumps({'variant':'baseline','nonce':'invalid'}))
            with self.assertRaisesRegex(AdapterError,'PRIVATE_CHILD_CLAIM'):fixed_child('baseline',directory)
        self.assertNotIn('bmssp_native',sys.modules)
    def test_no_clocks_or_smoke_campaign_invocation(self):
        import ast
        root=Path(__file__).resolve().parents[1]/'roadcheck'
        for f in root.glob('*.py'):
            tree=ast.parse(f.read_text())
            self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in {'perf_counter','perf_counter_ns','monotonic','monotonic_ns','process_time'} for n in ast.walk(tree)),f)
            self.assertFalse(any(isinstance(n,ast.Name) and n.id=='fixed_queries' for n in ast.walk(tree)),f)

if __name__=='__main__':unittest.main()
