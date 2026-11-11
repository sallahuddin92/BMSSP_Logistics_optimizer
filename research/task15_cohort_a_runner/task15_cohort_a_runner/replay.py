"""Independent bundle-level serial IPC/lifetime replay; no process launches or timing."""
import hashlib
from pathlib import Path
from . import SYNTHETIC
from .errors import require
from .wire import canonical,frame,validate,validate_reply,IDENTITY,digest,strict_json
from .lifecycle import Machine,payload
from .bundle import file_sha


def replay(root,workload,receipt,query_rows):
    workers={(c['unit_id'],w['variant']):w for c in receipt['clusters'] for w in c['workers']}
    machines={};stdout_hashes={};pending=None;requests=0;responses=0;queries=[];lifecycle_hash=hashlib.sha256()
    for line in (root/'ipc.jsonl').open('rb'):
        event=strict_json(line[:-1]);require(set(event)=={'synthetic','measurement_eligible','event','pid','request','response'},'BUNDLE_IPC_SCHEMA')
        if event['event']=='REQUEST':
            require(pending is None and event['response'] is None,'BUNDLE_CONCURRENT_REQUESTS')
            req=validate(event['request'],'REQUEST');key=(req['unit_id'],req['variant'])
            require(key in workers and workers[key]['pid']==event['pid'],'BUNDLE_WORKER_BINDING')
            if req['op']=='HELLO':
                require(key not in machines,'BUNDLE_WORKER_REUSE');machines[key]=Machine(workload.p,workload.units);stdout_hashes[key]=hashlib.sha256()
            require(key in machines,'BUNDLE_WORKER_NOT_STARTED')
            expected=machines[key].handle(req);expected['pid']=event['pid'];pending=(req,expected,key)
            if req['op']=='QUERY':queries.append({k:req[k] for k in IDENTITY})
            requests+=1
        else:
            require(event['event']=='RESPONSE' and pending is not None and event['request'] is None,'BUNDLE_EXTRA_RESPONSE')
            req,expected,key=pending;reply=validate_reply(req,event['response'])
            require(event['pid']==expected['pid'] and reply['data']==expected,'BUNDLE_LIFETIME_REPLAY')
            stdout_hashes[key].update(frame(reply))
            if req['op'] in {'PREPARE','QUERY','FINGERPRINT','RELEASE'}:
                life={**SYNTHETIC,'unit_id':req['unit_id'],'query_id':req['query_id'],'phase':req['phase'],
                      'pid':event['pid'],'op':req['op'],**expected}
                lifecycle_hash.update(canonical(life)+b'\n')
            pending=None;responses+=1
    require(pending is None and requests==responses,'BUNDLE_MISSING_RESPONSE')
    require(len(machines)==len(workers) and all(m.complete and m.completed==324 for m in machines.values()),'BUNDLE_WORKER_INCOMPLETE')
    require(len(queries)==len(query_rows),'BUNDLE_IPC_QUERY_COUNT')
    for actual,row in zip(queries,query_rows):
        q=row['query'];expected={k:q[k] for k in IDENTITY-{'unit_id'}};expected['unit_id']=q['trial_id']
        require(actual==expected,'BUNDLE_IPC_QUERY_ORDER')
        require(row['synthetic_fingerprint']==digest(payload(q,q['variant'])),'BUNDLE_SYNTHETIC_FINGERPRINT')
        expected_states=(['READY','TARGET_ACTIVE','TARGET_RETURNED','RESULT_RETAINED'] if q['phase']=='target' else ['WARMUP_ACTIVE','WARMUP_RETURNED','RESULT_RETAINED'])+['POST_TARGET_FINGERPRINTED','RESULT_RELEASED','WARMED' if q['phase']=='warmup' else 'READY']
        require(row['states']==expected_states and row['pid']==workers[(q['trial_id'],q['variant'])]['pid'],'BUNDLE_QUERY_LIFETIME')
    require(file_sha(root/'lifecycle.jsonl')==lifecycle_hash.hexdigest(),'BUNDLE_LIFECYCLE_REPLAY')
    for (unit,variant),h in stdout_hashes.items():
        path=root/'worker-logs'/digest(unit)[:24]/(variant+'.stdout.bin')
        require(file_sha(path)==h.hexdigest(),'BUNDLE_STDOUT_REPLAY')
    observed={}
    for line in (root/'workers.jsonl').open('rb'):
        event=strict_json(line[:-1]);key=(event['unit_id'],event['variant'])
        require(key in workers and event['pid']==workers[key]['pid'] and event['instance_id']==workers[key]['instance_id'],'BUNDLE_WORKER_EVENTS')
        observed.setdefault(key,[]).append(event['event'])
        if event['event']!='WORKER_CREATED':require(event['exit_code']==0,'BUNDLE_WORKER_EXIT')
        if event['event']=='WORKER_CLEANED':require(event['verified_exit'] is True,'BUNDLE_WORKER_EXIT')
    require(set(observed)==set(workers) and all(v==['WORKER_CREATED','WORKER_EXIT_VERIFIED','WORKER_CLEANED'] for v in observed.values()),'BUNDLE_WORKER_CLEANUP')
    return {'requests':requests,'responses':responses,'serial_queries':len(queries),'worker_instances':len(machines),'lifetime_replayed':True}
