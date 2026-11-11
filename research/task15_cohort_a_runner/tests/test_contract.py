"""Closed IPC and synthetic ownership tests; no native imports or graph loading."""
import ast
import copy
import io
import json
import os
from pathlib import Path
import socket
import struct
import unittest
from contextlib import redirect_stdout
from task15_cohort_a_runner.errors import RunnerError
from task15_cohort_a_runner.wire import (canonical,strict_json,validate,request,response,frame,MAX_FRAME,validate_reply,FIELDS)
from task15_cohort_a_runner.transport import receive
from task15_cohort_a_runner.frozen import Workload,variants,expected_variant_records
from task15_cohort_a_runner.lifecycle import Machine
from task15_cohort_a_runner.__main__ import main
from task15_cohort_a_runner.controller import production_backend


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.work=Workload();cls.unit=cls.work.units[0]

    def reject(self,code,func):
        with self.assertRaises(RunnerError) as caught:func()
        self.assertEqual(caught.exception.code,code)

    def binding(self):return {'protocol_sha256':self.work.protocol.identity,'session_key':self.unit['session_key'],'unit_id':self.unit['id'],'variant':variants(self.unit['startup_order'])[0]}

    def machine(self):
        m=Machine(self.work.p,self.work.units);binding=self.binding()
        m.handle(request(binding,'HELLO',1,data={'fault':'none','fault_at':0}))
        for seq,region in enumerate(self.work.p['design']['regions'],2):m.handle(request(binding,'PREPARE',seq,data={'graph_kind':'SYNTHETIC_STRUCTURAL_ONLY'},region=region))
        return m,binding

    def send(self,m,binding,op,q=None):return m.handle(request(binding,op,m.sequence+1,query=q))

    def test_01_closed_message_fields(self):
        r=request(self.binding(),'HELLO',1,data={'fault':'none','fault_at':0});self.assertEqual(set(r),FIELDS)
        for key in r:
            q=dict(r);q.pop(key);self.reject('IPC_SCHEMA_FIELDS',lambda:validate(q,'REQUEST'))
        q={**r,'backend':'production'};self.reject('IPC_SCHEMA_FIELDS',lambda:validate(q,'REQUEST'))
        q=copy.deepcopy(r);q['data']['shell']='anything';self.reject('IPC_DATA_FIELDS',lambda:validate(q,'REQUEST'))

    def test_02_canonical_json_failures(self):
        for data,code in [(b'{!','IPC_MALFORMED_JSON'),(b'{"a":1,"a":2}','IPC_DUPLICATE_KEY'),(b'{"a":NaN}','IPC_NONFINITE'),(b'{"a":1e999}','IPC_NONFINITE'),(b'{ "a":1}','IPC_NONCANONICAL_JSON')]:
            self.reject(code,lambda:strict_json(data))

    def test_03_bounded_framing(self):
        for data,code in [(struct.pack('!I',MAX_FRAME+1),'IPC_FRAME_TOO_LARGE'),(b'\0\0','IPC_TRUNCATED_FRAME'),(struct.pack('!I',10)+b'{','IPC_TRUNCATED_FRAME'),(b'','IPC_EOF')]:
            a,b=socket.socketpair()
            try:
                if data:b.sendall(data)
                b.close();self.reject(code,lambda:receive(a.fileno(),.1,lambda x:None))
            finally:a.close();b.close()
        a,b=socket.socketpair()
        try:self.reject('IPC_TIMEOUT',lambda:receive(a.fileno(),.01,lambda x:None))
        finally:a.close();b.close()

    def test_04_duplicate_request_and_out_of_order(self):
        m,binding=self.machine();q=expected_variant_records(self.work.p,self.unit,binding['variant'])[0]
        r=request(binding,'QUERY',m.sequence+1,query=q);m.handle(r)
        self.reject('IPC_DUPLICATE_REQUEST',lambda:m.handle(r))
        self.reject('IPC_OUT_OF_ORDER',lambda:m.handle(request(binding,'RELEASE',m.sequence+2,query=q)))

    def test_05_worker_binding(self):
        m,b=self.machine();q=expected_variant_records(self.work.p,self.unit,b['variant'])[0]
        r=request({**b,'session_key':'wrong'},'QUERY',m.sequence+1,query=q)
        self.reject('IPC_BINDING_IDENTITY',lambda:m.handle(r))

    def test_06_source_position_occurrence(self):
        for key,value in [('original_position',99),('source_occurrence',99),('query_id','0'*64)]:
            m,b=self.machine();q=dict(m.expected[0]);q[key]=value
            self.reject('WORKER_QUERY_IDENTITY',lambda:self.send(m,b,'QUERY',q))

    def test_07_preparation_before_queries(self):
        m=Machine(self.work.p,self.work.units);b=self.binding();m.handle(request(b,'HELLO',1,data={'fault':'none','fault_at':0}))
        q=expected_variant_records(self.work.p,self.unit,b['variant'])[0]
        self.reject('WORKER_NOT_PREPARED',lambda:self.send(m,b,'QUERY',q))

    def test_08_result_retained_then_released(self):
        m,b=self.machine()
        for index,q in enumerate(m.expected[:9]):
            start=self.send(m,b,'QUERY',q);self.assertTrue(start['retained']);self.assertTrue(start['prior_result_cleared']);self.assertFalse(start['conceptual_timing_active'])
            if index==8:self.assertEqual(start['states'],['READY','TARGET_ACTIVE','TARGET_RETURNED','RESULT_RETAINED'])
            retained=m.result;del retained
            post=self.send(m,b,'FINGERPRINT',q);self.assertEqual(post['states'],['POST_TARGET_FINGERPRINTED']);self.assertTrue(post['retained'])
            released=self.send(m,b,'RELEASE',q);self.assertFalse(released['retained']);self.assertTrue(released['prior_result_cleared']);self.assertIsNone(m.result);self.assertIsNone(m.result_copy)
            self.assertIsNone(m.last_result())
        self.assertEqual(m.completed,9)

    def test_09_no_overlapping_result(self):
        m,b=self.machine();q=m.expected[0];self.send(m,b,'QUERY',q)
        self.reject('RESULT_STILL_RETAINED',lambda:self.send(m,b,'QUERY',m.expected[1]))

    def test_10_fingerprint_after_return_and_release_order(self):
        m,b=self.machine();q=m.expected[0]
        self.reject('RESULT_NOT_RETAINED',lambda:self.send(m,b,'FINGERPRINT',q))
        self.send(m,b,'QUERY',q);self.reject('RELEASE_BEFORE_FINGERPRINT',lambda:self.send(m,b,'RELEASE',q))
        m.conceptual_active=True;self.reject('FINGERPRINT_INSIDE_TARGET',lambda:self.send(m,b,'FINGERPRINT',q))

    def test_11_no_early_completion(self):
        m,b=self.machine();self.reject('WORKER_INCOMPLETE',lambda:self.send(m,b,'SHUTDOWN'))

    def test_12_b_slots_preserved(self):
        slots=self.work.slots(self.work.units)
        self.assertEqual(len(slots),16);self.assertEqual([s['cohort'] for s in slots], [c for s in self.work.p['design']['sessions'] for c in s['cohort_phase_order']])
        blocked=[s for s in slots if s['cohort']=='B'];self.assertEqual(len(blocked),8)
        self.assertTrue(all(s['status']=='NOT_EXECUTED' and s['gate']=='SCIENTIFIC_GATE_PENDING' for s in blocked))

    def test_13_unauthorized_commands_and_environment(self):
        for operation in ['collect','calibrate','benchmark','run-benchmark','profile','native','production','real-run','analyze','promote','resume','retry','replace']:
            with redirect_stdout(io.StringIO()) as out:code=main([operation])
            result=json.loads(out.getvalue());self.assertEqual(code,2);self.assertEqual(result['error'],'UNSUPPORTED_OPERATION');self.assertTrue(result['synthetic']);self.assertFalse(result['measurement_eligible'])
        self.reject('PRODUCTION_BACKEND_UNAVAILABLE',production_backend)
        with redirect_stdout(io.StringIO()) as out:code=main(['synthetic-run','--backend','production'])
        self.assertEqual(code,2);self.assertEqual(json.loads(out.getvalue())['error'],'ARGUMENT')

    def test_14_safety_source_boundary(self):
        package=Path(__file__).resolve().parents[1]/'task15_cohort_a_runner'
        forbidden={'bmssp_native','ctypes','numpy','networkx','osmnx','native_graph','pickle'}
        for file in package.glob('*.py'):
            tree=ast.parse(file.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):self.assertFalse(any(x.name.split('.')[0] in forbidden for x in node.names),str(file))
                if isinstance(node,ast.ImportFrom):self.assertNotIn((node.module or '').split('.')[0],forbidden,str(file))
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):self.assertNotIn(node.func.id,{'eval','exec','__import__'})
                if isinstance(node,ast.Attribute):self.assertNotIn(node.attr,{'perf_counter','perf_counter_ns','process_time','thread_time','dlopen','CDLL'})

    def test_15_response_identity_and_data_closure(self):
        m,b=self.machine();r=request(b,'QUERY',m.sequence+1,query=m.expected[0]);reply=response(r,m.handle(r))
        for key,value,code in [('variant','baseline' if b['variant']=='candidate' else 'candidate','IPC_WRONG_VARIANT'),('session_key','wrong','IPC_WRONG_SESSION'),('unit_id','wrong','IPC_WRONG_UNIT'),('original_position',-1,'IPC_WRONG_POSITION')]:
            bad=copy.deepcopy(reply);bad[key]=value;self.reject(code,lambda:validate_reply(r,bad))
        bad=copy.deepcopy(reply);bad['data']['latency_seconds']=1;self.reject('IPC_DATA_FIELDS',lambda:validate_reply(r,bad))

    def test_16_p1_p2_worker_expectations_against_frozen_stream(self):
        for unit in self.work.units:
            for variant in ['baseline','candidate']:
                observed=[{k:q[k] for k in ['query_id','phase','region','execution_index','original_position','source_id','source_occurrence']} for q in self.work.queries[unit['id']] if q['variant']==variant]
                self.assertEqual(expected_variant_records(self.work.p,unit,variant),observed)

    def test_17_valid_json_wrong_types_are_classified(self):
        r=request(self.binding(),'HELLO',1,data={'fault':'none','fault_at':0})
        for key in ['op','kind','schema_version','status','error_code','variant','phase']:
            q=copy.deepcopy(r);q[key]=[];self.reject('IPC_SCHEMA_TYPE',lambda:validate(q,'REQUEST'))
        q=copy.deepcopy(r);q['data']['fault']=[];self.reject('IPC_FAULT_CONFIG',lambda:validate(q,'REQUEST'))
