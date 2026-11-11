"""API-shaped fake bindings only. No graph algorithm, native imports or real clocks."""
import copy
import gc
import hashlib
import importlib.abc
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import weakref
from unittest.mock import patch

from production_adapter import AdapterError, production_gate
from production_adapter.artifacts import verify_artifact, macho
from production_adapter.graphs import parse_graph
from production_adapter.fingerprints import COUNTERS, FRONTIER, PROFILES, evidence, historical_paths, binary64
from production_adapter.native import NativeBinding, NativeClock, runtime_dependencies
from production_adapter.worker import Worker, Cluster, production_worker, validate_response
from task15_cohort_a_runner.frozen import Workload
from task15_cohort_a_runner.bundle import source_identity

ROOT = Path(__file__).resolve().parents[3]


def diagnostic():
    d = {k: 0 for k in COUNTERS}
    d.update(label_nodes_created=1, label_nodes_materialized=1, query_seconds=0.125,
             preprocessing_seconds=0.25, implementation='BMSSP2025Engine::solve',
             frontier={k: 0 for k in FRONTIER},
             profile={k: {'inclusive_seconds': 0.0, 'exclusive_seconds': 0.0, 'calls': 0} for k in PROFILES})
    return d


class FakeResult:
    algorithm = 'native_bmssp_2025'
    def __init__(self, owner, source, graph):
        self.owner, self.source, self.graph = owner, source, graph
    def belongs_to(self, graph):
        self.owner.events.append('belongs_to')
        return self.graph is graph
    @property
    def diagnostics(self):
        self.owner.events.append('diagnostics')
        return self.owner.diagnostics
    @property
    def distances(self):
        self.owner.events.append('distances')
        # Programmed synthetic response, no shortest-path traversal.
        return [0.0 if v == self.source else float('inf') for v in self.graph.vertex_ids]
    def path(self, target):
        self.owner.events.append('path')
        if self.owner.bad_path:
            return {'reachable': True, 'distance': 0.0, 'vertices': [self.source, target], 'edges': [999]}
        return {'reachable': target == self.source, 'distance': 0.0 if target == self.source else float('inf'),
                'vertices': [target] if target == self.source else [], 'edges': []}
    def __del__(self):
        self.owner.events.append('destroy')


class FakeBinding:
    synthetic = True
    def __init__(self, variant, events):
        self.variant, self.events = variant, events
        self.diagnostics = diagnostic()
        self.fail = False
        self.bad_path = False
        self.calls = 0
        self.result_ref = None
    def NativeGraph(self, vertices, edges):
        self.events.append('NativeGraph')
        class Graph: pass
        g = Graph()
        g.vertex_ids = list(vertices)
        g.edges = list(edges)
        return g
    def BMSSP2025Engine(self, graph):
        self.events.append('BMSSP2025Engine')
        owner = self
        class Engine:
            metadata = {'preprocessing_count': 1}
            def solve(self, source, *, profile):
                owner.events.append('solve')
                assert profile is False
                owner.calls += 1
                if owner.fail:
                    raise RuntimeError('fake worker solve failure')
                r = FakeResult(owner, source, graph)
                owner.result_ref = weakref.ref(r)
                return r
        return Engine()
    @property
    def NativeReferenceDijkstra(self):
        raise AssertionError('Dijkstra forbidden')


class FakeClock:
    synthetic = True
    metadata = {'api': 'DETERMINISTIC_FAKE', 'units': 'synthetic_ticks', 'representation_ratio': [1, 1],
                'mapping': None, 'effective_quantum': None, 'calibration': 'NOT_A_MEASUREMENT'}
    def __init__(self, events, binding):
        self.events, self.binding, self.reads = events, binding, 0
    def read(self):
        self.reads += 1
        self.events.append('T0' if self.reads % 2 else 'T5')
        if self.reads % 2 == 0:
            assert self.binding.result_ref() is not None, 'destroyed before T5'
        return self.reads * 10


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = Workload()
        cls.runner = source_identity()['identity_sha256']
    def setup_worker(self, unit=None, cluster=None, variant=None):
        unit = unit or self.w.units[0]
        cluster = cluster or Cluster.frozen(self.w, unit['id'])
        variant = variant or cluster.queries[cluster.cursor]['variant']
        graphs = {}
        for region, inp in self.w.p['inputs'].items():
            vs = sorted({int(v) for v in inp['source_positions']+inp['path_targets']})
            data = (f'{len(vs)} 0\n' + ''.join(f'{v}\n' for v in vs)).encode()
            graphs[region] = parse_graph(data, hashlib.sha256(data).hexdigest(), synthetic=True)
        events = []
        b = FakeBinding(variant, events)
        c = FakeClock(events, b)
        worker = Worker(self.w, cluster, variant, b, c, graphs, self.runner)
        return worker, b, c, events
    def request(self, worker):
        return {'op': 'QUERY', 'sequence': worker.cluster.cursor+1,
                'query': copy.deepcopy(worker.cluster.queries[worker.cluster.cursor])}
    def execute(self, worker, events):
        frames = []
        def write(data):
            events.append('write')
            self.assertIsNone(worker.binding.result_ref())
            frames.append(data)
        response = worker.query(self.request(worker), write)
        self.assertEqual(len(frames), 1)
        self.assertEqual(struct.unpack('!I', frames[0][:4])[0], len(frames[0])-4)
        self.assertEqual(json.loads(frames[0][4:]), response)
        return response
    def test_archived_binary_identities_read_only(self):
        for variant in ('baseline', 'candidate'):
            r = verify_artifact(self.w.p, variant, self.w.p['binaries'][variant]['path'], abi='cpython-311', machine='arm64')
            self.assertEqual(r['variant'], variant)
            self.assertEqual(r['dependency_resolution'], 'NOT_LOADED')
            self.assertEqual(len(r['uuid']), 32)
    def test_binary_wrong_hash(self):
        p = copy.deepcopy(self.w.p)
        p['binaries']['baseline']['sha256'] = '0'*64
        with self.assertRaisesRegex(AdapterError, 'BINARY_HASH'):
            verify_artifact(p, 'baseline', p['binaries']['baseline']['path'], abi='cpython-311', machine='arm64')
    def test_binary_wrong_variant_path(self):
        with self.assertRaisesRegex(AdapterError, 'BINARY_PATH'):
            verify_artifact(self.w.p, 'baseline', self.w.p['binaries']['candidate']['path'])
    def test_binary_abi_arch(self):
        for abi, arch, reason in [('cpython-312', 'arm64', 'CPYTHON_ABI'), ('cpython-311', 'x86_64', 'HOST_ARCHITECTURE')]:
            with self.subTest(reason=reason), self.assertRaisesRegex(AdapterError, reason):
                verify_artifact(self.w.p, 'baseline', self.w.p['binaries']['baseline']['path'], abi=abi, machine=arch)
    def test_macho_rejects_wrong_cpu_and_truncation(self):
        data = bytearray(Path(self.w.p['binaries']['baseline']['path']).read_bytes())
        struct.pack_into('<I', data, 4, 7)
        for value in [data, b'xx']:
            with self.assertRaises(AdapterError): macho(value)
    def parse(self, data, sources=()):
        return parse_graph(data, hashlib.sha256(data).hexdigest(), sources, synthetic=True)
    def test_graph_binary64_orientation(self):
        g = self.parse(b'2 2\n-1\n2\n8 2 -1 0.10000000000000001\n9 -1 2 -0\n', [-1])
        self.assertEqual(g.edges[0][1:3], (2, -1))
        self.assertEqual(struct.pack('<d', g.edges[0][3]), struct.pack('<d', .1))
        self.assertEqual(struct.pack('<d', g.edges[1][3]).hex(), '0000000000000080')
    def test_graph_invalid_records(self):
        cases = [b'', b'2 0\n1\n', b'1 0\n1\nextra\n', b'2 0\n1\n1\n', b'2 0\n2\n1\n',
                 b'1 1\n1\n0 1 2 1\n', b'1 1\n1\n-1 1 1 1\n', b'1 1\n1\n0 1 1 nan\n',
                 b'1 1\n1\n0 1 1 -1\n', b'1 1\n1\n0 1 1 1e999\n', b'1 1\n1\n0 1 1 1_0\n',
                 b'1 2\n1\n0 1 1 1\n0 1 1 1\n', b'1 0\n9223372036854775808\n',
                 b'1 1\n1\n18446744073709551616 1 1 0\n']
        for data in cases:
            with self.subTest(data=data), self.assertRaises((AdapterError, UnicodeError)): self.parse(data)
    def test_graph_hash_and_source(self):
        with self.assertRaisesRegex(AdapterError, 'GRAPH_HASH'): parse_graph(b'1 0\n1\n', '0'*64)
        with self.assertRaisesRegex(AdapterError, 'SOURCE_MEMBERSHIP'): self.parse(b'1 0\n1\n', [2])
    def test_graph_real_exports_parse_only(self):
        from production_adapter.graphs import frozen_graph
        for region, counts in {'seremban-small':(834,1776),'seremban-medium':(14464,35530),'seremban-port-dickson':(24736,60214)}.items():
            g = frozen_graph(self.w.p['inputs'][region])
            self.assertEqual((len(g.vertices),len(g.edges)), counts)
            self.assertFalse(g.synthetic)
    def test_construction_order_and_variant(self):
        worker,b,c,events = self.setup_worker()
        self.assertEqual(events, ['NativeGraph','BMSSP2025Engine']*3)
        with self.assertRaisesRegex(AdapterError, 'WRONG_VARIANT'):
            Worker(self.w, worker.cluster, 'baseline' if b.variant == 'candidate' else 'candidate', b,c,worker.graphs,self.runner)
    def test_query_timing_lifetime_and_response(self):
        worker,b,c,events = self.setup_worker()
        events.clear()
        r = self.execute(worker,events)
        self.assertEqual(events[:3], ['T0','solve','T5'])
        self.assertEqual(events[-2:], ['destroy','write'])
        self.assertEqual(events.count('distances'),1)
        self.assertEqual(events.count('path'),4)
        self.assertEqual(b.calls,1)
        self.assertEqual(c.reads,2)
        self.assertEqual(r['evidence']['legacy_query_seconds'], .125)
        self.assertTrue(r['synthetic'])
        self.assertFalse(r['measurement_eligible'])
        self.assertTrue(r['warmup_excluded'])
        self.assertIsNone(r['timing']['T2'])
    def test_historical_hash_conventions(self):
        worker,b,c,events = self.setup_worker()
        q = worker.cluster.queries[0]
        r = self.execute(worker,events)
        vs = worker.graphs[q['region']].vertices
        ds = [0.0 if v == int(q['source_id']) else float('inf') for v in vs]
        self.assertEqual(r['evidence']['distance_sha256'], hashlib.sha256(struct.pack('<'+'d'*len(ds),*ds)).hexdigest())
        paths = [{'reachable':False,'distance':float('inf'),'vertices':[],'edges':[]}]*4
        self.assertEqual(r['evidence']['paths_sha256'], hashlib.sha256(json.dumps(paths,sort_keys=True).encode()).hexdigest())
        self.assertNotIn('label_nodes_materialized',r['evidence']['historical_work'])
    def test_binary64_special_values(self):
        self.assertNotEqual(binary64(0.0),binary64(-0.0))
        self.assertEqual(binary64(float('inf')),struct.pack('<d',float('inf')))
        for v in [float('nan'),float('-inf'),-1.0,1,True]:
            with self.assertRaises(AdapterError): binary64(v)
    def test_solve_failure_no_t5_cleanup_no_retry(self):
        worker,b,c,events = self.setup_worker()
        b.fail = True
        frames=[]
        r=worker.query(self.request(worker),frames.append)
        self.assertEqual(len(frames),1)
        self.assertEqual(b.calls,1)
        self.assertEqual(c.reads,1)
        self.assertIsNone(r['timing']['T5'])
        self.assertEqual(r['error']['message'],'fake worker solve failure')
        with self.assertRaisesRegex(AdapterError,'CLUSTER_INVALID'):
            worker.query(self.request(worker),frames.append)
        self.assertEqual(b.calls,1)
    def test_bad_diagnostics_cleanup(self):
        for mutation in ['missing','profile','counter','materialization']:
            worker,b,c,events = self.setup_worker()
            if mutation == 'missing': del b.diagnostics['query_seconds']
            if mutation == 'profile': b.diagnostics['profile']['base_case']['calls']=1
            if mutation == 'counter': b.diagnostics['recursive_calls']=-1
            if mutation == 'materialization': b.diagnostics['label_nodes_materialized']=2
            with self.subTest(mutation=mutation):
                r=self.execute(worker,events)
                self.assertEqual(r['status'],'ERROR')
                self.assertEqual(c.reads,2)
                self.assertTrue(worker.cluster.invalid)
    def test_bad_path_cleanup(self):
        worker,b,c,events = self.setup_worker()
        b.bad_path=True
        self.assertEqual(self.execute(worker,events)['status'],'ERROR')
    def test_whole_cluster_invalidation_both_variants(self):
        worker,b,c,events = self.setup_worker()
        other,ob,oc,oe = self.setup_worker(cluster=worker.cluster,variant='baseline' if b.variant=='candidate' else 'candidate')
        b.fail=True
        worker.query(self.request(worker),lambda _:None)
        with self.assertRaisesRegex(AdapterError,'CLUSTER_INVALID'):
            other.query(self.request(other),lambda _:None)
        self.assertEqual(ob.calls,0)
    def test_serial_order_p1_p2(self):
        for kind in ['P1','P2']:
            unit=next(u for u in self.w.units if u['protocol']==kind)
            cluster=Cluster.frozen(self.w,unit['id'])
            workers={v:self.setup_worker(unit,cluster,v) for v in ['baseline','candidate']}
            for q in cluster.queries:
                worker,b,c,events=workers[q['variant']]
                r=self.execute(worker,events)
                self.assertEqual(r['query'],q)
                self.assertEqual('label_nodes_materialized' in r['evidence']['historical_work'],kind=='P2')
            self.assertEqual(cluster.cursor,648)
            self.assertFalse(cluster.invalid)
    def test_repeated_source_occurrence(self):
        qs = [q for q in self.w.queries[self.w.units[0]['id']] if q['region']=='seremban-small' and q['source_id']=='4882418061' and q['phase']=='target']
        self.assertEqual({q['source_occurrence'] for q in qs},{1,2,3})
        self.assertEqual(len({q['query_id'] for q in qs}),6)
    def test_mutated_identity_and_sequence(self):
        for field,value in [('source_occurrence',999),('source_id','0'),('snapshot_id','0'*64),('query_id','0'*64),('original_position',-1)]:
            worker,b,c,e=self.setup_worker()
            r=self.request(worker);r['query'][field]=value
            response=worker.query(r,lambda _:None)
            self.assertEqual(response['status'],'ERROR')
            self.assertEqual(b.calls,0)
        worker,b,c,e=self.setup_worker()
        r=self.request(worker);r['sequence']=2
        self.assertEqual(worker.query(r,lambda _:None)['status'],'ERROR')
        self.assertEqual(c.reads,0)
    def test_prior_retained_result(self):
        worker,b,c,e=self.setup_worker()
        ng,engine=next(iter(worker.prepared.values()))
        held=engine.solve(ng.vertex_ids[0],profile=False)
        worker.last_result=weakref.ref(held)
        r=worker.query(self.request(worker),lambda _:None)
        # Releasing a foreign held result is not safe; adapter must fail before solve.
        self.assertEqual(b.calls,1)
        self.assertTrue(worker.cluster.invalid)
    def test_writer_crash_no_retry(self):
        worker,b,c,e=self.setup_worker()
        def fail(data): raise BrokenPipeError('fake IPC crash')
        with self.assertRaises(BrokenPipeError): worker.query(self.request(worker),fail)
        self.assertTrue(worker.cluster.invalid)
        self.assertIsNone(b.result_ref())
        self.assertEqual(b.calls,1)
    def test_strict_response(self):
        worker,b,c,e=self.setup_worker();r=self.execute(worker,e)
        for field,value in [('measurement_eligible',True),('schema','wrong'),('evidence',None)]:
            mutated=copy.deepcopy(r);mutated[field]=value
            with self.assertRaises(AdapterError):validate_response(mutated)
    def test_gates_before_native_import_or_clock(self):
        with patch('time.perf_counter_ns',side_effect=AssertionError('real clock forbidden')):
            for call in [production_gate,NativeClock().read,lambda:NativeBinding(self.w.p,'baseline'),
                         lambda:production_worker(None,None,None,None),lambda:runtime_dependencies([]),
                         lambda:NativeBinding.__new__(NativeBinding).prepare(None),
                         lambda:NativeBinding.__new__(NativeBinding).solve(None,1)]:
                with self.assertRaisesRegex(AdapterError,'PRODUCTION_EXECUTION_DISABLED'):call()
        self.assertNotIn('bmssp_native',sys.modules)
    def test_no_global_module_fallback(self):
        with patch.dict(sys.modules,{'bmssp_native':object()}):
            with self.assertRaisesRegex(AdapterError,'PRODUCTION_EXECUTION_DISABLED'):NativeBinding(self.w.p,'baseline')
    def test_existing_cli_rejects_all_execution_commands(self):
        from task15_cohort_a_runner.__main__ import main
        from contextlib import redirect_stdout
        import io
        for operation in ['collect','calibrate','run-real','benchmark','profile','analyze-confirmatory','promote','resume']:
            with redirect_stdout(io.StringIO()): self.assertEqual(main([operation]),2)

    def test_exact_import_transaction_fake_ops(self):
        from production_adapter.loading import import_verified
        from types import SimpleNamespace
        identity={'variant':'baseline','path':'/fake/original.so','sha256':'a'*64,'dependencies':['/fake/lib']}
        class Ops:
            def __init__(self): self.registry={};self.paths=[]
            def create(self,path): self.paths.append(path);return SimpleNamespace(__file__=path)
            def execute(self,module): pass
            def verify(self,path): return identity
            def dependencies(self,names): return {'/fake/lib':{'loaded_uuid':'f'*32}}
        ops=Ops();module,deps=import_verified(identity,{'/fake/original.so'},ops)
        self.assertEqual(ops.paths,['/fake/original.so'])
        self.assertIs(ops.registry['bmssp_native'],module)
        for kind in ['existing','alias','path','hash','dependency','crash']:
            ops=Ops()
            if kind=='existing': ops.registry['bmssp_native']=object()
            if kind=='alias': ops.registry['other']=SimpleNamespace(__file__='/fake/original.so')
            if kind=='path': ops.create=lambda path:SimpleNamespace(__file__='/global/fallback.so')
            if kind=='hash': ops.verify=lambda path:{**identity,'sha256':'b'*64}
            if kind=='dependency': ops.dependencies=lambda names:{}
            if kind=='crash':
                def crash(module): raise RuntimeError('fake import crash')
                ops.execute=crash
            with self.subTest(kind=kind),self.assertRaises((AdapterError,RuntimeError)):
                import_verified(identity,{'/fake/original.so'},ops)
            if kind not in ['existing','alias']: self.assertNotIn('bmssp_native',ops.registry)
        self.assertNotIn('bmssp_native',sys.modules)
    def test_ipc_frames_and_reply_identity(self):
        from production_adapter.ipc import decode,validate_reply
        worker,b,c,e=self.setup_worker();request=self.request(worker);r=self.execute(worker,e)
        payload=json.dumps(request).encode();frame=struct.pack('!I',len(payload))+payload
        self.assertEqual(decode(frame),request)
        validate_reply(r,request,self.w,self.runner)
        for payload in [b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}']:
            with self.assertRaises((AdapterError,ValueError)):decode(struct.pack('!I',len(payload))+payload)
        for frame in [b'',b'\0\0\0\1',b'\xff'*4,b'\0'*4]:
            with self.assertRaises(AdapterError): decode(frame)
        for field,value in [('runner_sha256','f'*64),('variant','wrong'),('warmup_excluded',False)]:
            changed=copy.deepcopy(r);changed[field]=value
            with self.assertRaises(AdapterError):validate_reply(changed,request,self.w,self.runner)
    def test_directed_reachable_path_and_invalid_reverse(self):
        g=self.parse(b'5 1\n1\n2\n3\n4\n5\n7 1 2 0.25\n')
        class Result:
            source=1;algorithm='native_bmssp_2025';diagnostics=diagnostic()
            distances=[0.0,.25,float('inf'),float('inf'),float('inf')]
            def belongs_to(self,graph):return graph is g
            def path(self,target):
                return {'reachable':target==2,'distance':.25 if target==2 else float('inf'),
                        'vertices':[1,2] if target==2 else [],'edges':[7] if target==2 else []}
        r=Result();proof=evidence(r,g,g,1,(2,3,4,5),'P1')
        self.assertTrue(proof['paths'][0]['reachable'])
        reverse=self.parse(b'5 1\n1\n2\n3\n4\n5\n7 2 1 0.25\n')
        r.belongs_to=lambda graph:True
        with self.assertRaisesRegex(AdapterError,'PATH_EDGE_ORIENTATION'): evidence(r,reverse,reverse,1,(2,3,4,5),'P1')
    def test_separate_process_state_and_coordinator(self):
        from production_adapter.ipc import Coordinator
        for kind in ['P1','P2']:
            unit=next(u for u in self.w.units if u['protocol']==kind)
            workers={v:self.setup_worker(unit,Cluster.frozen(self.w,unit['id'],v),v)[0] for v in ['baseline','candidate']}
            def invalidate(error):
                for worker in workers.values():worker.cluster.invalidate(error)
            peers={v:(lambda request,w=w:w.query(request,lambda frame:None)) for v,w in workers.items()}
            parent=Coordinator(self.w,unit['id'],self.runner,peers,invalidate)
            for _ in range(648):parent.step()
            self.assertEqual([w.cluster.cursor for w in workers.values()],[324,324])
            # Fresh pair to inject a transport crash, no solve or retry on other peer.
            workers={v:self.setup_worker(unit,Cluster.frozen(self.w,unit['id'],v),v)[0] for v in ['baseline','candidate']}
            def crash(request):raise EOFError('fake worker crash')
            parent=Coordinator(self.w,unit['id'],self.runner,{v:crash for v in workers},invalidate)
            with self.assertRaises(EOFError):parent.step()
            self.assertTrue(all(w.cluster.invalid for w in workers.values()))
            with self.assertRaises(AdapterError):parent.step()
    def test_real_graph_fake_binding_rejected(self):
        from production_adapter.graphs import GraphInput
        worker,b,c,e=self.setup_worker()
        graphs={r:GraphInput(g.vertices,g.edges,g.sha256,False) for r,g in worker.graphs.items()}
        with self.assertRaisesRegex(AdapterError,'FAKE_INPUT_REQUIRED'):
            Worker(self.w,worker.cluster,b.variant,b,c,graphs,self.runner)
    def test_no_native_import_from_supported_cli(self):
        from contextlib import redirect_stdout
        from task15_cohort_a_runner.__main__ import main
        import io
        with redirect_stdout(io.StringIO()):self.assertEqual(main(['plan']),0)
        self.assertNotIn('bmssp_native',sys.modules)


    def test_evidence_mutations_rejected(self):
        from production_adapter.ipc import validate_reply
        worker,b,c,e=self.setup_worker();request=self.request(worker);r=self.execute(worker,e)
        for field,value in [('distance_sha256','not-hash'),('work_sha256','f'*64),('materialization_count',100),('paths_sha256','f'*64),('legacy_query_seconds',999.0)]:
            changed=copy.deepcopy(r);changed['evidence'][field]=value
            with self.subTest(field=field),self.assertRaises(AdapterError):validate_reply(changed,request,self.w,self.runner)
        changed=copy.deepcopy(r);changed['evidence']['paths'][0]['target']=0
        with self.assertRaises(AdapterError):validate_reply(changed,request,self.w,self.runner)
    def test_boolean_position_rejected(self):
        worker,b,c,e=self.setup_worker();request=self.request(worker)
        request['query']['original_position']=False
        self.assertEqual(worker.query(request,lambda _:None)['status'],'ERROR')
        self.assertEqual(b.calls,0)
    def test_cross_variant_mismatch_invalidates_cluster(self):
        from production_adapter.ipc import Coordinator
        unit=next(u for u in self.w.units if u['protocol']=='P2')
        workers={v:self.setup_worker(unit,Cluster.frozen(self.w,unit['id'],v),v)[0] for v in ['baseline','candidate']}
        def peer(request):
            r=workers[request['query']['variant']].query(request,lambda _:None)
            if r['variant']=='candidate':r['evidence']['distance_sha256']='a'*64
            return r
        def invalidate(error):
            for w in workers.values():w.cluster.invalidate(error)
        parent=Coordinator(self.w,unit['id'],self.runner,{v:peer for v in workers},invalidate)
        with self.assertRaisesRegex(AdapterError,'CROSS_VARIANT_CORRECTNESS_MISMATCH'):
            for _ in range(648):parent.step()
        self.assertTrue(all(w.cluster.invalid for w in workers.values()))


if __name__ == '__main__': unittest.main()
