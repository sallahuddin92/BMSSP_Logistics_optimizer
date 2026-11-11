"""Exclusive durable synthetic bundles with an exact inventory and a completion marker LAST."""
import hashlib
import json
import os
from pathlib import Path
from . import SYNTHETIC
from .errors import RunnerError,require
from .wire import canonical,strict_json
from .frozen import Workload,HARNESS,PROTOCOL,source_lock
from task15_harness.output import safe_destination
from task15_harness.artifacts import repository_identity


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while block:=f.read(1048576):h.update(block)
    return h.hexdigest()


def source_identity():
    root=Path(__file__).resolve().parents[1]
    files={str(p.relative_to(root)):file_sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p.suffix in {'.py','.md','.json'}}
    return {'files':files,'identity_sha256':hashlib.sha256(canonical(files)).hexdigest()}


def atomic_new(path,value):
    path=Path(path);temporary=path.with_name('.'+path.name+'.partial')
    with temporary.open('xb') as stream:
        stream.write(canonical(value)+b'\n');stream.flush();os.fsync(stream.fileno())
    try:os.link(temporary,path)
    except OSError as exc:raise RunnerError('OUTPUT_FINALIZE_FAILED',str(exc)) from exc
    temporary.unlink()
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


class Recorder:
    def __init__(self,output,workload,units):
        self.root=safe_destination(workload.protocol,Path(output))
        try:self.root.mkdir(exist_ok=False)
        except OSError as exc:raise RunnerError('OUTPUT_EXISTS_OR_UNAVAILABLE',str(exc)) from exc
        (self.root/'private-home').mkdir();(self.root/'private-tmp').mkdir()
        self.streams={name:(self.root/(name+'.jsonl')).open('xb') for name in ['queries','ipc','lifecycle','clusters','workers']}
        self.counts={name:0 for name in self.streams};self.closed=False;self.pending_queries=[]
        self.selected=units
        self.sources={'harness':source_lock(),'controller_worker':source_identity()}
        self.write_json('manifest.json',{'kind':'SYNTHETIC_COHORT_A_MANIFEST','state':'IN_PROGRESS_UNTIL_FINAL_RECEIPT','protocol_sha256':PROTOCOL,
            'sources':self.sources,'repository':repository_identity(workload.protocol),'static_plan_identity':workload.plan['identity_sha256'],
            'selected_unit_ids':[u['id'] for u in units],'all_A_unit_ids':[u['id'] for u in workload.units],
            'production_backend':'UNAVAILABLE','scientific_acceptance':'PENDING',
            'calibration_authorized':False,'collection_authorized':False,'confirmatory_analysis_authorized':False})
        self.write_json('plan.json',{'plan':workload.plan})
        self.write_json('session-slots.json',{'slots':workload.slots(units),'calendar_waits_executed':False,
            'scientific_eight_session_experiment_executed':False})

    def write_json(self,name,value):
        atomic_new(self.root/name,{**value,**SYNTHETIC})

    def emit(self,name,value):
        value={**value,**SYNTHETIC};self.streams[name].write(canonical(value)+b'\n');self.counts[name]+=1

    def ipc(self,req,reply,pid,event):
        self.emit('ipc',{'event':event,'pid':pid,'request':req,'response':reply})

    def worker_event(self,event,peer,**fields):
        self.emit('workers',{'event':event,'pid':peer.process.pid,'instance_id':peer.instance_id,**peer.binding,**fields})

    def lifecycle(self,unit,q,pid,op,reply):
        self.emit('lifecycle',{'unit_id':unit['id'],'query_id':q.get('query_id',''),
            'phase':q.get('phase','control'),'pid':pid,'op':op,**reply['data']})

    def query(self,q,pid,fingerprint,states,corrupt=False):
        if corrupt:
            self.pending_queries.append(None)
            raise RunnerError('OUTPUT_CORRUPTED','deliberate disposable synthetic fault')
        self.pending_queries.append({'query':q,'pid':pid,'synthetic_fingerprint':fingerprint,
            'fingerprint_kind':'SYNTHETIC_OBJECT_ONLY_NOT_BMSSP_CORRECTNESS',
            'states':states,'cluster_validity':'PENDING_FINAL_CLUSTER_VERDICT',
            'measurement_values':None,'measurement_availability':'not_collected:SYNTHETIC_ONLY'})

    def flush_queries(self):
        # Frozen per-region buffering; graceful failure flushes the partial region for diagnosis.
        for row in self.pending_queries:
            if row is None:
                self.streams['queries'].write(b'{corrupted synthetic output\n');self.counts['queries']+=1
            else:self.emit('queries',row)
        self.pending_queries.clear()

    def sync(self):
        for stream in self.streams.values():stream.flush();os.fsync(stream.fileno())

    def finish(self,receipt,success):
        self.flush_queries();self.sync()
        for f in self.streams.values():f.close()
        self.closed=True
        payload={str(p.relative_to(self.root)):file_sha(p) for p in sorted(self.root.rglob('*')) if p.is_file()}
        self.write_json('receipt.json',{**receipt,'event_counts':self.counts,'payload_files_sha256':payload,
            'scientific_experiment_completed':False,'production_backend':'UNAVAILABLE'})
        inventory={str(p.relative_to(self.root)):file_sha(p) for p in sorted(self.root.rglob('*')) if p.is_file()}
        self.write_json('COMPLETED.json' if success else 'FAILED.json',{'kind':'SYNTHETIC_COMPLETE' if success else 'SYNTHETIC_INCOMPLETE',
            'files_sha256':inventory,'receipt_sha256':inventory['receipt.json']})


def read_json_file(path):
    data=Path(path).read_bytes();require(data.endswith(b'\n'),'BUNDLE_NONCANONICAL_JSON')
    return strict_json(data[:-1])


def _validate_bundle(output,allow_failed=False):
    root=Path(output);marker=root/'COMPLETED.json'
    if not marker.is_file():
        require(allow_failed and (root/'FAILED.json').is_file(),'BUNDLE_COMPLETION_MISSING')
        marker=root/'FAILED.json'
    require(not any(p.is_symlink() for p in root.rglob('*')),'BUNDLE_SYMLINK')
    m=read_json_file(marker);require(m.get('synthetic') is True and m.get('measurement_eligible') is False,'BUNDLE_SYNTHETIC_BOUNDARY')
    inventory=m['files_sha256'];actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    require(actual==set(inventory)|{marker.name},'BUNDLE_FILE_INVENTORY')
    for name,expected in inventory.items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'BUNDLE_UNSAFE_PATH')
        require(file_sha(root/name)==expected,'BUNDLE_HASH_MISMATCH',name)
    receipt=read_json_file(root/'receipt.json');require(receipt['synthetic'] is True and receipt['measurement_eligible'] is False,'BUNDLE_SYNTHETIC_BOUNDARY')
    require(receipt['scientific_experiment_completed'] is False and receipt['production_backend']=='UNAVAILABLE','BUNDLE_SCIENTIFIC_CLAIM')
    require(all(receipt[k] is False for k in ['calibration_authorized','collection_authorized','confirmatory_analysis_authorized']),'BUNDLE_AUTHORIZATION')
    require(receipt['retry_count']==0 and receipt['replacement_count']==0,'BUNDLE_RETRY_REPLACEMENT')
    counts={};queries=[];query_rows=[]
    for name in ['queries','ipc','lifecycle','clusters','workers']:
        count=0
        with (root/(name+'.jsonl')).open('rb') as stream:
            for line in stream:
                if marker.name=='FAILED.json' and name=='queries':count+=1;continue
                require(line.endswith(b'\n'),'BUNDLE_TRUNCATED_LOG')
                row=strict_json(line[:-1]);require(row.get('synthetic') is True and row.get('measurement_eligible') is False,'BUNDLE_SYNTHETIC_BOUNDARY');count+=1
                if name=='queries':
                    require(row['measurement_values'] is None and row['fingerprint_kind']=='SYNTHETIC_OBJECT_ONLY_NOT_BMSSP_CORRECTNESS','BUNDLE_REAL_METRICS')
                    require(set(row)=={'query','pid','synthetic_fingerprint','fingerprint_kind','states','cluster_validity','measurement_values','measurement_availability','synthetic','measurement_eligible'},'BUNDLE_QUERY_SCHEMA')
                    queries.append(row['query']);query_rows.append(row)
        counts[name]=count
    if marker.name=='COMPLETED.json':
        require(counts==receipt['event_counts'],'BUNDLE_RECORD_COUNTS')
        require(receipt['status']=='SYNTHETIC_COMPLETE' and all(x['status']=='SYNTHETIC_COMPLETE' for x in receipt['clusters']),'BUNDLE_CLUSTER_INCOMPLETE')
        workload=Workload();units=[u for u in workload.units if u['id'] in receipt['selected_unit_ids']]
        require([u['id'] for u in units]==receipt['selected_unit_ids'] and [u['id'] for u in workload.units]==receipt['all_frozen_A_unit_ids'],'BUNDLE_UNIT_SELECTION')
        require(receipt['plan_identity']==workload.plan['identity_sha256'] and receipt['protocol_sha256']==PROTOCOL,'BUNDLE_PROTOCOL')
        require(receipt['completed_units']==receipt['planned_units']==receipt['attempted_units']==len(units) and receipt['invalid_units']==0 and receipt['not_executed_unit_ids']==[],'BUNDLE_UNIT_COUNTS')
        require(receipt['retained_query_records']==receipt['planned_query_records']==len(queries),'BUNDLE_QUERY_COUNTS')
        require([c['unit_id'] for c in receipt['clusters']]==receipt['selected_unit_ids'],'BUNDLE_CLUSTER_ORDER')
        reconciliation=workload.verify(units,queries)
        from .replay import replay
        replay_result=replay(root,workload,receipt,query_rows)
        for cluster in receipt['clusters']:
            require(cluster['completion_marker'] is not None and (root/cluster['completion_marker']).is_file(),'BUNDLE_CLUSTER_MARKER_MISSING')
            sealed=read_json_file(root/cluster['completion_marker']);expected={**cluster,'completion_marker':None}
            require(sealed==expected,'BUNDLE_CLUSTER_RECEIPT')
        require(read_json_file(root/'manifest.json')['sources']=={'harness':source_lock(),'controller_worker':source_identity()},'BUNDLE_SOURCE_IDENTITY')
        cluster_rows=[strict_json(line[:-1]) for line in (root/'clusters.jsonl').open('rb')]
        require(cluster_rows==receipt['clusters'],'BUNDLE_CLUSTER_VERDICTS')
        slots=read_json_file(root/'session-slots.json')['slots'];require(slots==workload.slots(units),'BUNDLE_SESSION_SLOTS')
        require(len({p['instance_id'] for c in receipt['clusters'] for p in c['workers']})==2*len(units),'BUNDLE_WORKER_REUSE')
        require(all(p['exit_code']==0 and p['verified_exit'] for c in receipt['clusters'] for p in c['workers']),'BUNDLE_WORKER_EXIT')
    else:reconciliation=None;replay_result=None
    require(m['receipt_sha256']==file_sha(root/'receipt.json'),'BUNDLE_RECEIPT_IDENTITY')
    for name,expected in receipt['payload_files_sha256'].items():require(inventory.get(name)==expected,'BUNDLE_RECEIPT_INVENTORY')
    return {**SYNTHETIC,'status':'VALID_SYNTHETIC_BUNDLE' if marker.name=='COMPLETED.json' else 'VALID_INCOMPLETE_SYNTHETIC_EVIDENCE',
        'counts':counts,'reconciliation':reconciliation,'ipc_replay':replay_result,'receipt_status':receipt['status']}


def validate_bundle(output,allow_failed=False):
    try:
        return _validate_bundle(output,allow_failed)
    except RunnerError:
        raise
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        raise RunnerError('BUNDLE_MALFORMED',type(exc).__name__+': '+str(exc)) from exc
