"""Bounded public-tool E3 initial feasibility gate; no sudo/private APIs."""
import json,os,pathlib,shutil,subprocess,time,hashlib,xml.etree.ElementTree as ET
ROOT=pathlib.Path((pathlib.Path(__file__).parent/'EVIDENCE_PATH.txt').read_text().strip())
REPO=pathlib.Path(__file__).resolve().parents[2]
LABEL='EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION'
XCODE='/Applications/Xcode.app/Contents/Developer'
CLT='/Library/Developer/CommandLineTools'
XCTRACE=XCODE+'/usr/bin/xctrace'
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
def put(name,value):
 with (ROOT/name).open('x') as f:json.dump({'label':LABEL,**value},f,indent=2)
def size(path):return sum(p.stat().st_size for p in path.rglob('*') if p.is_file()) if path.exists() else 0
def command(name,argv,developer=XCODE,timeout=30,allowed_failure=False,trace=None):
 out=ROOT/(name+'.stdout');err=ROOT/(name+'.stderr');assert not out.exists() and not err.exists()
 env={k:v for k,v in os.environ.items() if not k.startswith(('DYLD_','Malloc'))}
 env.update(DEVELOPER_DIR=developer,SDKROOT=CLT+'/SDKs/MacOSX.sdk')
 start=time.monotonic();reason=None
 with out.open('xb') as f,err.open('xb') as e:
  child=subprocess.Popen(list(map(str,argv)),env=env,stdout=f,stderr=e)
  while child.poll() is None:
   if time.monotonic()-start>timeout:reason='WALL_TIME_LIMIT';child.terminate();break
   if trace and size(trace)>268435456:reason='TRACE_STORAGE_LIMIT';child.terminate();break
   if out.stat().st_size+err.stat().st_size>33554432:reason='OUTPUT_LIMIT';child.terminate();break
   time.sleep(.1)
  try:code=child.wait(timeout=5)
  except subprocess.TimeoutExpired:child.kill();code=child.wait();reason=reason or 'KILLED_AFTER_TERMINATE'
 result={'label':LABEL,'name':name,'argv':list(map(str,argv)),'DEVELOPER_DIR':developer,'exit':code,'elapsed_seconds':time.monotonic()-start,'limit_reason':reason,'stdout_sha256':sha(out),'stderr_sha256':sha(err)}
 with (ROOT/'commands.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
 print(name,'exit',code,'limit',reason,flush=True)
 if not allowed_failure and (code or reason):raise RuntimeError('Retained failure: '+name)
 return result,out.read_text(errors='replace'),err.read_text(errors='replace')
def run():
 free=shutil.disk_usage(ROOT).free;assert free>=3221225472
 put('capacity-before-recording.json',{'free_bytes':free,'trace_cap_bytes':2147483648,'probe_cap_bytes':268435456})
 command('xcode-version',[XCODE+'/usr/bin/xcodebuild','-version'])
 _,templates,_=command('templates',[XCTRACE,'list','templates'])
 command('instrument-list',[XCTRACE,'list','instruments'],allowed_failure=True)
 command('record-usage',[XCTRACE,'record','--help'],allowed_failure=True)
 command('export-usage',[XCTRACE,'export','--help'],allowed_failure=True)
 compiler=CLT+'/usr/bin/clang++'
 _,version,_=command('compiler-version',[compiler,'--version'],developer=CLT)
 compile_argv=[compiler,'-std=c++20','-O3','-DNDEBUG','-arch','arm64','-mmacosx-version-min=26.0','-isysroot',CLT+'/SDKs/MacOSX.sdk','-Wall','-Wextra','-Wpedantic','-Wconversion','-Wsign-conversion','-Werror',str(REPO/'research/exploratory_e3/probe.cpp'),'-o',str(ROOT/'availability-probe')]
 command('compile-probe',compile_argv,developer=CLT)
 put('tool-identities.json',{'compiler_path':compiler,'compiler_sha256':sha(compiler),'compiler_version_stdout':version,'sdk_root':str(pathlib.Path(CLT+'/SDKs/MacOSX.sdk').resolve()),'xctrace_path':XCTRACE,'xctrace_sha256':sha(XCTRACE),'probe_sha256':sha(ROOT/'availability-probe'),'probe_source_sha256':sha(REPO/'research/exploratory_e3/probe.cpp'),'template_listings':{name:name in templates.splitlines() for name in ['System Trace','Processor Trace','CPU Counters']},'listing_is_not_recording_permission':True})
 trace=ROOT/'availability.trace'
 result,stdout,stderr=command('system-trace-probe',[XCTRACE,'record','--template','System Trace','--time-limit','3s','--no-prompt','--output',str(trace),'--target-stdout',str(ROOT/'probe-query-spans.jsonl'),'--launch','--',str(ROOT/'availability-probe')],timeout=60,allowed_failure=True,trace=trace)
 inventory={'recording':result,'trace_exists':trace.exists(),'trace_bytes':size(trace),'schemas':[],'thread_state_capture_verified':False,'synchronization_verified':False,'hardware_metrics_verified':False}
 if trace.exists():
  exported,_,_=command('probe-export-toc',[XCTRACE,'export','--input',str(trace),'--toc','--output',str(ROOT/'probe-toc.xml')],timeout=30,allowed_failure=True)
  inventory['toc_export']=exported
  if exported['exit']==0 and (ROOT/'probe-toc.xml').exists():
   tree=ET.parse(ROOT/'probe-toc.xml')
   inventory['schemas']=sorted({e.attrib['schema'] for e in tree.iter() if 'schema' in e.attrib})
 put('availability-result.json',inventory)
 if result['exit'] or result['limit_reason']:
  put('technical-verdict.json',{'verdict':'BLOCKED','reason':'Actual System Trace recording failed; essential thread-state capture and query/trace synchronization unavailable. No primary road sessions authorized by this gate.','primary_sessions':0,'primary_queries':0,'H1_assessment':'STILL_INCONCLUSIVE','tail_investigation_closed':True})
  return
 # A successful recording alone does not validate scheduler fields or synchronization.
 put('availability-pending-validation.json',{'verdict':'PENDING_VALIDATION','reason':'Recording succeeded; schema/state/span/clock joins must still be validated before dispatch.','primary_sessions':0,'primary_queries':0})
if __name__=='__main__':run()
