"""Static and synthetic controls only. Never imports production engine/test modules."""
from __future__ import annotations
import ast
from collections import Counter
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from task15_harness.__main__ import main
from task15_harness.artifacts import inspect_file, inspect_identities, capacity, inspect_storage
from task15_harness.errors import ControlError
from task15_harness.g8 import classify_synthetic
from task15_harness.integrity import canonical, digest, strict_json_bytes
from task15_harness.manifest import prepare_manifest, seal, transition, validate_manifest
from task15_harness.output import create_bundle, read_bundle
from task15_harness.planning import compile_plan, plan_counts, query_records, validate_plan
from task15_harness.protocol import Protocol, load_protocol, validate_document, PACKAGE_ROOT
from task15_harness.schedule import validate_schedule
from task15_harness.simulation import simulate, reject_synthetic_for_measurement

REPO = PACKAGE_ROOT.parents[1]
NEGATIVE_RESULTS = []


class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        NEGATIVE_RESULTS.clear()
        cls.protocol = load_protocol(REPO)
        cls.original = cls.protocol.data()
        cls.plan = compile_plan(cls.protocol)

    def expect(self, code, fn):
        with self.assertRaises(ControlError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)
        NEGATIVE_RESULTS.append({'case':self.id(),'expected':code,'observed':caught.exception.code,'scope':'STATIC_OR_SYNTHETIC'})

    def mutate(self):
        return deepcopy(self.original)

    def p2(self, p):
        return next(r for r in p['design']['base_schedule'] if r['protocol']=='P2')

    def test_01_protocol_hash_mismatch(self):
        p=self.mutate();p['identity']['sha256']='0'*64
        self.expect('PROTOCOL_HASH',lambda:validate_document(p))

    def test_02_wrong_version(self):
        p=self.mutate();p['version']='1.0.0'
        self.expect('PROTOCOL_VERSION',lambda:validate_document(p))

    def test_03_unknown_schema_field(self):
        p=self.mutate();p['design']['allow_collection']=True
        self.expect('SCHEMA_UNKNOWN',lambda:validate_document(p))

    def test_04_invalid_trial_id(self):
        p=self.mutate();p['design']['base_schedule'][0]['id']='wrong'
        self.expect('TRIAL_ID',lambda:validate_schedule(p))

    def test_05_duplicate_position(self):
        p=self.mutate();a=self.p2(p)['positions_by_region']['seremban-small'];a[1]=a[0]
        self.expect('POSITION_DUPLICATE',lambda:validate_schedule(p))

    def test_06_missing_position(self):
        p=self.mutate();self.p2(p)['positions_by_region']['seremban-small'].pop()
        self.expect('POSITION_MISSING',lambda:validate_schedule(p))

    def test_07_trial_50_50(self):
        p=self.mutate();a=self.p2(p)['P2_pair_orders_by_region']['seremban-small'];a[0]='BA'if a[0]=='AB'else'AB'
        self.expect('P2_TRIAL_BALANCE',lambda:validate_schedule(p))

    def test_08_original_position_16_16(self):
        p=self.mutate();a=self.p2(p)['P2_pair_orders_by_region']['seremban-small'];j=next(i for i in range(1,100)if a[i]!=a[0]);a[0],a[j]=a[j],a[0]
        self.expect('P2_POSITION_BALANCE',lambda:validate_schedule(p))

    def test_09_session_2_2_with_global_balance_preserved(self):
        p=self.mutate();rr=sorted([r for r in p['design']['base_schedule']if r['protocol']=='P2'],key=lambda r:r['trial_within_protocol']);a,b=rr[0],rr[4];g='seremban-small'
        aa={pos:i for i,pos in enumerate(a['positions_by_region'][g])};bb={pos:i for i,pos in enumerate(b['positions_by_region'][g])};oa=a['P2_pair_orders_by_region'][g];ob=b['P2_pair_orders_by_region'][g]
        x=next(pos for pos in range(100)if oa[aa[pos]]=='AB'and ob[bb[pos]]=='BA');y=next(pos for pos in range(100)if oa[aa[pos]]=='BA'and ob[bb[pos]]=='AB')
        for row,index in [(oa,aa),(ob,bb)]:row[index[x]],row[index[y]]=row[index[y]],row[index[x]]
        self.expect('P2_SESSION_BALANCE',lambda:validate_schedule(p))

    def test_10_p1_orthogonality(self):
        p=self.mutate();r=next(r for r in p['design']['base_schedule']if r['protocol']=='P1');r['P1_variant_order']='BA'if r['P1_variant_order']=='AB'else'AB'
        self.expect('P1_ORTHOGONALITY',lambda:validate_schedule(p))

    def test_11_graph_hash_mismatch(self):
        with tempfile.TemporaryDirectory()as tmp:
            f=Path(tmp)/'graph.graphml';f.write_text('<graph/>')
            result=inspect_file('graph',f,'0'*64)
            self.assertEqual(result['status'],'MISMATCH');NEGATIVE_RESULTS.append({'case':self.id(),'expected':'MISMATCH','observed':result['status']});self.assertIsNotNone(result['actual_sha256'])

    def test_12_binary_hash_mismatch_no_native_load(self):
        with tempfile.TemporaryDirectory()as tmp:
            f=Path(tmp)/'fixture.so';f.write_bytes(b'SYNTHETIC_NOT_A_BINARY')
            result=inspect_file('binary',f,'0'*64);self.assertEqual(result['status'],'MISMATCH');NEGATIVE_RESULTS.append({'case':self.id(),'expected':'MISMATCH','observed':result['status']})

    def test_13_missing_binary(self):
        with tempfile.TemporaryDirectory()as tmp:
            r=inspect_file('binary',Path(tmp)/'absent.so','0'*64)
            self.assertEqual(r['status'],'MISSING');NEGATIVE_RESULTS.append({'case':self.id(),'expected':'MISSING','observed':r['status']});self.assertIsNone(r['actual_sha256'])

    def test_14_unreadable_evidence(self):
        with tempfile.TemporaryDirectory()as tmp:
            f=Path(tmp)/'unreadable';f.write_bytes(b'fixture');f.chmod(0)
            try:
                result=inspect_file('evidence',f,'0'*64);self.assertEqual(result['status'],'UNREADABLE');NEGATIVE_RESULTS.append({'case':self.id(),'expected':'UNREADABLE','observed':result['status']})
            finally:f.chmod(0o600)

    def draft(self):
        return prepare_manifest(self.protocol,checked=False)

    def test_15_stale_manifest_hash(self):
        m=self.draft();m['provenance']['scope']='changed'
        self.expect('MANIFEST_HASH',lambda:validate_manifest(self.protocol,m))

    def test_16_modified_plan_even_after_rehash(self):
        p=deepcopy(self.plan);p['units'][0]['startup_order']='BA'if p['units'][0]['startup_order']=='AB'else'AB';p.pop('identity_sha256');p['identity_sha256']=digest(p)
        self.expect('PLAN_MODIFIED',lambda:validate_plan(self.protocol,p))

    def test_17_unauthorized_state_transition(self):
        m=self.draft()
        for state in ['APPROVED_FOR_CALIBRATION','CALIBRATION_COMPLETE','APPROVED_FOR_COLLECTION','COLLECTION_COMPLETE','INVALID']:
            with self.subTest(state=state):self.expect('STATE_FORBIDDEN',lambda:transition(self.protocol,m,state))

    def test_18_duplicate_output_directory(self):
        with tempfile.TemporaryDirectory()as tmp:
            out=Path(tmp)/'bundle';create_bundle(self.protocol,out,{'fixture.json':b'{}\n'})
            self.expect('OUTPUT_EXISTS',lambda:create_bundle(self.protocol,out,{'fixture.json':b'changed'}))
            self.assertEqual((out/'fixture.json').read_bytes(),b'{}\n')

    def test_19_interrupted_creation(self):
        def broken():
            yield b'partial'
            raise RuntimeError('SYNTHETIC_INTERRUPTION')
        with tempfile.TemporaryDirectory()as tmp:
            out=Path(tmp)/'interrupted'
            self.expect('OUTPUT_INTERRUPTED',lambda:create_bundle(self.protocol,out,{'fixture.json':broken()}))
            self.assertFalse((out/'COMPLETED.json').exists())
            self.expect('BUNDLE_INCOMPLETE',lambda:read_bundle(out, expected_payloads={'fixture.json'}))
            self.expect('OUTPUT_EXISTS',lambda:create_bundle(self.protocol,out,{'fixture.json':b'{}'}))

    def test_20_unsupported_commands_and_environment_bypass(self):
        with patch.dict(os.environ,{'TASK15_ALLOW_COLLECTION':'1','TASK15_APPROVED':'true'}):
            for operation in ['collect','calibrate','run-benchmark','trace','profile','optimize','promote']:
                with self.subTest(operation=operation),io.StringIO()as out,patch('sys.stdout',out):
                    self.assertEqual(main([operation]),2)
                    actual=json.loads(out.getvalue())['error'];self.assertEqual(actual,'UNSUPPORTED_OPERATION');NEGATIVE_RESULTS.append({'case':self.id()+'/'+operation,'expected':'UNSUPPORTED_OPERATION','observed':actual})

    def test_21_repeated_source_position_identity(self):
        p=self.mutate();a=p['inputs']['seremban-small']['source_positions'];a[11]=a[2]
        self.expect('SOURCE_IDENTITY',lambda:validate_schedule(p))

    def test_22_cross_protocol_field(self):
        p=self.mutate();self.p2(p)['P1_variant_order']='AB'
        self.expect('CROSS_PROTOCOL_FIELD',lambda:validate_document(p))

    def fixture(self):
        return {'label':'SYNTHETIC_G8_FIXTURE','entry':4096,'loop_headers':[],
                'instructions':[{'address':4096,'opcode':'sub','operands':'sp, sp, #16'},
                                {'address':4100,'opcode':'ret','operands':''}]}

    def test_23_unsupported_g8_normalization(self):
        self.expect('G8_UNSUPPORTED_NORMALIZATION',lambda:classify_synthetic(self.fixture(),self.fixture(),'drop_registers'))
        other=self.fixture();other['instructions'][0]['opcode']='unknown'
        self.expect('G8_UNSUPPORTED_NORMALIZATION',lambda:classify_synthetic(other,self.fixture()))

    def test_24_synthetic_trial_failure_whole_cluster(self):
        first=next(query_records(self.protocol,self.plan));events=list(simulate(self.protocol,self.plan,fail_query=first['query_id'],interrupt_after=8))
        verdict=next(x for x in events if x['event']=='CLUSTER_VERDICT')
        self.assertEqual(verdict['status'],'INVALID');NEGATIVE_RESULTS.append({'case':self.id(),'expected':'INVALID','observed':verdict['status']});self.assertTrue(verdict['whole_cluster_all_regions_both_variants'])
        self.assertTrue(any(x['event']=='SYNTHETIC_FAILURE'for x in events))
        self.assertTrue(any(x['event']=='SKIPPED_INVALID_CLUSTER'for x in events))
        for event in events:
            self.assertEqual(event['label'],'SYNTHETIC_CONTROL_PLANE_TEST')
            self.assertFalse({'seconds','wall_seconds','cpu_seconds'}&event.keys())

    def test_25_silent_retry_forbidden(self):
        self.expect('RETRY_FORBIDDEN',lambda:next(simulate(self.protocol,self.plan,attempt=2)))

    def test_26_strict_json_duplicates_and_nonfinite(self):
        self.expect('JSON_DUPLICATE_KEY',lambda:strict_json_bytes(b'{"x":1,"x":2}'))
        self.expect('JSON_NONFINITE',lambda:strict_json_bytes(b'{"x":NaN}'))

    def test_27_protocol_immutable_and_constructor_fail_closed(self):
        data=self.protocol.data();data['version']='tampered'
        self.assertEqual(self.protocol.data()['version'],'1.1.0')
        self.expect('PROTOCOL_VERSION',lambda:Protocol(canonical(data),REPO))

    def test_28_all_stored_schedule_counts(self):
        report=validate_schedule(self.original)
        for g in self.original['design']['regions']:
            actual=report['protocols']['P2']['regions'][g]
            self.assertEqual(actual['AB_by_original_position'],[16]*100)
            self.assertEqual(actual['AB_by_session_original_position'],[[2]*100 for _ in range(8)])
        self.assertEqual(report['sources']['seremban-small']['distinct'],96)

    def test_29_full_enumeration_counts_and_query_ids(self):
        counts=Counter();ids=set();last=None
        for q in query_records(self.protocol,self.plan):
            self.assertNotIn(q['query_id'],ids);ids.add(q['query_id'])
            counts[f'{q["cohort"]}/{q["phase"]}']+=1;last=q
            self.assertEqual(q['source_id'],self.original['inputs'][q['region']]['source_positions'][q['original_position']])
        expected=plan_counts(self.protocol,self.plan)
        self.assertEqual(dict(counts),expected['by_cohort_phase'])
        self.assertEqual(len(ids),expected['query_record_count'])
        # Serialization inventory only: this does not approve cross-lane execution.
        self.assertEqual(last['plan_lane'],'allocation_stack_companions')

    def test_30_p1_batch_and_p2_interleaving(self):
        from itertools import groupby
        for unit in [next(x for x in self.plan['units']if x['protocol']=='P1'),next(x for x in self.plan['units']if x['protocol']=='P2')]:
            queries=(q for q in query_records(self.protocol,self.plan)if q['trial_id']==unit['id']and q['region']==self.original['design']['regions'][0]and q['phase']=='target')
            rows=list(queries)
            if unit['protocol']=='P1':self.assertEqual([len(list(group))for _,group in groupby(rows,key=lambda q:q['variant'])],[100,100])
            else:
                for a,b in zip(rows[::2],rows[1::2]):
                    self.assertEqual(a['original_position'],b['original_position']);self.assertNotEqual(a['variant'],b['variant'])

    def test_31_manifest_determinism(self):
        self.assertEqual(canonical(self.draft()),canonical(self.draft()))

    def test_32_manifest_fake_approval(self):
        m=self.draft();m['authorization']['execution']=True;m=seal(m)
        self.expect('AUTHORIZATION',lambda:validate_manifest(self.protocol,m))

    def test_33_manifest_cannot_weaken_requirements(self):
        m=self.draft();m['requirements']['storage_status']='STORAGE_CAPACITY_VERIFIED';m=seal(m)
        self.expect('MANIFEST_REQUIREMENTS',lambda:validate_manifest(self.protocol,m))

    def test_34_storage_and_capacity_no_allocation(self):
        c=capacity(self.protocol);self.assertEqual(c['event_cap_per_query'],4000000)
        self.assertEqual(c['selected_positions'],41);self.assertEqual(c['worst_timed_C_event_bytes'],335872000000)
        self.assertFalse(c['buffers_allocated'])
        self.assertEqual(inspect_storage(self.protocol,None)['status'],'NOT_CHECKED')
        with tempfile.TemporaryDirectory()as tmp:
            r=inspect_storage(self.protocol,Path(tmp));self.assertEqual(r['destination'],str(Path(tmp).resolve()))
            self.assertIn(r['status'],['STORAGE_CAPACITY_VERIFIED','INSUFFICIENT_CAPACITY'])

    def test_35_g8_classes_no_auto_approval(self):
        self.assertEqual(classify_synthetic(self.fixture(),self.fixture())['class'],'I')
        moved=self.fixture();moved['entry']+=64
        for x in moved['instructions']:x['address']+=64
        result=classify_synthetic(self.fixture(),moved);self.assertEqual(result['class'],'L');self.assertFalse(result['eligible'])
        changed=self.fixture();changed['instructions'][0]['operands']='sp, sp, #96'
        self.assertEqual(classify_synthetic(self.fixture(),changed)['class'],'M')

    def test_36_no_real_g8_claim(self):
        f=self.fixture();f['label']='REAL_BINARY'
        self.expect('G8_ACTUAL_PENDING',lambda:classify_synthetic(f,self.fixture()))

    def test_37_synthetic_not_measurement(self):
        self.expect('SYNTHETIC_NOT_MEASUREMENT',lambda:reject_synthetic_for_measurement({'label':'SYNTHETIC_CONTROL_PLANE_TEST'}))

    def test_38_no_native_import_or_execution_facility(self):
        for path in (PACKAGE_ROOT/'task15_harness').glob('*.py'):
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    self.assertFalse(any(x.name in ['bmssp_native','ctypes','native_graph','pickle']for x in node.names))
                if isinstance(node,ast.ImportFrom):
                    self.assertNotIn(node.module,{'bmssp_native','ctypes','native_graph','pickle'})
                if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):
                    self.assertNotIn(node.func.id,{'eval','exec','__import__'})

    def test_39_protected_output_path(self):
        self.expect('OUTPUT_PROTECTED',lambda:create_bundle(self.protocol,REPO/'should-not-exist',{'x':b'x'}))

    def test_40_invalid_transition_chain(self):
        m=self.draft();m['state']='AWAITING_APPROVAL';m=seal(m)
        self.expect('STATE_TRANSITION',lambda:validate_manifest(self.protocol,m))

    def test_41_skip_external_cannot_reach_static_verified(self):
        self.expect('STATIC_GATE',lambda:prepare_manifest(self.protocol,state='STATIC_VERIFIED',checked=False))

    def test_42_manifest_schema_unknown_field(self):
        m=self.draft();m['authorization']['allow_override']=True;m=seal(m)
        self.expect('SCHEMA_UNKNOWN',lambda:validate_manifest(self.protocol,m))

    def test_43_bundle_detects_modified_file(self):
        with tempfile.TemporaryDirectory()as tmp:
            out=Path(tmp)/'bundle';create_bundle(self.protocol,out,{'fixture.json':b'{}'})
            (out/'fixture.json').write_bytes(b'changed')
            self.expect('BUNDLE_HASH',lambda:read_bundle(out, expected_payloads={'fixture.json'}))

    def test_44_no_forged_approval_provenance(self):
        m=self.draft();m['provenance']['review_status']='approved for collection';m=seal(m)
        self.expect('MANIFEST_PROVENANCE',lambda:validate_manifest(self.protocol,m))

    def test_45_no_forged_transition_provenance(self):
        m=self.draft();m['transitions']=[{'from':'DRAFT','to':'STATIC_VERIFIED','provenance':'independent approval'}];m['state']='STATIC_VERIFIED';m=seal(m)
        self.expect('STATE_TRANSITION',lambda:validate_manifest(self.protocol,m))
