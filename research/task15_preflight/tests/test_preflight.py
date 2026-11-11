"""Static/disposable evidence tests only. No native imports, queries or clock probes."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from preflight.core import PreflightError,canonical,read,sha,boundary
from preflight.evidence import inventory,reconcile,verify,INDEX_SHA,CAMPAIGN_SHA
from preflight.readiness import matrix,cohorts,evaluate_foundations
from preflight.outputs import envelope,validate_extension
from preflight.integration import verify_paths
from task15_cohort_a_runner.frozen import protocol
from task15_harness.manifest import prepare_manifest,validate_manifest,seal
from task15_harness.artifacts import source_lock
from task15_harness.analysis_environment import inspect_environment

ORIGINAL=Path('/Users/sallahuddin/Projects/BMSSP-task15-phase7-road-6dgxya2t')

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.protocol=protocol();cls.p=cls.protocol.data()
    def copy_campaign(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        target=Path(temp.name)/'campaign';shutil.copytree(ORIGINAL/'campaign',target)
        return target
    def rewrite(self,path,value):path.write_bytes(canonical(value)+b'\n')
    def mutate_campaign(self,name,change,expected=None):
        root=self.copy_campaign();file=root/name;value=read(file);change(value);self.rewrite(file,value)
        with self.assertRaises((PreflightError,ValueError,KeyError)) as caught:reconcile(root,self.p)
        if expected:self.assertIn(expected,str(caught.exception))
    def test_01_missing_completion(self):
        root=self.copy_campaign();(root/'COMPLETED.json').unlink()
        with self.assertRaises(PreflightError):inventory(root,'COMPLETED.json','files',closed=True)
    def test_02_payload_hash(self):
        root=self.copy_campaign();(root/'summary.json').write_bytes(b'{}')
        with self.assertRaisesRegex(PreflightError,'PAYLOAD_HASH'):inventory(root,'COMPLETED.json','files',closed=True)
    def test_03_tampered_binary(self):
        self.mutate_campaign('campaign.json',lambda v:v['binaries']['baseline'].update(sha256='f'*64),'BINARY_IDENTITY')
    def test_04_tampered_protocol(self):
        self.mutate_campaign('campaign.json',lambda v:v.update(protocol_sha256='f'*64),'PROTOCOL_IDENTITY')
    def test_05_missing_oracle(self):
        root=self.copy_campaign();(root/'seremban-small.oracle.json').unlink()
        with self.assertRaises((PreflightError,OSError)):reconcile(root,self.p)
    def test_06_duplicate_query(self):
        root=self.copy_campaign();file=root/'baseline.events.jsonl';lines=file.read_bytes().splitlines();lines.append(lines[-1]);file.write_bytes(b'\n'.join(lines)+b'\n')
        with self.assertRaisesRegex(PreflightError,'DUPLICATED'):reconcile(root,self.p)
    def test_07_wrong_query_count(self):
        self.mutate_campaign('summary.json',lambda v:v.update(native_attempts=5),'QUERY_COUNT')
    def test_08_incorrect_path(self):
        root=self.copy_campaign();file=root/'baseline.events.jsonl';lines=[json.loads(x) for x in file.read_text().splitlines()]
        proof=next(e['evidence'] for e in lines if e['event']=='QUERY_VERIFIED');proof['paths'][0]['valid']=False
        file.write_bytes(b'\n'.join(canonical(e) for e in lines)+b'\n')
        with self.assertRaisesRegex(PreflightError,'PATH_ACCEPTANCE'):reconcile(root,self.p)
    def test_09_missing_exit(self):
        root=self.copy_campaign();(root/'candidate.exit.json').unlink()
        with self.assertRaises(PreflightError):reconcile(root,self.p)
    def test_10_forged_approval(self):
        self.mutate_campaign('summary.json',lambda v:v.update(calibration_authorized=True),'FORGED_APPROVAL')
    def test_11_stale_harness_lock(self):
        m=prepare_manifest(self.protocol,checked=False);m['harness']['source_lock']['identity_sha256']='f'*64
        with self.assertRaisesRegex(Exception,'HARNESS_CHANGED'):validate_manifest(self.protocol,seal(m))
    def test_12_redirected_road(self):
        # Disposable fixture path, never alter the frozen original.
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'data';file.write_bytes(b'x');alias=Path(d)/'alias';alias.symlink_to(file)
            import preflight.integration as integration
            from unittest.mock import patch
            with patch.object(integration,'specifications',return_value=[('input/test/graph',alias,'f'*64)]):
                with self.assertRaisesRegex(PreflightError,'REDIRECTED'):verify_paths(self.protocol)
    def test_13_missing_environment(self):
        with self.assertRaisesRegex(PreflightError,'ENVIRONMENT'):
            evaluate_foundations({'all_verified':True},{'live_identity_status':'FAILED'},{'runtime_matches_task14':True},{'status':'STORAGE_CAPACITY_VERIFIED'})
    def test_14_insufficient_storage(self):
        status=evaluate_foundations({'all_verified':True},{'live_identity_status':'VERIFIED'},{'runtime_matches_task14':True},{'status':'INSUFFICIENT_CAPACITY'})
        self.assertEqual(status,'BLOCKED')
        rows=matrix(self.p,{'permissions':{'status':'PENDING'}},{'status':'INSUFFICIENT_CAPACITY','free_bytes':1,'required_bytes':512*2**30})
        self.assertEqual(next(r for r in rows if r['id']=='storage-capacity')['status'],'BLOCKED')
    def test_15_unsupported_permission(self):
        rows=matrix(self.p,{'permissions':{'status':'UNSUPPORTED'}},{'status':'STORAGE_CAPACITY_VERIFIED','free_bytes':10**15,'required_bytes':512*2**30})
        self.assertEqual(next(r for r in rows if r['id']=='profiler-permission')['status'],'UNSUPPORTED')
        self.assertNotEqual(cohorts(rows)['D']['calibration_readiness'],'VERIFIED')
    def test_16_missing_g8(self):
        rows=matrix(self.p,{'permissions':{'status':'PENDING'}},{'status':'STORAGE_CAPACITY_VERIFIED','free_bytes':10**15,'required_bytes':512*2**30})
        self.assertEqual(next(r for r in rows if r['id']=='G8_codegen')['status'],'BLOCKED')
        self.assertEqual(cohorts(rows)['A']['diagnostic_build_readiness'],'NOT_APPLICABLE')
    def test_17_fake_calibration(self):
        self.mutate_campaign('summary.json',lambda v:v.update(T0=1,T5=2),'CALIBRATION_DATA')
    def test_18_unauthorized_commands(self):
        import run
        for name in ['collect','calibrate','benchmark','profile','run-real','analyze-confirmatory','approve','promote','resume']:
            with redirect_stdout(io.StringIO()):self.assertEqual(run.main([name]),2)
    def test_19_native_import_forbidden(self):
        with self.assertRaisesRegex(PreflightError,'NATIVE_IMPORT'):__import__('bmssp_native')
        self.assertNotIn('bmssp_native',sys.modules)
    def test_20_native_execution_forbidden(self):
        # Audit hook rejects before subprocess creation. No original entry is launched.
        with self.assertRaisesRegex(PreflightError,'EXECUTION_FORBIDDEN'):
            subprocess.run([sys.executable,'-I','-B','research/task15_road_readiness/run.py','run-fixed','--output','/unused'],check=False)
    def test_21_authentic_receipts(self):
        r=verify(ORIGINAL,self.protocol);self.assertEqual((r['native_queries'],r['independent_road_oracles'],r['recorded_full_vector_comparisons'],r['paths_revalidated']),(6,3,80068,24))
    def test_22_resigned_inventory_still_requires_semantics(self):
        root=self.copy_campaign();value=read(root/'summary.json');value['native_attempts']=999;self.rewrite(root/'summary.json',value)
        marker=read(root/'COMPLETED.json');marker['files']['summary.json']=sha((root/'summary.json').read_bytes());self.rewrite(root/'COMPLETED.json',marker)
        inventory(root,'COMPLETED.json','files',closed=True)
        with self.assertRaisesRegex(PreflightError,'QUERY_COUNT'):reconcile(root,self.p)
    def test_23_extension_closed_schema(self):
        e=envelope('phase7-evidence-validation',{'validation':None});e['approval']=True
        with self.assertRaises(PreflightError):validate_extension(e)
        e=envelope('phase7-evidence-validation',{'validation':None});e['collection_authorized']=True
        with self.assertRaises(PreflightError):validate_extension(e)
    def test_24_no_clock_probe_or_runtime_import(self):
        import ast
        root=Path(__file__).resolve().parents[1]/'preflight'
        for file in root.glob('*.py'):
            tree=ast.parse(file.read_text())
            self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in {'perf_counter','perf_counter_ns','monotonic','monotonic_ns','solve','dijkstra'} for n in ast.walk(tree)),file)
        self.assertNotIn('bmssp_native',sys.modules)

    def test_25_fake_host_endpoint_in_extension(self):
        value=envelope('host-runtime-observations',{'observations':None,'storage':None})
        value['data']['observations']={'T0':100,'T5':200}
        with self.assertRaisesRegex(PreflightError,'CALIBRATION_DATA'):validate_extension(value)
    def test_26_missing_environment_live_inspection(self):
        from types import SimpleNamespace
        p=copy.deepcopy(self.p);p['analysis_environment_amendment']['python']['executable']='/nonexistent/phase8-fixture/python'
        observed=inspect_environment(SimpleNamespace(data=lambda:p))
        self.assertEqual(observed['live_identity_status'],'FAILED')
        with self.assertRaisesRegex(PreflightError,'ENVIRONMENT'):
            evaluate_foundations({'all_verified':True},observed,{'runtime_matches_task14':True},{'status':'STORAGE_CAPACITY_VERIFIED'})
    def test_27_marker_inventory_and_unknown_payload(self):
        root=self.copy_campaign();(root/'unlisted.json').write_bytes(b'{}')
        with self.assertRaisesRegex(PreflightError,'UNLISTED'):inventory(root,'COMPLETED.json','files',closed=True)
    def test_28_incorrect_path_geometry_with_pass_flag(self):
        root=self.copy_campaign();file=root/'baseline.events.jsonl';lines=[json.loads(x) for x in file.read_text().splitlines()]
        proof=next(e['evidence'] for e in lines if e['event']=='QUERY_VERIFIED')
        path=next(p for p in proof['paths'] if p['edges']);path['edges'][0]=2**64-1
        file.write_bytes(b'\n'.join(canonical(e) for e in lines)+b'\n')
        with self.assertRaisesRegex(ValueError,'ORIENTATION'):reconcile(root,self.p)

    def failure_bundle(self):
        from preflight.outputs import DATA_KEYS,write
        from preflight.integration import own_source
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)/'output'
        docs={k:{field:None for field in fields} for k,fields in DATA_KEYS.items()}
        docs['preflight-summary']={'technical_result':'TECHNICAL_STATIC_PREFLIGHT_BLOCKED','static_foundations_verified':False,'errors':[{'type':'SyntheticFixture','message':'deliberate failure'}],'phase8_source_identity':own_source()}
        docs['static-manifest-reference']={'manifest_file':None,'state':None,'reason':'SYNTHETIC_FAILURE_FIXTURE'}
        write(self.protocol,root,docs,None)
        return root
    def test_29_durable_blocked_bundle_no_approval(self):
        from preflight.outputs import validate_bundle
        root=self.failure_bundle();summary=validate_bundle(root)
        self.assertEqual(summary['technical_result'],'TECHNICAL_STATIC_PREFLIGHT_BLOCKED')
        self.assertFalse(read(root/'preflight-summary.json')['calibration_authorized'])
    def test_30_durable_payload_corruption(self):
        from preflight.outputs import validate_bundle
        root=self.failure_bundle();file=root/'preflight-summary.json';file.write_bytes(file.read_bytes()+b' ')
        with self.assertRaisesRegex(Exception,'BUNDLE_HASH'):validate_bundle(root)

if __name__=='__main__':unittest.main()
