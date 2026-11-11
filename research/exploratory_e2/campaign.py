"""One bounded E2 diagnostic campaign; never resumes/replaces failed observations."""
import argparse,collections,hashlib,json,math,os,pathlib,platform,shlex,statistics,subprocess,time
LABEL='EXPLORATORY_BMSSP_TAIL_ATTRIBUTION'
REPO=pathlib.Path(__file__).resolve().parents[2]
ROOT=pathlib.Path((pathlib.Path(__file__).parent/'EVIDENCE_PATH.txt').read_text().strip())
ENV={k:v for k,v in os.environ.items() if not k.startswith(('DYLD_','Malloc')) and k not in ['CXXFLAGS','CPPFLAGS','LDFLAGS','CPATH','CPLUS_INCLUDE_PATH','LIBRARY_PATH']}
ENV.update(DEVELOPER_DIR='/Library/Developer/CommandLineTools',SDKROOT='/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk')
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_text())
def rows(p):return [json.loads(s) for s in pathlib.Path(p).read_text().splitlines() if s.startswith('{')]
def put(name,data):
 with (ROOT/name).open('x') as f:json.dump({'label':LABEL,**data},f,indent=2)
def run(name,argv):
 out=ROOT/(name+'.log');err=ROOT/(name+'.stderr');assert not out.exists() and not err.exists(),name
 start=time.monotonic();before=os.getloadavg()
 with out.open('xb') as f,err.open('xb') as e:p=subprocess.run(list(map(str,argv)),env=ENV,stdout=f,stderr=e)
 item={'label':LABEL,'name':name,'argv':list(map(str,argv)),'exit':p.returncode,'elapsed_seconds':time.monotonic()-start,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'load_before':before,'load_after':os.getloadavg(),'stdout_sha256':sha(out),'stderr_sha256':sha(err)}
 with (ROOT/'invocations.jsonl').open('a') as f:f.write(json.dumps(item)+'\n')
 print(name,'exit',p.returncode,'seconds',round(item['elapsed_seconds'],3),flush=True)
 if p.returncode:
  with (ROOT/'campaign-failure.json').open('x') as f:json.dump({'label':LABEL,'status':'INCOMPLETE_CAMPAIGN','failed_process':item,'automatic_replacement':False},f,indent=2)
  raise RuntimeError('Failed process retained; campaign stops: '+name)
 return rows(out)
def plan():
 inputs=read(ROOT/'input-identities.json')['inputs'];conditions=['A1','A2','B','D'];order=[[conditions[(n+row)%4] for n in [0,1,3,2]] for row in range(4)];jobs=[];graphs=list(inputs)
 for block in range(12):
  for graph in graphs[block%3:]+graphs[:block%3]:
   sources=list(enumerate(inputs[graph]['source_positions'][:10]));offset=block%10;sources=sources[offset:]+sources[:offset];path=ROOT/(f'block-{block:02d}-{graph}.sources');path.write_text(''.join(f'{i} {s}\n' for i,s in sources))
   for slot,c in enumerate(order[block%4]):jobs.append({'block':block,'graph':graph,'condition':c,'order_slot':slot,'sources':str(path),'measured_per_source':5,'warmup_per_source':1})
 assert len(jobs)==144
 put('predeclared-plan.json',{'primary_observations':7200,'jobs':jobs,'balanced_orders':order,'clock_characterization':{'consecutive_read_pairs_per_clock':10000,'empty_endpoint_pairs':10000},'endpoint_controls':{'conditions':['A1','B'],'modes':['plain','paired'],'graphs':graphs,'sources':10,'repetitions':3,'warmups':1,'primary':False},'allocator_diagnostics':{'variants':['A','B'],'replicate_processes':2,'sources':10,'repetitions':3,'warmups':1,'event_capacity':8192,'address_table_capacity':131072},'cpu_sampling':{'variants':['A','B'],'graphs':graphs,'seconds':3,'interval_ms':1,'worker_spin_seconds':5,'primary':False},'rules':{'clock_failure_or_backwards':'stop; retain incomplete campaign','negative_off_estimates':'retain without clamping','exclusions':[],'reschedule_failed_blocks':False,'tail_analysis':'nearest-rank p50/p95/p99; paired source/block and10000 block bootstrap draws seed20261112; no post-hoc acceptance threshold','causality':'off estimate bounded by read apertures/unknown clock accuracy, never proof of scheduler cause; allocation counts/RSS alone not allocator/layout causality'},'task15_collection':False})
 put('environment.json',{'host':platform.uname()._asdict(),'process_selection':{k:ENV[k] for k in ['DEVELOPER_DIR','SDKROOT']},'removed_environment_key_names':sorted(set(os.environ)-set(ENV)),'baseline_sdk_reference':read('/Users/sallahuddin/Projects/BMSSP-exploratory-E1-q8k1o451/native-build-manifest.json')['sdk'],'notes':'No Task15 identities/approvals or statistical estimands reused; SDK metadata reference is a current-input reference, not historical equivalence.'})
def build():
 for variant in ['A','B']:
  source=ROOT/('source-'+variant);target=ROOT/('build-raw-'+variant)
  run('configure-raw-'+variant,['/opt/homebrew/bin/cmake','-S',source,'-B',target,'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER=/Library/Developer/CommandLineTools/usr/bin/clang++','-DCMAKE_OSX_SYSROOT='+ENV['SDKROOT'],'-DCMAKE_OSX_ARCHITECTURES=arm64','-DCMAKE_OSX_DEPLOYMENT_TARGET=26.0','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DBMSSP_PYTHON=OFF','-DBMSSP_SANITIZERS=OFF','-DBMSSP_ALLOCATION_PROBE=OFF','-DCMAKE_PROJECT_bmssp_native_foundation_INCLUDE='+str(REPO/'research/exploratory_e2/add_target.cmake')])
  run('build-raw-'+variant,['/opt/homebrew/bin/cmake','--build',target,'--parallel','4'])
 def tool(argv):
  p=subprocess.run(argv,env=ENV,capture_output=True);return {'argv':argv,'exit':p.returncode,'stdout':p.stdout.decode(),'stderr':p.stderr.decode()}
 put('build-identities-raw.json',{'compiler_sha256':sha('/Library/Developer/CommandLineTools/usr/bin/clang++'),'compiler_version':tool(['/Library/Developer/CommandLineTools/usr/bin/clang++','--version']),'linker_sha256':sha('/Library/Developer/CommandLineTools/usr/bin/ld'),'tool_versions':[tool(['/opt/homebrew/bin/cmake','--version']),tool(['/usr/bin/sw_vers'])],'variants':{v:{'executable_sha256':sha(ROOT/('build-raw-'+v)/'e2_worker'),'correctness_executable_sha256':sha(ROOT/('build-raw-'+v)/'e2_correctness'),'library_sha256':sha(ROOT/('build-raw-'+v)/'libbmssp_foundation.a'),'compile_commands':read(ROOT/('build-raw-'+v)/'compile_commands.json'),'link_command':(ROOT/('build-raw-'+v)/'CMakeFiles/e2_worker.dir/link.txt').read_text(),'cmake_cache':(ROOT/('build-raw-'+v)/'CMakeCache.txt').read_text()} for v in ['A','B']},'condition_executables':{'A1':str(ROOT/'build-raw-A/e2_worker'),'A2':str(ROOT/'build-raw-A/e2_worker'),'D':str(ROOT/'build-raw-A/e2_worker'),'B':str(ROOT/'build-raw-B/e2_worker')},'A1_A2_identical_file':True})
def correctness():
 inputs=read(ROOT/'input-identities.json')['inputs']
 for v in ['A','B']:
  run('ctest-raw-'+v,['/opt/homebrew/bin/ctest','--test-dir',ROOT/('build-raw-'+v),'--output-on-failure','-j','1'])
  for g,p in inputs.items():run('correctness-raw-'+v+'-'+g,[ROOT/('build-raw-'+v)/'e2_correctness','check',p['native_export_path'],ROOT/(g+'-all.sources'),'bmssp','1','0',ROOT/(v+'-'+g+'-vectors.bin')])
 for g in inputs:assert sha(ROOT/('A-'+g+'-vectors.bin'))==sha(ROOT/('B-'+g+'-vectors.bin')),'Unexpected candidate vector mismatch'
def clocks():
 data=run('clock-characterization-raw',[ROOT/'build-raw-A/e2_worker','clock']);empty=[r for r in data if r['kind']=='empty_pair'];assert len(empty)==10000
 assert all(not any(r['clock_rc']) and r['wall_ns']>=0 and r['cpu_ns']>=0 and r['start_aperture_ns']>=0 and r['end_aperture_ns']>=0 for r in empty)
 for r in data:
  if r['kind']=='clock_increment':assert r['rc']==0 and r['delta_ns']>=0
 inputs=read(ROOT/'input-identities.json')['inputs']
 for i,(g,p) in enumerate(inputs.items()):
  for c in ['A1','B']:
   modes=['plain','paired'] if (i+(c=='B'))%2==0 else ['paired','plain']
   for mode in modes:run('endpoint-raw-'+g+'-'+c+'-'+mode,[ROOT/('build-raw-B' if c=='B' else 'build-raw-A')/'e2_worker',mode,p['native_export_path'],ROOT/(g+'-ten.sources'),c,g,'0','3','1','unused'])
def measure():
 quality=read(ROOT/'clock-quality-raw.json');assert quality['clock_errors']==0 and quality['empty_cpu_outside_envelope']==0
 assert read(ROOT/'predeclared-plan-raw.json')['jobs']==read(ROOT/'predeclared-plan.json')['jobs'];assert not (ROOT/'campaign-failure.json').exists()
 inputs=read(ROOT/'input-identities.json')['inputs'];plan=read(ROOT/'predeclared-plan-raw.json');identity=read(ROOT/'build-identities-raw.json')
 for j in plan['jobs']:
  c=j['condition'];g=j['graph'];exe=pathlib.Path(identity['condition_executables'][c]);assert sha(exe)==identity['variants']['B' if c=='B' else 'A']['executable_sha256']
  run(f"primary-{j['block']:02d}-{g}-{c}",[exe,'paired',inputs[g]['native_export_path'],j['sources'],c,g,str(j['block']),'5','1','unused'])
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('phase',choices=['plan','build','correctness','clocks','measure']);x=a.parse_args();globals()[x.phase]()
