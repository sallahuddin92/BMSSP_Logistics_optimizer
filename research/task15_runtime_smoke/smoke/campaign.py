"""One bounded campaign, two owned children, no retries or configurable workloads."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from production_adapter import require
from . import MARKS
from .io import publish

REPO = Path(__file__).resolve().parents[3]
ENTRY = Path(__file__).resolve().parents[1]/'run.py'
PROTOCOL = 'b639d9960353f00c5a3d5efc58255206d5dd7d7f701311ebe7f715f5ad277ddd'
EXPECTED_HEAD = '5a05738b08a8c5ee46875d5dbed975f573d9da51'
PYTHON = Path('/Users/sallahuddin/Projects/BMSSP-task15-offline-reconstruction-jgt6c3vy/environment/bin/python')


def protocol():
    # Reuse the frozen loader only; it reads no road data or native extension.
    from task15_cohort_a_runner.frozen import protocol as load
    p = load()
    require(p.identity == PROTOCOL,'PROTOCOL_IDENTITY')
    return p.data()


def classify(returncode,receipt):
    if returncode < 0:return 'NATIVE_PROCESS_SIGNAL'
    if returncode != 0:return 'CHILD_FAILURE'
    require(receipt is not None and receipt.get('status') == 'PASS','MISSING_OR_FAILED_RECEIPT')
    require(receipt['query_attempts'] == receipt['query_successes'] == 2,'CHILD_QUERY_COUNT')
    return 'PASS'


def run(directory):
    directory = Path(directory).absolute()
    require(not directory.exists(),'EVIDENCE_DIRECTORY_EXISTS')
    require(REPO not in directory.parents and directory != REPO,'EXTERNAL_EVIDENCE_REQUIRED')
    require(directory.parent.is_dir(),'EVIDENCE_PARENT_REQUIRED')
    p = protocol()
    from .runtime import preflight
    # Parent verifies host/hash only; does not load either extension.
    identities = {v:preflight(p,v) for v in ('baseline','candidate')}
    directory.mkdir()
    publish(directory/'campaign.json',{'status':'STARTED','protocol_sha256':PROTOCOL,'maximum_solves':4,'variants':['baseline','candidate'],'sources':[0,3],
                                     'binaries':identities,'interpreter':sys.version,'python':str(PYTHON),'retries_permitted':False})
    outcomes = []
    for variant in ('baseline','candidate'):
        nonce = secrets.token_hex(32)
        # Durable launch claim prevents accidental reuse/retry within this campaign.
        publish(directory/(variant+'.launch.json'),{'variant':variant,'nonce':nonce,'status':'CLAIMED_ONCE'})
        env = {'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(directory),'TMPDIR':str(directory),
               'LANG':'C','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1','BMSSP_FIXED_SMOKE_NONCE':nonce}
        command = [str(PYTHON),'-I','-B',str(ENTRY),'_fixed-child',variant,str(directory)]
        exitcode = None
        failure = None
        pid = None
        try:
            with (directory/(variant+'.stdout')).open('xb') as stdout, (directory/(variant+'.stderr')).open('xb') as stderr:
                proc = subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,env=env,cwd=directory,start_new_session=True,close_fds=True)
                pid = proc.pid
                try:exitcode = proc.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    proc.kill();exitcode = proc.wait();failure = 'CHILD_TIMEOUT_NO_RETRY'
                stdout.flush();os.fsync(stdout.fileno());stderr.flush();os.fsync(stderr.fileno())
        except OSError as exc:
            failure = {'type':type(exc).__name__,'message':str(exc)}
        receipt_path = directory/(variant+'.receipt.json')
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
        try:status = classify(exitcode,receipt) if exitcode is not None and failure is None else 'FAIL'
        except (ValueError,KeyError) as exc:
            status = 'FAIL';failure = {'type':type(exc).__name__,'message':str(exc)}
        events_path = directory/(variant+'.events.jsonl')
        events = [json.loads(line) for line in events_path.read_text().splitlines()] if events_path.exists() else []
        attempts = [e for e in events if e.get('event') == 'SOLVE_ATTEMPT']
        successes = [e for e in events if e.get('event') == 'QUERY_VERIFIED']
        if receipt is not None and status == 'PASS':
            require(receipt['variant'] == variant and receipt['binary'] == identities[variant] and receipt['pid'] == pid,'RECEIPT_BINDING')
            require([e['source'] for e in attempts] == [0,3] and len(successes) == 2,'JOURNAL_QUERY_COUNT')
        outcome = {'variant':variant,'pid':pid,'exit_code':exitcode,'status':status,'failure':failure,'receipt':receipt,
                   'recorded_solve_attempts':len(attempts),'recorded_query_successes':len(successes),'process_reaped':exitcode is not None,'stdout_bytes':(directory/(variant+'.stdout')).stat().st_size if pid else None,
                   'stderr_bytes':(directory/(variant+'.stderr')).stat().st_size if pid else None}
        outcomes.append(outcome)
        publish(directory/(variant+'.exit.json'),outcome)
    dependencies_agree = (outcomes[0]['receipt']['dependencies'] == outcomes[1]['receipt']['dependencies']) if all(x['receipt'] and 'dependencies' in x['receipt'] for x in outcomes) else None
    success = all(x['status'] == 'PASS' for x in outcomes) and dependencies_agree is True
    summary = {'status':'PASS' if success else 'BLOCKED','protocol_sha256':PROTOCOL,'outcomes':outcomes,
               'total_query_attempts':sum(x['recorded_solve_attempts'] for x in outcomes),
               'maximum_query_attempts':4,'native_timing_values_retained':False,
               'performance_collection':False,'production_gate_changed':False,'road_graphs_opened':False,
               'dependency_pair_agreement':dependencies_agree,'no_retries':True}
    publish(directory/'summary.json',summary)
    files = {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(directory.iterdir()) if f.is_file()}
    publish(directory/'COMPLETED.json',{'status':summary['status'],'files':files})
    return 0 if success else 3


def fixed_child(variant,directory):
    require(variant in {'baseline','candidate'},'VARIANT')
    directory = Path(directory).absolute()
    claim = json.loads((directory/(variant+'.launch.json')).read_text())
    nonce = os.environ.pop('BMSSP_FIXED_SMOKE_NONCE',None)
    require(nonce is not None and claim['nonce'] == nonce and claim['variant'] == variant,'PRIVATE_CHILD_CLAIM')
    # One child invocation can claim this variant only once, even if launched again.
    publish(directory/(variant+'.child-claimed.json'),{'variant':variant,'pid':os.getpid()})
    p = protocol()
    # Explicit I/O guard: no frozen input may be opened by the actual smoke child.
    input_root = str(Path(p['inputs']['seremban-small']['native_export_path']).parents[1])
    def no_roads(event,args):
        if event == 'open' and isinstance(args[0],(str,bytes,os.PathLike)):
            path = str(Path(os.fsdecode(args[0])).absolute())
            require(not (path == input_root or path.startswith(input_root+'/')),'ROAD_INPUT_OPEN_FORBIDDEN')
    sys.addaudithook(no_roads)
    from .runtime import child
    return child(p,variant,directory)
