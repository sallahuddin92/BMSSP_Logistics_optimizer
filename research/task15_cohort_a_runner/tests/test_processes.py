"""Real child-process and durable-evidence tests; workers are strictly synthetic."""
import copy
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager
from task15_cohort_a_runner.controller import Controller
from task15_cohort_a_runner.bundle import validate_bundle,read_json_file,file_sha
from task15_cohort_a_runner.errors import RunnerError
from task15_cohort_a_runner.frozen import Workload
from task15_cohort_a_runner.wire import canonical

OBSERVED=[]
EVIDENCE_ROOT=None


class ProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work=Workload();cls.p1=next(u for u in cls.work.units if u['protocol']=='P1');cls.p2=next(u for u in cls.work.units if u['protocol']=='P2')
        if EVIDENCE_ROOT is None:
            cls.temp=tempfile.TemporaryDirectory(prefix='task15-process-');cls.base=Path(cls.temp.name)
        else:
            cls.temp=None;cls.base=Path(EVIDENCE_ROOT)/'processes';cls.base.mkdir()
        cls.successes={}
        for name,unit in [('P1',cls.p1),('P2',cls.p2)]:
            path=cls.base/name;receipt=Controller(path,[unit['id']]).run();cls.successes[name]=(path,receipt)
            if receipt['status']!='SYNTHETIC_COMPLETE':raise RuntimeError(receipt)
    @classmethod
    def tearDownClass(cls):
        if cls.temp is not None:cls.temp.cleanup()

    def reject(self,code,func):
        with self.assertRaises(RunnerError) as caught:func()
        self.assertEqual(caught.exception.code,code)

    def test_01_real_p1_lifecycle_and_oracle(self):
        path,r=self.successes['P1'];v=validate_bundle(path)
        self.assertEqual(v['reconciliation']['records'],648);self.assertEqual(v['ipc_replay']['requests'],1954)
        self.assertEqual(v['ipc_replay']['responses'],1954);self.assertEqual(v['ipc_replay']['serial_queries'],648)
        self.assertEqual(r['clusters'][0]['phase_counts'],{'warmup':48,'target':600})
        self.assertTrue(all(w['exit_code']==0 and w['verified_exit'] for w in r['clusters'][0]['workers']))
        OBSERVED.append({'case':'P1','records':648,'status':'PASS','ipc_replay':v['ipc_replay']})

    def test_02_real_p2_interleaving_and_oracle(self):
        path,r=self.successes['P2'];v=validate_bundle(path)
        self.assertEqual(v['reconciliation']['records'],648)
        records=[json.loads(line)['query'] for line in (path/'queries.jsonl').read_text().splitlines()]
        self.assertEqual(records,self.work.queries[self.p2['id']])
        for region in self.work.rows[self.p2['schedule_ref']]['regions']:
            targets=[q for q in records if q['region']==region and q['phase']=='target']
            self.assertEqual(len(targets),200)
            for a,b in zip(targets[::2],targets[1::2]):self.assertEqual(a['original_position'],b['original_position']);self.assertNotEqual(a['variant'],b['variant'])
        OBSERVED.append({'case':'P2','records':648,'status':'PASS'})

    def test_03_fault_matrix_whole_cluster_no_retries(self):
        faults={'crash':'WORKER_CRASH','nonzero_exit':'WORKER_NONZERO_EXIT','timeout':'IPC_TIMEOUT',
            'wrong_response_identity':'IPC_WRONG_UNIT','missing_response':'IPC_MISSING_RESPONSE',
            'duplicate_response':'IPC_DUPLICATE_RESPONSE','wrong_variant':'IPC_WRONG_VARIANT',
            'wrong_position':'IPC_WRONG_POSITION','failed_fingerprint':'POST_TARGET_FINGERPRINT_FAILED',
            'interrupted_session':'SESSION_INTERRUPTED','corrupted_output':'OUTPUT_CORRUPTED',
            'missing_completion_marker':'MISSING_COMPLETION_MARKER','wrong_session':'IPC_WRONG_SESSION',
            'out_of_order':'IPC_OUT_OF_ORDER','malformed_frame':'IPC_MALFORMED_JSON',
            'oversized_frame':'IPC_FRAME_TOO_LARGE','truncated_message':'IPC_TRUNCATED_FRAME',
            'extra_response':'IPC_UNEXPECTED_EXTRA_RESPONSE','disconnect':'IPC_DISCONNECTED'}
        for name,expected in faults.items():
            with self.subTest(name=name):
                path=self.base/('fault-'+name);receipt=Controller(path,[self.p1['id']],name,timeout=.15).run()
                self.assertEqual(receipt['error_code'],expected)
                self.assertEqual(receipt['invalid_units'],1);self.assertEqual(receipt['completed_units'],0)
                c=receipt['clusters'][0];self.assertEqual(c['status'],'INVALID')
                self.assertEqual(c['invalidates'],'WHOLE_PAIRED_CLUSTER_ALL_3_REGIONS_BOTH_VARIANTS_ALL_WARMUPS_AND_TARGETS')
                self.assertEqual(c['planned_records'],648);self.assertEqual(c['retry_count'],0);self.assertEqual(c['replacement_count'],0)
                self.assertFalse((path/'COMPLETED.json').exists());self.assertTrue((path/'FAILED.json').is_file())
                for worker in c['workers']:
                    with self.assertRaises(ProcessLookupError):os.kill(worker['pid'],0)
                self.assertEqual(validate_bundle(path,allow_failed=True)['status'],'VALID_INCOMPLETE_SYNTHETIC_EVIDENCE')
                self.reject('BUNDLE_COMPLETION_MISSING',lambda:validate_bundle(path))
                OBSERVED.append({'case':name,'expected':expected,'observed':receipt['error_code'],'partial_records':receipt['retained_query_records'],'invalidates':c['invalidates'],'status':'PASS'})

    def test_04_no_overwrite_or_resume(self):
        path,r=self.successes['P1'];before=file_sha(path/'COMPLETED.json')
        self.reject('OUTPUT_EXISTS_OR_UNAVAILABLE',lambda:Controller(path,[self.p1['id']]))
        self.assertEqual(file_sha(path/'COMPLETED.json'),before)

    @contextmanager
    def copied(self,name):
        with tempfile.TemporaryDirectory(prefix='bundle-'+name+'-',dir=self.base) as tmp:
            path=Path(tmp)/'copy';shutil.copytree(self.successes['P1'][0],path);yield path

    def reseal(self,path,name):
        receipt=read_json_file(path/'receipt.json');receipt['payload_files_sha256'][name]=file_sha(path/name);(path/'receipt.json').write_bytes(canonical(receipt)+b'\n')
        marker=read_json_file(path/'COMPLETED.json');marker['files_sha256'][name]=file_sha(path/name);marker['files_sha256']['receipt.json']=file_sha(path/'receipt.json');marker['receipt_sha256']=file_sha(path/'receipt.json');(path/'COMPLETED.json').write_bytes(canonical(marker)+b'\n')

    def test_05_corrupted_bundle_hash(self):
        with self.copied('corrupt') as path:
            with (path/'queries.jsonl').open('ab') as f:f.write(b'bad\n')
            self.reject('BUNDLE_HASH_MISMATCH',lambda:validate_bundle(path))

    def test_06_missing_completion_marker(self):
        with self.copied('missing') as path:
            (path/'COMPLETED.json').unlink();self.reject('BUNDLE_COMPLETION_MISSING',lambda:validate_bundle(path))

    def test_07_unlisted_or_symlink_output(self):
        with self.copied('extra') as path:
            (path/'extra').write_text('extra');self.reject('BUNDLE_FILE_INVENTORY',lambda:validate_bundle(path))
        with self.copied('symlink') as path:
            (path/'extra').symlink_to(path/'queries.jsonl');self.reject('BUNDLE_SYMLINK',lambda:validate_bundle(path))

    def test_08_resealed_lifetime_corruption_rejected(self):
        with self.copied('lifetime') as path:
            rows=[json.loads(x) for x in (path/'lifecycle.jsonl').read_text().splitlines()];rows[-1]['states']=['RESULT_RETAINED'];(path/'lifecycle.jsonl').write_bytes(b''.join(canonical(x)+b'\n' for x in rows));self.reseal(path,'lifecycle.jsonl')
            self.reject('BUNDLE_LIFECYCLE_REPLAY',lambda:validate_bundle(path))

    def test_09_resealed_source_occurrence_rejected(self):
        with self.copied('source') as path:
            rows=[json.loads(x) for x in (path/'queries.jsonl').read_text().splitlines()];rows[0]['query']['source_occurrence']+=1;(path/'queries.jsonl').write_bytes(b''.join(canonical(x)+b'\n' for x in rows));self.reseal(path,'queries.jsonl')
            self.reject('QUERY_SCIENTIFIC_PAYLOAD',lambda:validate_bundle(path))

    def test_10_real_signal_interrupt_and_child_cleanup(self):
        path=self.base/'signal';run=Path(__file__).resolve().parents[1]/'run.py'
        with (self.base/'signal.stdout').open('wb') as out,(self.base/'signal.stderr').open('wb') as err:
            p=subprocess.Popen([sys.executable,'-I','-B',str(run),'synthetic-run','--unit',self.p1['id'],'--fault','timeout','--timeout','10','--output',str(path)],stdout=out,stderr=err)
            try:
                deadline=time.monotonic()+12;ready=False
                while p.poll() is None and time.monotonic()<deadline:
                    files=list(path.glob('worker-logs/*/*.stderr.jsonl'))
                    if any('FAULT_INJECTED' in f.read_text() for f in files):ready=True;break
                    time.sleep(.02)
                self.assertTrue(ready,'worker did not reach controlled synthetic fault')
                p.send_signal(signal.SIGINT);self.assertEqual(p.wait(timeout=5),130)
            finally:
                if p.poll() is None:p.kill();p.wait()
        r=read_json_file(path/'receipt.json');self.assertEqual(r['status'],'INTERRUPTED');self.assertEqual(r['error_code'],'SESSION_INTERRUPTED')
        self.assertEqual(r['invalid_units'],1)
        for w in r['clusters'][0]['workers']:
            with self.assertRaises(ProcessLookupError):os.kill(w['pid'],0)
        OBSERVED.append({'case':'actual_SIGINT','observed':'SESSION_INTERRUPTED','status':'PASS'})

    def test_11_actual_worker_rejects_bad_requests(self):
        import struct
        from task15_cohort_a_runner.wire import request,frame
        script=Path(__file__).resolve().parents[1]/'task15_cohort_a_runner/worker.py'
        binding={'protocol_sha256':self.work.protocol.identity,'session_key':self.p1['session_key'],'unit_id':self.p1['id'],'variant':'baseline'}
        hello=request(binding,'HELLO',1,data={'fault':'none','fault_at':0})
        missing=dict(hello);missing.pop('phase')
        badop={**hello,'op':'collect'}
        badtype={**hello,'op':[]}
        inputs=[('wrong_request_type',frame(badtype),'IPC_SCHEMA_TYPE'),('malformed_request',struct.pack('!I',2)+b'{!','IPC_MALFORMED_JSON'),
            ('oversized_request',struct.pack('!I',65537),'IPC_FRAME_TOO_LARGE'),
            ('missing_request_field',frame(missing),'IPC_SCHEMA_FIELDS'),
            ('duplicate_request',frame(hello)+frame(hello),'IPC_DUPLICATE_REQUEST'),
            ('wrong_request_sequence',frame(request(binding,'HELLO',2,data={'fault':'none','fault_at':0})),'IPC_OUT_OF_ORDER'),
            ('unsupported_worker_operation',frame(badop),'IPC_UNSUPPORTED_OPERATION')]
        for name,data,code in inputs:
            proc=subprocess.run([sys.executable,'-I','-B',str(script),'serve-synthetic'],input=data,capture_output=True,timeout=8)
            self.assertEqual(proc.returncode,2)
            errors=[json.loads(x) for x in proc.stderr.splitlines()]
            self.assertEqual(errors[-1]['code'],code);self.assertTrue(errors[-1]['synthetic']);self.assertFalse(errors[-1]['measurement_eligible'])
            (self.base/(name+'.stdout.bin')).write_bytes(proc.stdout);(self.base/(name+'.stderr.jsonl')).write_bytes(proc.stderr)
            OBSERVED.append({'case':name,'expected':code,'observed':errors[-1]['code'],'status':'PASS'})

    def test_12_resealed_authorization_rejected(self):
        with self.copied('authorization') as path:
            receipt=read_json_file(path/'receipt.json');receipt['collection_authorized']=True;(path/'receipt.json').write_bytes(canonical(receipt)+b'\n')
            marker=read_json_file(path/'COMPLETED.json');marker['files_sha256']['receipt.json']=file_sha(path/'receipt.json');marker['receipt_sha256']=file_sha(path/'receipt.json');(path/'COMPLETED.json').write_bytes(canonical(marker)+b'\n')
            self.reject('BUNDLE_AUTHORIZATION',lambda:validate_bundle(path))

    def test_13_illegal_selection_cannot_make_new_schedule(self):
        self.reject('UNIT_SELECTION',lambda:Controller(self.base/'bad-order',[self.work.units[1]['id'],self.work.units[0]['id']]))
        self.reject('UNIT_SELECTION',lambda:Controller(self.base/'bad-unit',['B/primary/S00-P1-T01']))

    def test_14_existing_output_cannot_be_deleted_or_resumed(self):
        path=self.base/'fault-crash';before=file_sha(path/'FAILED.json')
        self.reject('OUTPUT_EXISTS_OR_UNAVAILABLE',lambda:Controller(path,[self.p1['id']]))
        self.assertEqual(file_sha(path/'FAILED.json'),before)

    def test_15_malformed_completion_schema_rejected(self):
        with self.copied('bad-marker') as path:
            (path/'COMPLETED.json').write_bytes(canonical([])+b'\n')
            self.reject('BUNDLE_MALFORMED',lambda:validate_bundle(path))
