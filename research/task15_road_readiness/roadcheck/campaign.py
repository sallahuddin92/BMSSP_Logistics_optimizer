"""One serial engineering campaign: three independent oracles and at most six solves."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from production_adapter import require
from smoke.campaign import protocol,PYTHON
from smoke.runtime import preflight
from .inputs import REGIONS,load
from .oracle import dijkstra,vector_identity
from .io import sha,publish

REPO=Path(__file__).resolve().parents[3]
ENTRY=Path(__file__).resolve().parents[1]/'run.py'


def compare_variants(root):
    records={}
    for variant in ('baseline','candidate'):
        events=[json.loads(line) for line in (root/(variant+'.events.jsonl')).read_text().splitlines()]
        records[variant]={e['evidence']['selection']['region']:e['evidence'] for e in events if e['event']=='QUERY_VERIFIED'}
    for region in REGIONS:
        a,b=records['baseline'][region],records['candidate'][region]
        require(a['native_sha256']==b['native_sha256']==a['oracle_sha256']==b['oracle_sha256'],'CROSS_VARIANT_DISTANCE_MISMATCH')
        require(a['diagnostics_without_timing']==b['diagnostics_without_timing'],'CROSS_VARIANT_WORK_MISMATCH')
    return {r:{'distance_sha256':records['baseline'][r]['native_sha256'],'exact_distance_agreement':True,
               'work_agreement':True,'identical_path_sequence_required':False} for r in REGIONS}


def run(directory):
    root=Path(directory).absolute()
    require(not root.exists() and root.parent.is_dir(),'FRESH_EVIDENCE_REQUIRED')
    require(root!=REPO and REPO not in root.parents,'EXTERNAL_EVIDENCE_REQUIRED')
    p=protocol();identities={v:preflight(p,v) for v in ('baseline','candidate')}
    root.mkdir()
    publish(root/'STARTED.json',{'maximum_bmssp_solves':6,'maximum_road_oracle_queries':3,'protocol_sha256':p['identity']['sha256'],'binaries':identities})
    oracle_files={};outcomes=[];oracle_attempts=0;status='BLOCKED';error=None;agreement=None
    try:
        for region in REGIONS:
            graph,chosen=load(p,region)
            publish(root/(region+'.oracle-attempt.json'),{'selection':chosen,'oracle_attempt':oracle_attempts+1})
            oracle_attempts+=1
            distances=dijkstra(graph,chosen['source_id'])  # Exactly one independent road SSSP.
            vector,fingerprint=vector_identity(distances)
            inp=p['inputs'][region]
            publish(root/(region+'.oracle.json'),{'selection':chosen,'vertices':list(graph.vertices),'distance_sha256':fingerprint,'distances_le_hex':vector,
                    'vertex_count':len(graph.vertices),'edge_count':len(graph.edges),
                    'frozen_artifact_hashes':{k:inp[k] for k in ('graph_sha256','native_export_sha256','fixture_manifest_sha256','query_file_sha256')}})
            oracle_files[region]=sha((root/(region+'.oracle.json')).read_bytes())
            graph=distances=vector=None
        publish(root/'campaign.json',{'protocol_sha256':p['identity']['sha256'],'oracle_files':oracle_files,'binaries':identities,'native_order':['baseline','candidate'],'region_order':list(REGIONS),'source_policy':'ORIGINAL_POSITION_ZERO_ONLY'})
        for variant in ('baseline','candidate'):
            nonce=secrets.token_hex(32)
            publish(root/(variant+'.launch.json'),{'variant':variant,'nonce':nonce,'launch_claimed_once':True})
            env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(root),'TMPDIR':str(root),'LC_ALL':'C','LANG':'C','PYTHONDONTWRITEBYTECODE':'1','BMSSP_ROAD_NONCE':nonce}
            with (root/(variant+'.stdout')).open('xb') as stdout,(root/(variant+'.stderr')).open('xb') as stderr:
                proc=subprocess.Popen([str(PYTHON),'-I','-B',str(ENTRY),'_fixed-child',variant,str(root)],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,
                                      cwd=root,env=env,close_fds=True,start_new_session=True)
                timeout=False
                try:code=proc.wait(timeout=180)
                except subprocess.TimeoutExpired:proc.kill();code=proc.wait();timeout=True
                stdout.flush();os.fsync(stdout.fileno());stderr.flush();os.fsync(stderr.fileno())
            receipt_file=root/(variant+'.receipt.json')
            receipt=json.loads(receipt_file.read_bytes()) if receipt_file.exists() else None
            events_file=root/(variant+'.events.jsonl')
            events=[json.loads(line) for line in events_file.read_text().splitlines()] if events_file.exists() else []
            attempts=sum(e['event']=='SOLVE_ATTEMPT' for e in events)
            outcome={'variant':variant,'pid':proc.pid,'exit_code':code,'process_reaped':True,'timeout':timeout,'recorded_attempts':attempts,'receipt':receipt}
            outcomes.append(outcome);publish(root/(variant+'.exit.json'),outcome)
            require(code==0 and not timeout and receipt is not None and receipt['status']=='PASS','NATIVE_CHILD_FAILED_STOP_NO_RETRY')
            require(receipt['variant']==variant and receipt['pid']==proc.pid and receipt['binary_preimport_identity']==identities[variant],'CHILD_IDENTITY')
            require(attempts==receipt['query_attempts']==3,'NATIVE_QUERY_COUNT')
        require(outcomes[0]['receipt']['dependencies']==outcomes[1]['receipt']['dependencies'],'DEPENDENCY_PAIR_MISMATCH')
        agreement=compare_variants(root)
        status='PASS'
    except BaseException as exc:
        import traceback
        error={'type':type(exc).__name__,'message':str(exc),'traceback':''.join(traceback.format_exception(exc))}
    summary={'status':status,'oracle_attempts':oracle_attempts,'native_attempts':sum(o['recorded_attempts'] for o in outcomes),'outcomes':outcomes,'agreement':agreement,
             'error':error,'retries':0,'performance_collection':False,'production_gate_changed':False}
    publish(root/'summary.json',summary)
    files={f.name:sha(f.read_bytes()) for f in sorted(root.iterdir()) if f.is_file()}
    publish(root/'COMPLETED.json',{'status':status,'files':files})
    return 0 if status=='PASS' else 3


def fixed_child(variant,directory):
    require(variant in {'baseline','candidate'},'VARIANT')
    root=Path(directory).absolute()
    claim=json.loads((root/(variant+'.launch.json')).read_bytes())
    nonce=os.environ.pop('BMSSP_ROAD_NONCE',None)
    require(nonce is not None and nonce==claim['nonce'] and claim['variant']==variant,'PRIVATE_CHILD_CLAIM')
    publish(root/(variant+'.child-claimed.json'),{'variant':variant,'pid':os.getpid()})
    from .runtime import child
    return child(protocol(),variant,root)
