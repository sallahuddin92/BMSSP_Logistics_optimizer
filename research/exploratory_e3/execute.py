"""One serial frozen E3 schedule. Never retries a primary condition process."""
import json,pathlib,shutil,os,time
from availability import ROOT,REPO,CLT,XCTRACE,LABEL,command,put,sha,size
def append(name,data):
 with (ROOT/name).open('a') as f:f.write(json.dumps({'label':LABEL,**data})+'\n')
def run():
 assert (ROOT/'instrument-lock.json').exists()
 assert not (ROOT/'primary-start.json').exists(),'primary campaign cannot be restarted'
 plan=json.loads((ROOT/'fixed-execution-plan.json').read_text());identity=json.loads((ROOT/'build-identities.json').read_text())
 selection=json.loads((ROOT/'source-selection.json').read_text())['graphs']
 put('primary-start.json',{'fixed_plan_sha256':sha(ROOT/'fixed-execution-plan.json'),'instrument_lock_sha256':sha(ROOT/'instrument-lock.json'),'wall_time':time.time(),'expected_sessions':48})
 for number,job in enumerate(plan['jobs']):
  sid=job['session_id'];on=job['mode']=='on';variant='B' if job['condition']=='B' else 'A';exe=identity['variants'][variant]['executables']['e3_on' if on else 'e3_off']
  assert sha(exe['path'])==exe['sha256']
  free=shutil.disk_usage(ROOT).free;used=sum(size(t) for t in ROOT.glob('*.trace'))
  assert free>=3*1024**3 and used<4*1024**3,('capacity gate',free,used)
  graph=selection[job['graph']];assert sha(graph['native_export_path'])==graph['native_export_sha256']
  argv=[exe['path'],'paired',graph['native_export_path'],str(ROOT/(job['graph']+'.sources')),job['condition'],job['graph'],str(job['block']),'5','1','unused']
  append('primary-dispatch.jsonl',{'number':number,**job,'free_bytes':free,'trace_bytes_before':used,'executable_sha256':exe['sha256'],'argv':argv})
  if on:
   trace=ROOT/(sid+'.trace');raw=ROOT/(sid+'.queries.jsonl')
   result,_,_=command(sid,[XCTRACE,'record','--template','System Trace','--time-limit','10s','--window','10s','--no-prompt','--output',str(trace),'--target-stdout',str(raw),'--launch','--',*argv],timeout=60,trace=trace)
  else:
   raw=ROOT/(sid+'.stdout');result,_,_=command(sid,argv,developer=CLT,timeout=30)
  rows=[json.loads(s) for s in raw.read_text().splitlines() if s.strip()];samples=[r for r in rows if r['kind']=='sample'];footers=[r for r in rows if r['kind']=='footer']
  assert len(samples)==20 and len(footers)==1 and footers[0]['exit_state']=='SUCCESS'
  assert {(s['position'],s['repeat']) for s in samples}=={(p,r) for p in job['sources'] for r in range(5)}
  assert len({s['query_id'] for s in samples})==20
  assert all(not any(s['clock_rc']) and s['trace_on']==on for s in samples)
  used=sum(size(t) for t in ROOT.glob('*.trace'));assert used<=4*1024**3
  append('primary-completion.jsonl',{'number':number,**job,'raw_path':str(raw),'raw_sha256':sha(raw),'samples':20,'footer':footers[0],'record_command':result,'trace_bytes_total':used})
 put('primary-complete.json',{'sessions':48,'observations':960,'trace_on':480,'trace_off':480,'replacements':0})
if __name__=='__main__':run()
