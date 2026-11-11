"""Deterministic synthetic result ownership; no timing or graph-solving operations."""
import os
import weakref
from .errors import require
from .wire import validate,digest
from .frozen import PROTOCOL,expected_variant_records


def payload(query,variant):
    return {'synthetic':True,'measurement_eligible':False,'kind':'SYNTHETIC_RESULT_ONLY',
        'query_id':query['query_id'],'phase':query['phase'],'region':query['region'],
        'original_position':query['original_position'],'source_id':query['source_id'],
        'source_occurrence':query['source_occurrence'],'variant':variant}


class SyntheticResult:
    def __init__(self,query,variant):
        self.value=payload(query,variant)


class Machine:
    def __init__(self,p,units):
        self.p=p;self.units={u['id']:u for u in units if u['cohort']=='A'}
        self.binding=None;self.sequence=0;self.requests=set();self.graphs={};self.result=None
        self.result_copy=None;self.last_result=None;self.active=None;self.fingerprinted=False
        self.cursor=0;self.completed=0;self.expected=[];self.conceptual_active=False;self.complete=False
        self.fault='none';self.fault_at=0

    def data(self,states=(),fingerprint=''):
        return {'pid':os.getpid(),'backend':'SYNTHETIC_ONLY','states':list(states),
            'retained':self.result is not None,'prior_result_cleared':self.last_result is None or self.last_result() is None,
            'synthetic_fingerprint':fingerprint,'completed_queries':self.completed,
            'prepared_regions':list(self.graphs),'worker_complete':self.complete,
            'conceptual_timing_active':self.conceptual_active}

    def handle(self,r):
        validate(r,'REQUEST')
        require(r['request_id'] not in self.requests,'IPC_DUPLICATE_REQUEST')
        require(r['request_sequence']==self.sequence+1,'IPC_OUT_OF_ORDER')
        expected_id=digest([r[k] for k in ['protocol_sha256','unit_id','variant','op','query_id','region','request_sequence']])
        require(r['request_id']==expected_id,'IPC_REQUEST_ID')
        if self.binding is None:
            require(r['op']=='HELLO','WORKER_NOT_BOUND')
            require(r['protocol_sha256']==PROTOCOL,'IPC_PROTOCOL_IDENTITY')
            require(r['unit_id'] in self.units,'IPC_WRONG_UNIT')
            unit=self.units[r['unit_id']];require(unit['session_key']==r['session_key'],'IPC_WRONG_SESSION')
            self.binding={k:r[k] for k in ['protocol_sha256','unit_id','session_key','variant']}
            self.expected=expected_variant_records(self.p,unit,r['variant'])
            self.fault=r['data']['fault'];self.fault_at=r['data']['fault_at']
        else:
            for field in self.binding:require(r[field]==self.binding[field],'IPC_BINDING_IDENTITY',field)
            require(r['op']!='HELLO','WORKER_ALREADY_BOUND')
        self.requests.add(r['request_id']);self.sequence+=1
        op=r['op']
        if op in {'HELLO','PREPARE','SHUTDOWN'}:
            require(r['phase']=='control' and r['query_id']=='' and r['execution_index']==-1 and r['original_position']==-1 and r['source_id']=='' and r['source_occurrence']==0,'IPC_CONTROL_IDENTITY')
        if op=='HELLO':return self.data(['WORKER_STARTED'])
        if op=='PREPARE':
            regions=self.p['design']['regions'];index=len(self.graphs)
            require(self.cursor==0 and index<len(regions) and r['region']==regions[index],'WORKER_PREPARE_ORDER')
            self.graphs[r['region']]={'kind':'SYNTHETIC_STRUCTURAL_ONLY','prepared_once':True}
            return self.data(['PREPARED'])
        if op=='QUERY':
            require(len(self.graphs)==3,'WORKER_NOT_PREPARED')
            require(self.result is None and self.result_copy is None,'RESULT_STILL_RETAINED')
            require(self.last_result is None or self.last_result() is None,'PRIOR_RESULT_NOT_RELEASED')
            require(self.cursor<len(self.expected),'WORKER_QUERY_OVERFLOW')
            q=self.expected[self.cursor]
            for key,value in q.items():require(r[key]==value,'WORKER_QUERY_IDENTITY',key)
            self.active=q;self.cursor+=1;self.fingerprinted=False
            self.conceptual_active=True
            try:
                self.result=SyntheticResult(q,self.binding['variant'])
                self.result_copy=dict(self.result.value)
            finally:self.conceptual_active=False
            states=['READY','TARGET_ACTIVE','TARGET_RETURNED','RESULT_RETAINED'] if q['phase']=='target' else ['WARMUP_ACTIVE','WARMUP_RETURNED','RESULT_RETAINED']
            return self.data(states)
        if op in {'FINGERPRINT','RELEASE'}:
            require(self.result is not None and self.active is not None,'RESULT_NOT_RETAINED')
            for key,value in self.active.items():require(r[key]==value,'WORKER_RESULT_IDENTITY',key)
            require(not self.conceptual_active,'FINGERPRINT_INSIDE_TARGET')
            if op=='FINGERPRINT':
                require(not self.fingerprinted,'DUPLICATE_FINGERPRINT');self.fingerprinted=True
                return self.data(['POST_TARGET_FINGERPRINTED'],digest(self.result.value))
            require(self.fingerprinted,'RELEASE_BEFORE_FINGERPRINT')
            phase=self.active['phase'];self.last_result=weakref.ref(self.result)
            self.result=None;self.result_copy=None;self.active=None;self.completed+=1
            require(self.last_result() is None,'RESULT_RELEASE_FAILED')
            return self.data(['RESULT_RELEASED','WARMED' if phase=='warmup' else 'READY'])
        require(op=='SHUTDOWN','IPC_UNSUPPORTED_OPERATION')
        require(self.result is None and self.cursor==len(self.expected) and self.completed==len(self.expected),'WORKER_INCOMPLETE')
        self.complete=True;return self.data(['CLUSTER_COMPLETE'])
