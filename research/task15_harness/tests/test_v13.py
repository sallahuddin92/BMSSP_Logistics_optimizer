"""Environment amendment controls; no runtime/NumPy import or workload execution."""
from collections import Counter
from copy import deepcopy
from contextlib import contextmanager, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from task15_harness.__main__ import main
from task15_harness.errors import ControlError
from task15_harness.integrity import canonical, digest, read_json
from task15_harness.protocol import (PACKAGE_ROOT, FROZEN_FILES, Protocol, load_protocol,
    validate_document, canonical_protocol_hash, parent_projection, PARENT_HASH)
from task15_harness.manifest import prepare_manifest, validate_manifest, seal
from task15_harness.analysis_environment import inspect_environment
from task15_harness.planning import compile_plan, plan_counts, query_records

REPO=PACKAGE_ROOT.parents[1]
NEGATIVE_RESULTS=[]


class V13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        NEGATIVE_RESULTS.clear()
        cls.protocol=load_protocol(REPO);cls.p=cls.protocol.data()

    def reject(self,code,action):
        with self.assertRaises(ControlError) as exc:action()
        self.assertEqual(exc.exception.code,code)
        NEGATIVE_RESULTS.append({'case':self.id(),'expected':code,'observed':exc.exception.code,'scope':'STATIC_OR_SYNTHETIC'})

    def altered(self):
        p=deepcopy(self.p);return p,p['analysis_environment_amendment']

    def rehash(self,p):
        p['identity']['sha256']=canonical_protocol_hash(p)

    @contextmanager
    def copied(self):
        with tempfile.TemporaryDirectory(prefix='task15-v13-') as tmp:
            root=Path(tmp)
            for name in FROZEN_FILES:
                dst=root/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPO/name,dst)
            yield root

    def test_01_wrong_numpy(self):
        p,a=self.altered();a['numpy']['version']='2.4.3';self.rehash(p)
        self.reject('ANALYSIS_NUMPY_VERSION',lambda:validate_document(p))

    def test_02_wrong_python(self):
        p,a=self.altered();a['python']['version']='3.11.14';self.rehash(p)
        self.reject('ANALYSIS_PYTHON_VERSION',lambda:validate_document(p))

    def test_03_changed_interpreter_hash(self):
        p,a=self.altered();a['python']['executable_sha256']='0'*64;self.rehash(p)
        self.reject('ANALYSIS_INTERPRETER_HASH',lambda:validate_document(p))

    def test_04_corrupted_package_identity(self):
        p,a=self.altered();a['numpy']['installed_file_identity_sha256']='0'*64;self.rehash(p)
        self.reject('ANALYSIS_PACKAGE_IDENTITY',lambda:validate_document(p))

    def test_05_stale_parent(self):
        p,a=self.altered();a['parent_canonical_sha256']='0'*64;self.rehash(p)
        self.reject('AMENDMENT_IDENTITY',lambda:validate_document(p))

    def test_06_altered_ledger(self):
        with self.copied() as root:
            file=root/'docs/task15_tail_attribution_amendment_v1.3.0.json';ledger=read_json(file)
            ledger['new_task15_observations_used']=True;ledger.pop('identity_sha256');ledger['identity_sha256']=digest(ledger);file.write_bytes(canonical(ledger))
            self.reject('AMENDMENT_HASH',lambda:load_protocol(root))

    def test_07_unapproved_replacement(self):
        p,a=self.altered();a['replacement']['environment_path']='/unapproved/venv';self.rehash(p)
        self.reject('ANALYSIS_ENVIRONMENT_REPLACEMENT',lambda:validate_document(p))

    def test_08_forged_approval_signatures(self):
        p,a=self.altered();a['scientific_acceptance']['approval_signatures']=['forged'];self.rehash(p)
        self.reject('SCIENTIFIC_APPROVAL',lambda:validate_document(p))

    def test_09_old_manifest_historical(self):
        m=prepare_manifest(self.protocol,checked=False);m['schema_version']='2';m['protocol']['version']='1.2.0';m['protocol']['canonical_sha256']=PARENT_HASH
        self.reject('HISTORICAL_MANIFEST',lambda:validate_manifest(self.protocol,seal(m)))
        m['schema_version']='3'
        self.reject('MANIFEST_PROTOCOL',lambda:validate_manifest(self.protocol,seal(m)))

    def test_10_query_namespace(self):
        p,a=self.altered();p['design']['resolved_diagnostic_order']['query_identity_policy']['namespace_protocol_sha256']=self.protocol.identity;self.rehash(p)
        self.reject('QUERY_NAMESPACE',lambda:validate_document(p))

    def test_11_schedule_or_source(self):
        p,a=self.altered();row=p['design']['base_schedule'][0];region=row['regions'][0];positions=row['positions_by_region'][region];positions[0]=positions[1];self.rehash(p)
        self.reject('POSITION_DUPLICATE',lambda:validate_document(p))
        p,a=self.altered();p['inputs']['seremban-small']['source_positions'][0]=p['inputs']['seremban-small']['source_positions'][1];self.rehash(p)
        self.reject('SOURCE_IDENTITY',lambda:validate_document(p))

    def test_12_statistical_seeds(self):
        p,a=self.altered();p['statistics']['bootstrap_execution_spec']['primary_initialization']+=' changed seed';self.rehash(p)
        self.reject('PROTOCOL_HASH',lambda:validate_document(p))

    def test_13_confidence_rules(self):
        p,a=self.altered();p['statistics']['bootstrap_execution_spec']['endpoint_fractions']['primary99_5'][0][0]=2;self.rehash(p)
        self.reject('PROTOCOL_HASH',lambda:validate_document(p))

    def test_14_incorrect_provenance(self):
        m=prepare_manifest(self.protocol,checked=False);m['protocol']['canonical_sha256']=PARENT_HASH
        self.reject('MANIFEST_PROTOCOL',lambda:validate_manifest(self.protocol,seal(m)))

    def test_15_missing_historical_version(self):
        with self.copied() as root:
            (root/'docs/task15_tail_attribution_protocol_v1.1.0.json').unlink()
            self.reject('HISTORICAL_FILE_MISSING',lambda:load_protocol(root))

    def test_16_execution_commands(self):
        for command in ['calibrate','collect','run-benchmark','profile','promote','trace','analyze']:
            with redirect_stdout(io.StringIO()) as stream:code=main([command])
            self.assertEqual(code,2);result=json.loads(stream.getvalue());self.assertEqual(result['error'],'UNSUPPORTED_OPERATION')
            NEGATIVE_RESULTS.append({'case':self.id(),'command':command,'expected':'UNSUPPORTED_OPERATION','observed':result['error']})

    def test_17_all_science_retained(self):
        self.assertEqual(parent_projection(self.p),read_json(REPO/'docs/task15_tail_attribution_protocol_v1.2.0.json'))
        self.assertEqual(self.p['analysis_environment_amendment']['scientific_acceptance']['approval_signatures'],[])
        self.assertFalse(self.p['execution_authorized']);self.assertFalse(self.p['promotion_authorized'])
        plan=compile_plan(self.protocol);counts=plan_counts(self.protocol,plan)
        self.assertEqual(counts['unit_count'],228);self.assertEqual(counts['query_record_count'],138696)
        self.assertEqual(Counter(u['session_kind'] for u in plan['units']),{'PRIMARY':128,'DIAGNOSTIC':100})
        self.assertEqual(sum(u['cohort']=='A' for u in plan['units']),64)
        self.assertEqual(counts['by_cohort_phase']['A/target']+counts['by_cohort_phase']['A/warmup'],41472)

    def test_18_manifest_pending_acceptance(self):
        m=prepare_manifest(self.protocol,checked=False);a=m['analysis_environment']
        self.assertEqual(a['technical_status'],'TECHNICALLY_VERIFIED');self.assertEqual(a['scientific_acceptance'],'SCIENTIFIC_ACCEPTANCE_PENDING');self.assertFalse(a['confirmatory_analysis_authorized']);self.assertEqual(a['live_identity_status'],'NOT_CHECKED')
        a['scientific_acceptance']='APPROVED'
        self.reject('ANALYSIS_ENVIRONMENT_CHANGED',lambda:validate_manifest(self.protocol,seal(m)))

    def test_19_corrupted_live_environment_rejected(self):
        from task15_harness.integrity import hash_file
        target=Path(self.p['analysis_environment_amendment']['python']['executable'])
        def corrupt(path):
            value=hash_file(path)
            return ('0'*64,value[1]) if Path(path)==target else value
        with patch('task15_harness.analysis_environment.hash_file',side_effect=corrupt):
            report=inspect_environment(self.protocol)
        self.assertEqual(report['live_identity_status'],'FAILED')
        self.assertTrue(any(r['status']=='MISMATCH' and r['path']==str(target) for r in report['live_identity_records']))

    def test_20_no_silent_environment_identity_change(self):
        p,a=self.altered();a['provenance_limitations']['independent_publisher_authenticity_established']=True;self.rehash(p)
        self.reject('ANALYSIS_ENVIRONMENT_IDENTITY',lambda:validate_document(p))

    def test_21_old_active_document_rejected(self):
        self.reject('PROTOCOL_VERSION',lambda:validate_document(read_json(REPO/'docs/task15_tail_attribution_protocol_v1.2.0.json')))

    def test_22_environment_output_protection(self):
        from task15_harness.output import create_bundle
        a=self.p['analysis_environment_amendment']
        for path in [Path(a['replacement']['environment_path'])/'new-output',
                     Path(a['numpy']['offline_source'])/'new-output',
                     Path(a['replacement']['environment_path']).parent/'new-output']:
            self.reject('OUTPUT_PROTECTED',lambda:create_bundle(self.protocol,path,{'x':b'x'}))
