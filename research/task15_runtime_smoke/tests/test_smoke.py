"""Negative controls use fake results/loaders only; zero real native calls."""
import copy
import io
import json
import math
from pathlib import Path
import struct
import sys
from contextlib import redirect_stdout
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from production_adapter import AdapterError,production_gate
from production_adapter.artifacts import verify_artifact,macho
from production_adapter.loading import import_verified
from production_adapter.fingerprints import COUNTERS,FRONTIER,PROFILES
from smoke.contract import VERTICES,EDGES,SOURCES,EXPECTATIONS,Budget,validate_result
from smoke.dependencies import verify_dependencies,parse_image
from smoke.runtime import fixed_queries,preflight
from smoke.campaign import protocol,classify


def diagnostic():
    d = {k:0 for k in COUNTERS}
    d.update(label_nodes_created=1,label_nodes_materialized=1,query_seconds=123456.789,preprocessing_seconds=987654.321,
             implementation='BMSSP2025Engine::solve',frontier={k:0 for k in FRONTIER},
             profile={k:{'calls':0,'inclusive_seconds':0.0,'exclusive_seconds':0.0} for k in PROFILES})
    return d


class Result:
    algorithm = 'native_bmssp_2025'
    def __init__(self,graph,source):self.graph,self.source=graph,source
    def belongs_to(self,graph):return graph is self.graph
    @property
    def distances(self):return list(EXPECTATIONS[self.source]['distances'])
    @property
    def diagnostics(self):return diagnostic()
    def path(self,target):
        if target == 5:return {'reachable':False,'distance':math.inf,'vertices':[],'edges':[]}
        ex = EXPECTATIONS[self.source]
        return {'reachable':True,'distance':ex['distances'][target],'vertices':list(ex['vertices']),'edges':list(ex['edges'])}


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p=protocol()
    def test_wrong_binary_sha(self):
        p=copy.deepcopy(self.p);p['binaries']['baseline']['sha256']='f'*64
        with self.assertRaisesRegex(AdapterError,'BINARY_HASH'):
            verify_artifact(p,'baseline',p['binaries']['baseline']['path'])
    def test_wrong_architecture(self):
        with self.assertRaisesRegex(AdapterError,'HOST_ARCHITECTURE'):
            verify_artifact(self.p,'baseline',self.p['binaries']['baseline']['path'],machine='x86_64')
    def test_wrong_cpython_abi(self):
        with self.assertRaisesRegex(AdapterError,'CPYTHON_ABI'):
            verify_artifact(self.p,'baseline',self.p['binaries']['baseline']['path'],abi='cpython-312')
    def test_wrong_variant_path(self):
        with self.assertRaisesRegex(AdapterError,'BINARY_PATH'):
            verify_artifact(self.p,'baseline',self.p['binaries']['candidate']['path'])
    def test_original_binary_hashes_only(self):
        for v in ['baseline','candidate']:
            r=verify_artifact(self.p,v,self.p['binaries'][v]['path'])
            self.assertEqual(r['variant'],v)
    def test_global_module_contamination(self):
        with patch.dict(sys.modules,{'bmssp_native':object()}):
            with self.assertRaisesRegex(AdapterError,'NATIVE_MODULE_ALREADY_LOADED'):preflight(self.p,'baseline')
    def test_loader_injection(self):
        with patch.dict('os.environ',{'DYLD_INSERT_LIBRARIES':'/fake/inject.dylib'}):
            with self.assertRaisesRegex(AdapterError,'INJECTED_LOADER'):preflight(self.p,'baseline')
    def test_unexpected_dependency_identity(self):
        name='/usr/lib/libc++.1.dylib'
        good={'loaded_path':name,'install_name':name,'architecture':'arm64','loaded_uuid':'a'*32}
        verify_dependencies({name:good},[name])
        for key,value in [('loaded_path','/fake/lib'),('install_name','/fake/lib'),('architecture','x86_64'),('loaded_uuid','0'*32)]:
            bad={**good,key:value}
            with self.subTest(key=key),self.assertRaises(AdapterError):verify_dependencies({name:bad},[name])
    def test_wrong_loaded_extension_uuid_or_arch(self):
        data=bytearray(Path(self.p['binaries']['baseline']['path']).read_bytes())
        struct.pack_into('<I',data,4,7)
        with self.assertRaises(AdapterError):parse_image(data,'/fake')
    def test_wrong_distance_vector(self):
        class Bad(Result):
            @property
            def distances(self):return [0.0]*6
        graph=object()
        with self.assertRaisesRegex(AdapterError,'DISTANCE_MISMATCH'):validate_result(Bad(graph,0),graph,0)
    def test_wrong_directed_path(self):
        class Bad(Result):
            def path(self,target):
                r=super().path(target)
                if target != 5:r['edges']=[10,11,12,14]
                return r
        graph=object()
        with self.assertRaisesRegex(AdapterError,'DIRECTED_PATH_MISMATCH'):validate_result(Bad(graph,0),graph,0)
    def test_nonzero_profile_calls(self):
        class Bad(Result):
            @property
            def diagnostics(self):
                d=diagnostic();d['profile']['base_case']['calls']=1;return d
        graph=object()
        with self.assertRaisesRegex(AdapterError,'PROFILE_ENABLED'):validate_result(Bad(graph,0),graph,0)
    def test_no_native_timing_fields_retained(self):
        graph=object();r=validate_result(Result(graph,0),graph,0)
        text=json.dumps(r,allow_nan=False)
        for banned in ['query_seconds','preprocessing_seconds','inclusive_seconds','exclusive_seconds','123456.789','987654.321']:
            self.assertNotIn(banned,text)
    def test_failed_native_import_fake_ops(self):
        identity={'variant':'baseline','path':'/fake/original.so','dependencies':[]}
        class Ops:
            registry={}
            def create(self,path):raise ImportError('fixed fake native loader failure')
        ops=Ops()
        with self.assertRaisesRegex(ImportError,'fixed fake native loader failure'):import_verified(identity,set(),ops)
        self.assertNotIn('bmssp_native',ops.registry)
    def test_native_crash_classification_without_process(self):
        self.assertEqual(classify(-11,None),'NATIVE_PROCESS_SIGNAL')
        self.assertEqual(classify(3,None),'CHILD_FAILURE')
    def test_extra_solve_and_wrong_source_rejected(self):
        b=Budget();b.before_solve(0);b.before_solve(3)
        with self.assertRaisesRegex(AdapterError,'BUDGET_EXHAUSTED'):b.before_solve(0)
        for source in [1,2,True,'0']:
            with self.assertRaises(AdapterError):Budget().before_solve(source)
    def test_fixed_fake_graph_and_exact_two_queries(self):
        calls=[]
        class Module:
            @staticmethod
            def NativeGraph(vertices,edges):
                assert vertices == VERTICES and edges == EDGES
                return SimpleNamespace(vertex_ids=VERTICES,metadata={'vertex_count':6,'edge_count':7,'directed':True,'immutable':True})
            @staticmethod
            def BMSSP2025Engine(graph):
                class Engine:
                    metadata={'preprocessing_count':1,'preprocessing_seconds':987654.321}
                    def solve(self,source,*,profile):
                        assert profile is False
                        calls.append(source);return Result(graph,source)
                return Engine()
        events=[]
        self.assertEqual(fixed_queries(Module,events.append),2)
        self.assertEqual(calls,[0,3])
        self.assertEqual([e['event'] for e in events].count('QUERY_VERIFIED'),2)
        self.assertNotIn('987654.321',json.dumps(events))
    def test_no_reference_dijkstra(self):
        import ast
        path=Path(__file__).resolve().parents[1]/'smoke/runtime.py'
        tree=ast.parse(path.read_text())
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr=='NativeReferenceDijkstra' for n in ast.walk(tree)))
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in {'perf_counter','perf_counter_ns','monotonic','monotonic_ns','time'} for n in ast.walk(tree)))
    def test_forbidden_smoke_commands(self):
        import run
        for args in [['collect'],['benchmark'],['profile'],['calibrate'],['run-fixed','--graph','/road'],['run-fixed','--source','9'],['run-fixed','--executable','/fake'],['run-real']]:
            with self.subTest(args=args),redirect_stdout(io.StringIO()):self.assertEqual(run.main(args),2)
    def test_production_gate_still_disabled(self):
        with self.assertRaisesRegex(AdapterError,'PRODUCTION_EXECUTION_DISABLED'):production_gate()
        from task15_cohort_a_runner.__main__ import main
        for op in ['collect','calibrate','run-real','benchmark','profile','analyze-confirmatory','promote','resume']:
            with redirect_stdout(io.StringIO()):self.assertEqual(main([op]),2)
    def test_child_claim_required_before_loading(self):
        import tempfile
        from smoke.campaign import fixed_child
        with tempfile.TemporaryDirectory() as directory:
            Path(directory,'baseline.launch.json').write_text(json.dumps({'nonce':'no-match','variant':'baseline'}))
            with self.assertRaisesRegex(AdapterError,'PRIVATE_CHILD_CLAIM'):fixed_child('baseline',directory)
        self.assertNotIn('bmssp_native',sys.modules)

    def test_disposable_process_crash_no_native_module(self):
        import subprocess
        proc=subprocess.run([sys.executable,'-I','-B','-c',
                             "import os,signal,sys; assert 'bmssp_native' not in sys.modules; os.kill(os.getpid(),signal.SIGKILL)"],
                            capture_output=True,timeout=10)
        self.assertEqual(proc.returncode,-9)
        self.assertEqual(classify(proc.returncode,None),'NATIVE_PROCESS_SIGNAL')

if __name__ == '__main__':unittest.main()
