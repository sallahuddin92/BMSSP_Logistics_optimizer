"""v1.2 static integration and independent pre-upgrade payload-ledger controls."""
from collections import Counter
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from task15_harness.__main__ import main
from task15_harness.errors import ControlError, require
from task15_harness.integrity import canonical, digest, read_json, strict_json_bytes
from task15_harness.manifest import prepare_manifest, validate_manifest, seal
from task15_harness.planning import compile_plan, query_records, validate_plan
from task15_harness.protocol import (PACKAGE_ROOT, PROTOCOL_HASH, PROTOCOL_FILE_HASH, PARENT_HASH,
    LEDGER_HASH, FROZEN_FILES, Protocol, load_protocol, validate_document, canonical_protocol_hash)
from task15_harness.simulation import simulate, reject_synthetic_for_measurement

REPO=PACKAGE_ROOT.parents[1]
ORACLE=PACKAGE_ROOT/'tests/fixtures/v1.1-query-oracle.json'
ORACLE_HASH='8dcc00537d586b61f97b0fb20dc489ca7e900c64c89bc5cb8b52afc4318be975'
NAMESPACE='6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f'
ACTIVE='c41e45bccb68abdf03bab40ea793837a7f508fde17634c1aa8b358a3d82fceb0'
NEGATIVE_RESULTS=[]
NEW_PROVENANCE={'protocol_sha256','protocol_version','query_identity_namespace_sha256','resolved_diagnostic_order_sha256'}


def reconcile(records, oracle):
    """Independent frozen scientific payload/ID oracle, captured before replacing loader.

    Does not call the new planner to construct expected payloads or identifiers.
    """
    groups={};population=[];unit_order=[]
    for record in records:
        require(record['protocol_sha256']==ACTIVE and record['protocol_version']=='1.2.0',
                'QUERY_ACTIVE_PROVENANCE','active provenance')
        require(record['query_identity_namespace_sha256']==NAMESPACE,'QUERY_NAMESPACE','legacy identity')
        require(record['resolved_diagnostic_order_sha256']=='3e22c8ebfbdb23af04059bece54734844ee58664a3c43abd9170625922cf20ba',
                'QUERY_ORDER_PROVENANCE','resolved order')
        key=record['trial_id']
        require(key in oracle['by_unit'],'QUERY_UNIT','unknown unit')
        if not unit_order or unit_order[-1]!=key:unit_order.append(key)
        group=groups.setdefault(key,{'payload':hashlib.sha256(),'ids':hashlib.sha256(),'count':0})
        group['payload'].update(canonical({k:v for k,v in record.items() if k not in NEW_PROVENANCE})+b'\n')
        group['ids'].update(canonical(record['query_id'])+b'\n');group['count']+=1;population.append(record['query_id'])
    require(len(population)==len(set(population)),'QUERY_DUPLICATE','collision')
    require(set(groups)==set(oracle['by_unit']),'QUERY_UNIT','missing units')
    for key,g in groups.items():
        expected=oracle['by_unit'][key]
        require(g['count']==expected['count'],'QUERY_COUNT',key)
        require(g['payload'].hexdigest()==expected['ordered_scientific_payload_sha256'],'QUERY_PAYLOAD',key)
        require(g['ids'].hexdigest()==expected['ordered_query_ids_sha256'],'QUERY_IDENTITIES',key)
    require(len(population)==oracle['record_count'] and digest(sorted(population))==oracle['query_id_population_sha256'],
            'QUERY_POPULATION','complete multiset')
    return unit_order,groups


class V12Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        NEGATIVE_RESULTS.clear()
        cls.protocol=load_protocol(REPO);cls.p=cls.protocol.data();cls.plan=compile_plan(cls.protocol)
        require(hashlib.sha256(ORACLE.read_bytes()).hexdigest()==ORACLE_HASH,'BASELINE_ORACLE_HASH','immutable pre-upgrade fixture')
        cls.oracle=read_json(ORACLE)

    def reject(self,code,action):
        with self.assertRaises(ControlError) as caught:action()
        self.assertEqual(caught.exception.code,code)
        NEGATIVE_RESULTS.append({'case':self.id(),'expected':code,'observed':caught.exception.code,'scope':'STATIC_OR_SYNTHETIC'})

    def altered(self):
        p=deepcopy(self.p);return p,p['design']['resolved_diagnostic_order']

    def rehash(self,p):
        p['design']['resolved_diagnostic_order_sha256']=digest(p['design']['resolved_diagnostic_order'])
        p['identity']['sha256']=canonical_protocol_hash(p)

    @contextmanager
    def copied_repo(self):
        with tempfile.TemporaryDirectory(prefix='task15-static-v12-') as tmp:
            root=Path(tmp);(root/'docs').mkdir()
            for name in FROZEN_FILES:shutil.copyfile(REPO/name,root/name)
            yield root

    def test_01_old_protocol_cannot_be_active(self):
        old=read_json(REPO/'docs/task15_tail_attribution_protocol_v1.1.0.json')
        self.reject('PROTOCOL_VERSION',lambda:validate_document(old))
        with self.copied_repo() as root:
            shutil.copyfile(root/'docs/task15_tail_attribution_protocol_v1.1.0.json',root/'docs/task15_tail_attribution_protocol_v1.2.0.json')
            self.reject('PROTOCOL_VERSION',lambda:load_protocol(root))

    def test_02_stale_canonical(self):
        p,r=self.altered();p['identity']['sha256']='0'*64
        self.reject('PROTOCOL_HASH',lambda:validate_document(p))

    def test_03_stale_file_byte_hash(self):
        with self.copied_repo() as root:
            path=root/'docs/task15_tail_attribution_protocol_v1.2.0.json';path.write_bytes(path.read_bytes()+b' ')
            self.reject('PROTOCOL_FILE_HASH',lambda:load_protocol(root))

    def test_04_altered_preregistration(self):
        with self.copied_repo() as root:
            path=root/'docs/task15_tail_attribution_preregistration_v1.2.0.md';path.write_bytes(path.read_bytes()+b'changed')
            self.reject('FROZEN_FILE_HASH',lambda:load_protocol(root))

    def test_05_altered_ledger(self):
        with self.copied_repo() as root:
            path=root/'docs/task15_tail_attribution_amendment_v1.2.0.json';ledger=read_json(path)
            ledger['independent_approval_status']='APPROVED';ledger.pop('identity_sha256');ledger['identity_sha256']=digest(ledger)
            path.write_bytes(canonical(ledger))
            self.reject('AMENDMENT_HASH',lambda:load_protocol(root))

    def test_06_missing_historical_parent(self):
        with self.copied_repo() as root:
            (root/'docs/task15_tail_attribution_preregistration.md').unlink()
            self.reject('HISTORICAL_FILE_MISSING',lambda:load_protocol(root))

    def test_07_forged_independent_approval(self):
        p,r=self.altered();p['ordering_amendment']['approval_status']='APPROVED';self.rehash(p)
        self.reject('SCIENTIFIC_APPROVAL',lambda:validate_document(p))

    def test_08_missing_condition_block(self):
        p,r=self.altered();r['condition_blocks'].pop();self.rehash(p)
        self.reject('ORDER_UNIT_MEMBERSHIP',lambda:validate_document(p))

    def test_09_duplicate_condition_block(self):
        p,r=self.altered();r['condition_blocks'][1]=deepcopy(r['condition_blocks'][0]);self.rehash(p)
        self.reject('ORDER_UNIT_MEMBERSHIP',lambda:validate_document(p))

    def test_10_changed_diagnostic_session(self):
        p,r=self.altered();r['condition_blocks'][0]['diagnostic_session']=1;self.rehash(p)
        self.reject('ORDER_SESSION',lambda:validate_document(p))

    def test_11_companion_wrong_session(self):
        p,r=self.altered();next(b for b in r['condition_blocks'] if b['lane']=='COMPANION')['diagnostic_session']=1;self.rehash(p)
        self.reject('ORDER_SESSION',lambda:validate_document(p))

    def test_12_companions_globally_appended(self):
        p,r=self.altered();r['condition_blocks'].sort(key=lambda b:b['lane']=='COMPANION');self.rehash(p)
        self.reject('ORDER_SEQUENCE',lambda:validate_document(p))

    def test_13_reversed_conditions(self):
        p,r=self.altered();r['condition_blocks'][0],r['condition_blocks'][1]=r['condition_blocks'][1],r['condition_blocks'][0];self.rehash(p)
        self.reject('ORDER_SEQUENCE',lambda:validate_document(p))

    def test_14_changed_schedule_reference(self):
        p,r=self.altered();r['condition_blocks'][0]['schedule_ref']='S00-P2-T03';self.rehash(p)
        self.reject('ORDER_REFERENCE',lambda:validate_document(p))

    def test_15_changed_variant_order(self):
        p,r=self.altered();r['condition_blocks'][0]['startup_order']='BA';self.rehash(p)
        self.reject('ORDER_VARIANT',lambda:validate_document(p))

    def test_16_changed_original_occurrence(self):
        def corrupt():
            first=True
            for record in query_records(self.protocol,self.plan):
                if first:record['source_occurrence']+=1;first=False
                yield record
        self.reject('QUERY_PAYLOAD',lambda:reconcile(corrupt(),self.oracle))

    def test_17_wrong_query_namespace(self):
        p,r=self.altered();r['query_identity_policy']['namespace_protocol_sha256']=ACTIVE;self.rehash(p)
        self.reject('QUERY_NAMESPACE',lambda:validate_document(p))

    def test_18_changed_active_provenance(self):
        q=next(query_records(self.protocol,self.plan));q['protocol_sha256']=NAMESPACE
        self.reject('QUERY_ACTIVE_PROVENANCE',lambda:reconcile([q],self.oracle))

    def test_19_query_id_collision(self):
        q=next(query_records(self.protocol,self.plan))
        with patch('task15_harness.simulation.query_records',return_value=iter([q,q])):
            self.reject('QUERY_DUPLICATE',lambda:list(simulate(self.protocol,self.plan)))

    def test_20_stale_plan_identity(self):
        plan=deepcopy(self.plan);plan['identity_sha256']='0'*64
        self.reject('PLAN_MODIFIED',lambda:validate_plan(self.protocol,plan))
        plan=deepcopy(self.plan);plan['units'][-1]['condition']='changed';plan.pop('identity_sha256');plan['identity_sha256']=digest(plan)
        self.reject('PLAN_MODIFIED',lambda:validate_plan(self.protocol,plan))

    def test_21_old_manifest_resealed(self):
        manifest=prepare_manifest(self.protocol,checked=False)
        manifest['protocol']['version']='1.1.0';manifest['protocol']['canonical_sha256']=NAMESPACE
        self.reject('MANIFEST_PROTOCOL',lambda:validate_manifest(self.protocol,seal(manifest)))
        manifest=prepare_manifest(self.protocol,checked=False);manifest['schema_version']='1'
        self.reject('SCHEMA_ENUM',lambda:validate_manifest(self.protocol,seal(manifest)))
        current=prepare_manifest(self.protocol,checked=False)
        report=validate_manifest(self.protocol,current)
        self.assertEqual(report['protocol']['canonical_sha256'],ACTIVE)
        self.assertEqual(report['protocol']['resolved_diagnostic_order_sha256'],
                         self.p['design']['resolved_diagnostic_order_sha256'])
        self.assertEqual(report['plan_identity_sha256'],self.plan['identity_sha256'])

    def test_22_synthetic_not_measurements(self):
        self.reject('SYNTHETIC_NOT_MEASUREMENT',lambda:reject_synthetic_for_measurement(next(simulate(self.protocol,self.plan,interrupt_after=0))))

    def test_23_unauthorized_commands(self):
        for command in ['calibrate','collect','run-benchmark','profile','promote','trace']:
            with redirect_stdout(io.StringIO()) as stream:self.assertEqual(main([command]),2)
            value=json.loads(stream.getvalue());self.assertEqual(value['error'],'UNSUPPORTED_OPERATION')
            NEGATIVE_RESULTS.append({'case':self.id(),'command':command,'expected':'UNSUPPORTED_OPERATION','observed':value['error']})

    def test_24_missing_modified_redirected_artifact_identities(self):
        for key,value in [('status','MISSING'),('actual_sha256','0'*64),('path','/redirected/artifact')]:
            manifest=prepare_manifest(self.protocol,checked=False);manifest['identities']['records'][0][key]=value
            self.reject('IDENTITY_REPORT_CHANGED',lambda:validate_manifest(self.protocol,seal(manifest)))

    def test_25_full_query_and_payload_ledger(self):
        order,groups=reconcile(query_records(self.protocol,self.plan),self.oracle)
        primary=[u['id'] for u in self.oracle['primary_units']]
        expected_diagnostic=[b['unit_id'] for b in self.p['design']['resolved_diagnostic_order']['condition_blocks']]
        self.assertEqual(order,primary+expected_diagnostic)
        self.assertEqual(self.plan['units'][:128],self.oracle['primary_units'])
        self.assertEqual(len(groups),228)
        self.assertEqual(len(order),228)

    def test_26_independent_order_reference_and_join(self):
        spec=importlib.util.spec_from_file_location('frozen_v12_reference',REPO/'research/task15_ordering_v1_2/validate_amendment.py')
        reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
        report=reference.verify_order(self.p,read_json(REPO/'docs/task15_tail_attribution_protocol_v1.1.0.json'))
        self.assertEqual(report['blocks_by_session'],{0:26,1:24,2:26,3:24})
        blocks=self.p['design']['resolved_diagnostic_order']['condition_blocks']
        self.assertEqual([u['resolved_condition_block'] for u in self.plan['units'][128:]],blocks)
        self.assertEqual(self.plan['unit_order'],[u['id'] for u in self.plan['units']])
        self.assertEqual(self.plan['diagnostic_source_lanes']['main'],self.oracle['main_diagnostic_ids'])
        self.assertEqual(self.plan['diagnostic_source_lanes']['allocation_stack_companions'],self.oracle['companion_ids'])
        self.assertFalse(self.plan['dispatchable']);self.assertFalse(self.plan['collection_authorized'])

    def test_27_full_simulation_order_and_whole_cluster_failure(self):
        order=[];counts=Counter();failed=next(u for u in self.plan['units'] if u['session_kind']=='DIAGNOSTIC' and u['mode']!='allocation_stacks')
        selected=next(q for q in query_records(self.protocol,self.plan) if q['trial_id']==failed['id'])
        invalid=[]
        for event in simulate(self.protocol,self.plan,fail_query=selected['query_id']):
            self.assertEqual(event['protocol']['canonical_sha256'],ACTIVE)
            self.assertEqual(event['label'],'SYNTHETIC_CONTROL_PLANE_TEST')
            if 'query' in event:
                q=event['query'];counts[q['trial_id']]+=1
                if not order or order[-1]!=q['trial_id']:order.append(q['trial_id'])
            elif event['event']=='CLUSTER_VERDICT' and event['status']=='INVALID':invalid.append(event['cluster'])
        self.assertEqual(order,self.plan['unit_order'])
        self.assertEqual(sum(counts.values()),138696)
        self.assertEqual(invalid,[selected['paired_cluster_id']])
        paired=[u for u in self.plan['units'] if u['diagnostic_id']==failed['diagnostic_id']]
        self.assertEqual(len(paired),2)
        self.assertTrue(all(counts[u['id']]>0 for u in paired))


    def test_28_malformed_protocol_structures(self):
        for value in (None, [], 7, 'not an object'):
            p=deepcopy(self.p);p['design']=value
            self.reject('SCHEMA_TYPE',lambda:validate_document(p))
        p=deepcopy(self.p);p['design']['base_schedule']=[None]
        self.reject('SCHEMA_TYPE',lambda:validate_document(p))
        with self.copied_repo() as root:
            path=root/'docs/task15_tail_attribution_amendment_v1.2.0.json';path.write_bytes(b'[]')
            self.reject('AMENDMENT_HASH',lambda:load_protocol(root))

        with self.copied_repo() as root:
            (root/'docs/task15_tail_attribution_preregistration_v1.2.0.md').unlink()
            self.reject('FROZEN_FILE_HASH',lambda:load_protocol(root))

    def test_29_missing_or_changed_source_lane_blocks(self):
        for lane in ('entries','condition_blocks'):
            p,r=self.altered();r[lane].append(deepcopy(r[lane][0]));self.rehash(p)
            code='ORDER_ENTRY_MEMBERSHIP' if lane=='entries' else 'ORDER_UNIT_MEMBERSHIP'
            self.reject(code,lambda:validate_document(p))
        p,r=self.altered();r['condition_blocks'][0]['cohort']='C';self.rehash(p)
        self.reject('ORDER_WORKLOAD',lambda:validate_document(p))
        p,r=self.altered();r['condition_blocks'][0]['source_lane_index']=999;self.rehash(p)
        self.reject('ORDER_PROVENANCE',lambda:validate_document(p))
