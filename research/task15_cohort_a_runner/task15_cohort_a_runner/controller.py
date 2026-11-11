"""Functioning synthetic orchestration only; no production import/dispatch capability."""
from collections import Counter
from pathlib import Path
import sys
from . import SYNTHETIC
from .errors import RunnerError,Interrupted,require
from .wire import FAULTS,digest
from .frozen import Workload,PROTOCOL,variants
from .transport import Peer
from .bundle import Recorder,validate_bundle,atomic_new
from .lifecycle import payload

CONTROLLER_FAULTS={'interrupted_session','corrupted_output','missing_completion_marker'}


def production_backend():
    raise RunnerError('PRODUCTION_BACKEND_UNAVAILABLE','no import, loader or execution adapter exists')


class Controller:
    def __init__(self,output,unit_ids=None,fault='none',timeout=2.0):
        require(sys.version_info[:2]==(3,11),'PYTHON_VERSION','synthetic worker contract requires Python3.11')
        require(fault in FAULTS|CONTROLLER_FAULTS,'UNSUPPORTED_FAULT')
        require(type(timeout) in {int,float} and 0<timeout<=30,'IPC_TIMEOUT_CONFIG')
        self.workload=Workload();self.fault=fault;self.timeout=timeout;self.active_query=False
        if unit_ids is None:self.units=self.workload.units
        else:
            require(type(unit_ids) is list and unit_ids and len(unit_ids)==len(set(unit_ids)),'UNIT_SELECTION')
            self.units=[u for u in self.workload.units if u['id'] in unit_ids]
            require([u['id'] for u in self.units]==unit_ids,'UNIT_SELECTION','only frozen A units in original order')
        self.recorder=Recorder(output,self.workload,self.units)
        self.accepted_queries=[];self.last_failure=None

    def query(self,unit,q,peers,fault):
        require(not self.active_query,'SERIAL_QUERY_OVERLAP');self.active_query=True
        peer=peers[q['variant']];states=[]
        try:
            reply=peer.rpc('QUERY',query=q);data=reply['data'];states.extend(data['states'])
            require(data['retained'] and data['prior_result_cleared'],'RESULT_LIFETIME')
            expected_states=['READY','TARGET_ACTIVE','TARGET_RETURNED','RESULT_RETAINED'] if q['phase']=='target' else ['WARMUP_ACTIVE','WARMUP_RETURNED','RESULT_RETAINED']
            require(data['states']==expected_states,'RESULT_STATE_ORDER')
            require(data['synthetic_fingerprint']=='','FINGERPRINT_INSIDE_TARGET')
            self.recorder.lifecycle(unit,q,peer.process.pid,'QUERY',reply)
            fingerprint=peer.rpc('FINGERPRINT',query=q);states.extend(fingerprint['data']['states'])
            require(fingerprint['data']['retained'],'RESULT_RELEASED_EARLY')
            require(fingerprint['data']['states']==['POST_TARGET_FINGERPRINTED'],'RESULT_STATE_ORDER')
            require(fingerprint['data']['synthetic_fingerprint']==digest(payload(q,q['variant'])),'POST_TARGET_FINGERPRINT_FAILED')
            self.recorder.lifecycle(unit,q,peer.process.pid,'FINGERPRINT',fingerprint)
            released=peer.rpc('RELEASE',query=q);states.extend(released['data']['states'])
            require(released['data']['states']==['RESULT_RELEASED','WARMED' if q['phase']=='warmup' else 'READY'],'RESULT_STATE_ORDER')
            require(not released['data']['retained'] and released['data']['prior_result_cleared'],'RESULT_NOT_RELEASED')
            self.recorder.lifecycle(unit,q,peer.process.pid,'RELEASE',released)
            inject=fault=='corrupted_output' and q['phase']=='target'
            self.recorder.query(q,peer.process.pid,fingerprint['data']['synthetic_fingerprint'],states,corrupt=inject)
            self.accepted_queries.append(q)
            if fault=='interrupted_session' and q['phase']=='target':raise Interrupted('deterministic synthetic session fault')
        finally:self.active_query=False

    def p1_region(self,unit,region,peers,fault):
        row=self.workload.rows[unit['schedule_ref']]
        expected=[q for q in self.workload.queries[unit['id']] if q['region']==region]
        emitted=[]
        for variant in variants(row['P1_variant_order']):
            batch=[q for q in expected if q['variant']==variant]
            require([q['phase'] for q in batch]==['warmup']*8+['target']*100,'P1_WARMUP_BATCH')
            for q in batch:self.query(unit,q,peers,fault);emitted.append(q)
        require(emitted==expected,'P1_FROZEN_ORDER')

    def p2_region(self,unit,region,peers,fault):
        row=self.workload.rows[unit['schedule_ref']]
        expected=[q for q in self.workload.queries[unit['id']] if q['region']==region]
        lookup={(q['variant'],q['phase'],q['execution_index']):q for q in expected};require(len(lookup)==216,'P2_QUERY_MEMBERSHIP')
        emitted=[]
        for variant in variants(unit['startup_order']):
            for index in range(8):
                q=lookup[variant,'warmup',index];self.query(unit,q,peers,fault);emitted.append(q)
        for index in range(100):
            for variant in variants(row['P2_pair_orders_by_region'][region][index]):
                q=lookup[variant,'target',index];self.query(unit,q,peers,fault);emitted.append(q)
        require(emitted==expected,'P2_FROZEN_ORDER')

    def cluster(self,unit,fault):
        peers={};cleanup=[];error=None;before=len(self.accepted_queries)
        directory=self.recorder.root/'worker-logs'/digest(unit['id'])[:24]
        try:
            for variant in variants(unit['startup_order']):
                binding={'protocol_sha256':PROTOCOL,'session_key':unit['session_key'],'unit_id':unit['id'],'variant':variant}
                peer=Peer(binding,directory,self.recorder,self.timeout);peers[variant]=peer
                configured=fault if fault in FAULTS and variant==variants(unit['startup_order'])[0] else 'none'
                reply=peer.rpc('HELLO',data={'fault':configured,'fault_at':0})
                require(reply['data']['pid']==peer.process.pid and reply['data']['completed_queries']==0,'WORKER_START_IDENTITY')
            for variant in variants(unit['startup_order']):
                for region in self.workload.p['design']['regions']:
                    reply=peers[variant].rpc('PREPARE',data={'graph_kind':'SYNTHETIC_STRUCTURAL_ONLY'},region=region)
                    self.recorder.lifecycle(unit,{},peers[variant].process.pid,'PREPARE',reply)
            row=self.workload.rows[unit['schedule_ref']]
            for region in row['regions']:
                if unit['protocol']=='P1':self.p1_region(unit,region,peers,fault)
                else:self.p2_region(unit,region,peers,fault)
                self.recorder.flush_queries();self.recorder.sync()
            for variant in variants(unit['startup_order']):
                peers[variant].shutdown()
            require(len(self.accepted_queries)-before==648,'CLUSTER_QUERY_COUNT')
            if fault=='missing_completion_marker':raise RunnerError('MISSING_COMPLETION_MARKER','synthetic cluster seal deliberately withheld')
        except KeyboardInterrupt:error=Interrupted()
        except RunnerError as exc:error=exc
        except (OSError,ValueError) as exc:error=RunnerError('OUTPUT_OR_PROCESS_ERROR',str(exc))
        finally:
            for peer in peers.values():
                try:cleanup.append(peer.cleanup())
                except Exception as exc:
                    if error is None:error=RunnerError('WORKER_CLEANUP_FAILED',str(exc))
        try:self.recorder.flush_queries()
        except OSError as exc:
            if error is None:error=RunnerError('OUTPUT_WRITE_FAILED',str(exc))
        records=self.accepted_queries[before:];counts=Counter(q['phase'] for q in records)
        verdict={**SYNTHETIC,'unit_id':unit['id'],'session_key':unit['session_key'],
            'status':'INVALID' if error else 'SYNTHETIC_COMPLETE','error_code':error.code if error else '',
            'error_detail':error.detail if error else '',
            'invalidates':'WHOLE_PAIRED_CLUSTER_ALL_3_REGIONS_BOTH_VARIANTS_ALL_WARMUPS_AND_TARGETS' if error else '',
            'planned_records':648,'retained_structural_records':len(records),'phase_counts':dict(counts),
            'workers':cleanup,'retry_count':0,'replacement_count':0,'completion_marker':None}
        if error is None:
            require(len(cleanup)==2 and all(w['exit_code']==0 and w['verified_exit'] for w in cleanup),'WORKER_EXIT_NOT_VERIFIED')
            completion=directory/'CLUSTER_COMPLETE.json'
            try:
                atomic_new(completion,verdict);verdict['completion_marker']=str(completion.relative_to(self.recorder.root))
            except (OSError,RunnerError) as exc:
                error=RunnerError('CLUSTER_SEAL_FAILED',str(exc))
                verdict.update(status='INVALID',error_code=error.code,error_detail=error.detail,
                    invalidates='WHOLE_PAIRED_CLUSTER_ALL_3_REGIONS_BOTH_VARIANTS_ALL_WARMUPS_AND_TARGETS')
        self.recorder.emit('clusters',verdict);self.recorder.sync()
        self.last_failure=error
        return verdict

    def run(self):
        clusters=[];error=None
        try:
            for index,unit in enumerate(self.units):
                verdict=self.cluster(unit,self.fault if index==0 else 'none');clusters.append(verdict)
                if verdict['status']=='INVALID':error=self.last_failure;break
        except KeyboardInterrupt:error=Interrupted()
        except RunnerError as exc:error=exc
        except OSError as exc:error=RunnerError('OUTPUT_WRITE_FAILED',str(exc))
        successful=error is None and len(clusters)==len(self.units) and all(c['status']=='SYNTHETIC_COMPLETE' for c in clusters)
        if successful:
            try:self.workload.verify(self.units,self.accepted_queries)
            except RunnerError as exc:
                error=RunnerError('STRUCTURAL_RECONCILIATION_FAILED',str(exc));successful=False
        status='SYNTHETIC_COMPLETE' if successful else 'INTERRUPTED' if error and error.code=='SESSION_INTERRUPTED' else 'FAILED'
        receipt={**SYNTHETIC,'status':status,'protocol_sha256':PROTOCOL,'plan_identity':self.workload.plan['identity_sha256'],
            'scope':'FULL_COHORT_A_SYNTHETIC_LIFECYCLE' if len(self.units)==64 else 'SUBSET_SYNTHETIC_LIFECYCLE_TEST',
            'selected_unit_ids':[u['id'] for u in self.units],'all_frozen_A_unit_ids':[u['id'] for u in self.workload.units],
            'planned_units':len(self.units),'attempted_units':len(clusters),'completed_units':sum(c['status']=='SYNTHETIC_COMPLETE' for c in clusters),
            'invalid_units':sum(c['status']=='INVALID' for c in clusters),'planned_query_records':len(self.units)*648,
            'retained_query_records':len(self.accepted_queries),'not_executed_unit_ids':[u['id'] for u in self.units[len(clusters):]],
            'error_code':error.code if error else '', 'error_detail':error.detail if error else '',
            'clusters':clusters,'retry_count':0,'replacement_count':0,'calibration_authorized':False,
            'collection_authorized':False,'confirmatory_analysis_authorized':False,'fault_injection':self.fault,
            'timeout_use':'IPC_SUPERVISION_ONLY_NO_QUERY_TIMING_OR_PERFORMANCE_VALUES'}
        try:self.recorder.finish(receipt,successful)
        except OSError as exc:raise RunnerError('OUTPUT_DURABILITY_FAILED',str(exc)) from exc
        if successful:validate_bundle(self.recorder.root)
        return receipt
