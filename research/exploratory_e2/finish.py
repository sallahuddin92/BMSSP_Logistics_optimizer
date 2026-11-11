"""Finalize immutable E2 evidence, with limited conclusions and no H1 promotion."""
import ast,collections,hashlib,json,pathlib,statistics,struct,subprocess,time
from campaign import ROOT,REPO,LABEL,read,rows,put,sha
def finish():
 inputs=read(ROOT/'input-identities.json')['inputs'];correct={}
 for v in ['A','B']:
  correct[v]={}
  for g in inputs:
   data=rows(ROOT/f'correctness-{v}-{g}.log');query=[r for r in data if r['kind']=='correctness'];assert len(query)==100 and [r['position'] for r in query]==list(range(100));assert all(not r['mismatches'] for r in query)
   vector=ROOT/f'{v}-{g}-vectors.bin';raw=vector.read_bytes();assert len(raw)==data[0]['vertices']*100*16 and all(a==b for a,b in struct.iter_unpack('<QQ',raw))
   correct[v][g]={'positions':100,'distance_entries':data[0]['vertices']*100,'bit_mismatches':0,'valid_reachable_paths':sum(r['reachable_paths'] for r in query),'valid_unreachable_paths':sum(r['unreachable_paths'] for r in query),'vectors_sha256':sha(vector)}
   if v=='B':assert correct[v][g]['vectors_sha256']==correct['A'][g]['vectors_sha256']
  log=(ROOT/f'ctest-{v}.log').read_text();assert '100% tests passed, 0 tests failed out of 19' in log
 put('correctness-report.json',{'variants':correct,'native_regressions':{'A':19,'B':19},'raw_clock_rebuild_continuity':read(ROOT/'clock-quality-raw.json')['native_identity_continuity'],'unexpected_native_failures':0})
 identity=read(ROOT/'build-identities-raw.json')
 for v in ['A','B']:assert sha(ROOT/('build-raw-'+v)/'e2_worker')==identity['variants'][v]['executable_sha256']
 assert identity['condition_executables']['A1']==identity['condition_executables']['A2']
 # Verify SDK against the full current E1 inventory, without copying licensed bytes.
 e1=pathlib.Path('/Users/sallahuddin/Projects/BMSSP-exploratory-E1-q8k1o451');inventory=read(e1/'fresh-sdk-inventory.json');sdk=pathlib.Path(inventory['root']);cache={};checked=0;begin=time.monotonic()
 import os,stat
 physical={'.'}
 for directory,dirs,files in os.walk(sdk,followlinks=False):physical.update(str((pathlib.Path(directory)/name).relative_to(sdk)) for name in dirs+files)
 assert physical=={r['path'] for r in inventory['entries']}
 for r in inventory['entries']:
  p=sdk/r['path'];s=p.lstat();assert stat.S_IMODE(s.st_mode)==r['mode']
  if r['type']=='symlink':assert p.is_symlink() and os.readlink(p)==r['symlink_target'];target=p.resolve();assert target==sdk or sdk in target.parents
  else:target=p
  if r['sha256']:
   key=str(target)
   if key not in cache:cache[key]=sha(target)
   assert cache[key]==r['sha256'];checked+=1
 put('sdk-current-verification.json',{'sdk_root':str(sdk),'full_inventory_sha256':sha(e1/'fresh-sdk-inventory.json'),'tree_sha256':inventory['tree_sha256'],'physical_entries_verified':len(physical),'content_records_verified':checked,'elapsed_seconds':time.monotonic()-begin,'scope':'Current post-campaign bytes match the full selected E1 current SDK inventory; no historical Task15 continuity claim.'})
 put('hypothesis-assessment.json',{'hypotheses':{
 'H2-A':{'assessment':'PARTIAL_SUPPORT','evidence':'Some wall tails include large positive wall-minus-CPU estimates, up to roughly10–18ms in selected worst observations; many also have elevated CPU. Not proof of scheduler cause or a complete explanation.'},
 'H2-B':{'assessment':'SUPPORTED_AS_SHARED_BEHAVIOR_NOT_H1_SPECIFIC','evidence':'B wall-reference tails also exceed CPU reference in9/12 medium and18/22 corridor events; unchanged A1/A2 have CPU-time tails too. Underlying on-CPU cause unidentified.'},
 'H2-C':{'assessment':'H1_MECHANISM_VERIFIED_TAIL_CAUSE_UNRESOLVED','evidence':'Paired callback differences exactly match removed32-byte same-insertion temporaries; reuse and zero tracked post-result live bytes observed. Separate tracing perturbs latency/RSS; no direct allocator-cache or layout-to-primary-tail causal link.'},
 'H2-D':{'assessment':'ASSOCIATION_NOT_CAUSAL_IDENTIFICATION','evidence':'A1 small extremes concentrate in block0; other tails span blocks/sources. Williams order balances slots; source/block/slot/load and image-slide data retained. No direct thermal/core-placement/cache evidence.'},
 'H2-E':{'assessment':'STRONG_SUPPORT_FOR_LIMITED_TAIL_PRECISION','evidence':'Byte-identical A2/A1 medium wall p99 ratio1.07975; B/A1 and B/A2 medium/corridor p99 intervals span1. Only12 blocks,600 samples/condition/graph and60/source. Ordinary experimental variation is present; original E1 cause cannot be retrospectively established.'}},
 'strongest_supported_conclusion':'Shared on-thread CPU-time variability plus occasional substantial wall-minus-CPU components affect tails in unchanged controls too. E1 candidate-specific p99 pattern is not stably reproduced; lower-level causal mechanism remains unknown.'})
 put('h1-acceptance-assessment.json',{'campaign_verdict':'INCONCLUSIVE','H1_assessment':'STILL_INCONCLUSIVE','promoted':False,'reason':'Median wall/CPU benefits recur, and medium/corridor point p99 ratios improve versus both controls, but exploratory p99 intervals remain broad and B retains extreme mixed CPU/off-CPU observations. No acceptance tolerance introduced after data; no algorithm change or promotion.'})
 put('failure-exclusion-ledger.json',{'primary_attempted':7200,'primary_completed':7200,'primary_failed_processes':[],'primary_exclusions':[],'replacement_or_favorable_reruns':0,'negative_primary_off_estimates':read(ROOT/'primary-quality.json')['negative_off_estimates'],'predata_clock_correction':read(ROOT/'predeclared-plan-raw.json')['pre_data_clock_correction'],'v1_endpoint_controls_not_pooled':True,'setup_events':[{'event':'Tool-call serialization errors while writing diagnostic files','effect':'No files/native processes created by rejected calls; retried file creation before diagnostics.'},{'event':'Exclusive configure-A log guard refused reuse after choosing a new raw-clock build directory','effect':'No existing output overwritten; corrected log names before new builds.'}],'bounded_trace_event_truncation':'8192 retained events/process; all additional callback-event records explicitly counted as not retained; aggregate counters/histograms and table remained complete.'})
 base='04cf15c043e290c375155d7b0f2cd30c4c65d4f5'
 assert subprocess.check_output(['git','diff','--name-only',base,'--'],cwd=REPO,text=True).strip()==''
 assert subprocess.check_output(['git','rev-parse','research/bmssp-exploratory-performance'],cwd=REPO,text=True).strip()==base
 assert subprocess.check_output(['git','rev-parse','codex/genuine-bmssp-engine'],cwd=REPO,text=True).strip()=='5e8b11b4db8a0883969e7fe1405b048f419d7f07'
 for name,value in read(ROOT/'measurement-source-lock.json')['source_files'].items():assert sha(REPO/name)==value,name
 for v in ['A','B']:
  for name,value in read(ROOT/'source-identities.json')['sources'][v].items():assert sha(ROOT/('source-'+v)/name)==value
 frozen=read(REPO/'docs/task15_tail_attribution_protocol_v1.3.0.json');expected=frozen['identity'].pop('sha256');assert hashlib.sha256(json.dumps(frozen,sort_keys=True,separators=(',',':')).encode()).hexdigest()==expected
 for item in frozen['binaries'].values():assert sha(item['path'])==item['sha256']
 assert sha(e1/'completion-receipt.json')=='ada7f61268569c8aeb60e58d42589153c16521bf84e7c8deb271aff7d670acda'
 original_files=subprocess.check_output(['git','ls-tree','-r','--name-only',base],cwd=REPO,text=True).splitlines()
 put('source-integrity.json',{'starting_commit':base,'protected_files':{name:sha(REPO/name) for name in original_files},'task15_protocol_canonical_sha256':expected,'task15_status':'BLOCKED','E1_receipt_sha256':sha(e1/'completion-receipt.json'),'H1_patch_sha256':sha(REPO/'research/exploratory_e1/candidate-engine.diff'),'active_native_source_unchanged':True,'H1_patch_unchanged':True,'no_scientific_approval':True})
 print('Validated7200 observations, native/road correctness, source locks, fixed H1 and current SDK.',flush=True)
if __name__=='__main__':finish()
