#!/usr/bin/env python3
"""Independent STATIC validator. No generator import, engine import, benchmark or clock calls.
Strict host hashes by default; --portable explicitly leaves external inputs UNVERIFIED.
--self-test mutates in-memory synthetic copies and checks small dimensionless RNG fixtures.
"""
import argparse,collections,copy,hashlib,json,math,pathlib,subprocess,sys
PARENT_HASH='590838e4fdde2dcd86228fe0c521845e479fcc6372fa39d3745cb21270ce8247'
PARENT_FILES={'task15_tail_attribution_protocol.json':'081b6f2cb06e59c9a0578b78f9a007be505fef11f2302ae834d4c62dd209ed17','task15_tail_attribution_preregistration.md':'c9ae85657fd94c1d51485f06a2ea6e022d848473e79969354a36ae13cc5330c5'}
SEED='BMSSP-T15-AMENDMENT-v1.1.0-20261106-P2'
def encode(v):return json.dumps(v,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def fingerprint(v):return hashlib.sha256(encode(v)).hexdigest()
def key(*parts):return hashlib.sha256(encode([SEED]+list(parts))).hexdigest()
def rehash(p):
 p['design']['schedule_sha256']=fingerprint(p['design']['base_schedule']);p['design']['diagnostic_schedule_sha256']=fingerprint(p['design']['diagnostic_schedule']);p['design']['allocator_stack_companions_sha256']=fingerprint(p['design']['allocator_stack_companions']);x=copy.deepcopy(p);x['identity'].pop('sha256',None);p['identity']['sha256']=fingerprint(x)
def validate(p,parent,repo,external=True):
 errors=[];passed=[];unverified=[]
 def check(code,ok,detail=''):
  (passed if ok else errors).append({'code':code,'detail':detail})
 x=copy.deepcopy(p);stored=x.get('identity',{}).pop('sha256',None);check('CANONICAL_HASH',fingerprint(x)==stored)
 x=copy.deepcopy(parent);h=x['identity'].pop('sha256');check('PARENT_HASH',h==PARENT_HASH and fingerprint(x)==PARENT_HASH)
 check('VERSION_AUTH',p.get('version')=='1.1.0'and p.get('execution_authorized')is False and p.get('promotion_authorized')is False)
 for f,want in PARENT_FILES.items():check('PARENT_BYTES',hashlib.sha256((repo/'docs'/f).read_bytes()).hexdigest()==want,f)
 for path,want in parent['runtime_tree_identities'].items():
  actual=subprocess.check_output(['git','rev-parse','HEAD:'+path],cwd=repo,text=True).strip();check('RUNTIME_IDENTITY',actual==want==p['runtime_tree_identities'][path],path)
 check('INPUT_IDS',p['inputs']==parent['inputs'],'all IDs, repeated occurrences, targets, hashes and source positions identical')
 regs=parent['design']['regions'];rows=p['design']['base_schedule'];original={r['id']:r for r in parent['design']['base_schedule']};check('TRIAL_COUNT',len(rows)==64 and collections.Counter(r.get('protocol')for r in rows)=={'P1':32,'P2':32})
 check('TRIAL_UNIQUENESS',len({r.get('id')for r in rows})==len(rows)and set(r.get('id')for r in rows)==set(original))
 check('SESSION_IDS',set(r.get('session')for r in rows)==set(range(8)))
 check('SESSIONS_PRESERVED',p['design']['sessions']==parent['design']['sessions'])
 check('ROW_SEQUENCE', [r.get('id')for r in rows]==[r['id']for r in parent['design']['base_schedule']])
 common={'id','session','protocol','trial_within_protocol','startup_order','regions','positions_by_region'}
 for r in rows:
  extra={'P1_variant_order'}if r.get('protocol')=='P1'else{'P2_pair_orders_by_region'};check('ROW_SCHEMA',set(r)==common|extra,r.get('id','?'))
  old=original.get(r.get('id'));check('TRIAL_MAPPING',old is not None and all(r.get(k)==old[k]for k in common),r.get('id','?'))
  if old is None:continue
  check('ZERO_BASED_ID',r['id']==f"S{r['session']:02d}-{r['protocol']}-T{r['trial_within_protocol']:02d}"and r['session']==r['trial_within_protocol']//4,r['id'])
  check('REGION_ORDER',r['regions']==old['regions']and sorted(r['regions'])==sorted(regs),r['id'])
  for g in regs:
   positions=r['positions_by_region'].get(g,[]);check('PERMUTATION',len(positions)==100 and all(type(i)is int for i in positions)and sorted(positions)==list(range(100)),r['id']+g)
 if errors and any(e['code']in ['TRIAL_COUNT','TRIAL_UNIQUENESS','PERMUTATION','ROW_SCHEMA']for e in errors):return {'errors':errors,'checks':passed,'unverified':unverified}
 p2=[r for r in rows if r['protocol']=='P2'];p1=[r for r in rows if r['protocol']=='P1'];balance={}
 # Map every execution slot -> ORIGINAL POSITION before accumulating counts.
 for g in regs:
  counts=collections.Counter();per_session={s:collections.Counter()for s in range(8)};per_iteration=collections.Counter()
  ordered_positions=sorted(range(100),key=lambda v:(key('position_pairs',g,v),v));pairs=[ordered_positions[i:i+2]for i in range(0,100,2)]
  check('PAIR_PROOF',p['design']['order_assignment_construction']['position_pairs'][g]==pairs,g)
  for r in p2:
   labels=r['P2_pair_orders_by_region'][g];check('P2_TRIAL_BALANCE',len(labels)==100 and collections.Counter(labels)=={'AB':50,'BA':50},r['id']+g)
   expected={};session=r['session'];slot=r['trial_within_protocol']%4
   for n,(a,b)in enumerate(pairs):
    selected=sorted(range(4),key=lambda v:(key('AB_slots',g,session,n,v),v))[:2];expected[a]='AB'if slot in selected else'BA';expected[b]='BA'if slot in selected else'AB'
    check('SLOT_PROOF',p['design']['order_assignment_construction']['first_position_AB_slots_by_region_session'][g][str(session)][n]==selected,g)
   for execution,pos in enumerate(r['positions_by_region'][g]):
    order=labels[execution];check('P2_MAPPING',order==expected[pos],f"{r['id']} {g} execution={execution} original={pos}")
    if order=='AB':counts[pos]+=1;per_session[session][pos]+=1;per_iteration[execution]+=1
   check('SOURCE_OCCURRENCE',all(p['inputs'][g]['source_positions'][pos]==parent['inputs'][g]['source_positions'][pos]for pos in r['positions_by_region'][g]),r['id']+g)
  check('P2_POSITION_BALANCE',all(counts[i]==16 for i in range(100)),g)
  check('P2_SESSION_BALANCE',all(per_session[s][i]==2 for s in range(8)for i in range(100)),g)
  balance[g]={'original_position_AB_min':min(counts[i]for i in range(100)),'original_position_AB_max':max(counts[i]for i in range(100)),'session_AB_values':sorted({per_session[s][i]for s in range(8)for i in range(100)}),'iteration_AB_min':min(per_iteration[i]for i in range(100)),'iteration_AB_max':max(per_iteration[i]for i in range(100))}
 for s in range(8):
  for prot in ['P1','P2']:
   subset=[r for r in rows if r['session']==s and r['protocol']==prot];check('SESSION_TRIAL_COUNT',len(subset)==4,f'{s}{prot}');check('STARTUP_BALANCE',collections.Counter(r['startup_order']for r in subset)=={'AB':2,'BA':2})
  subset=[r for r in p1 if r['session']==s];check('P1_ORTHOGONAL',collections.Counter((r['startup_order'],r['P1_variant_order'])for r in subset)=={('AB','AB'):1,('AB','BA'):1,('BA','AB'):1,('BA','BA'):1})
 for prot in ['P1','P2']:
  for g in regs:check('REGION_COUNTS',sorted(collections.Counter(r['regions'].index(g)for r in rows if r['protocol']==prot).values())==[10,11,11])
 check('SCHEDULE_HASH',fingerprint(rows)==p['design']['schedule_sha256'])
 check('DIAGNOSTIC_HASH',fingerprint(p['design']['diagnostic_schedule'])==p['design']['diagnostic_schedule_sha256'])
 check('STACK_HASH',fingerprint(p['design']['allocator_stack_companions'])==p['design']['allocator_stack_companions_sha256'])
 lookup={r['id']:r for r in rows};diag=p['design']['diagnostic_schedule'];stacks=p['design']['allocator_stack_companions']
 check('DIAG_IDS',len(diag)==48 and len({r['id']for r in diag})==48 and len(stacks)==4)
 old_diags={r['id']:r for r in parent['design']['diagnostic_schedule']+parent['design']['allocator_stack_companions']}
 for d in diag+stacks:
  ref=lookup.get(d['schedule_ref']);check('DIAG_REFERENCE',ref is not None and ref['protocol']=='P2',d['id'])
  check('DIAG_IDENTITY',{k:v for k,v in d.items()if k!='resolved_workload_sha256'}==old_diags.get(d['id']),d['id'])
  if ref is None:continue
  subset=p['cohorts']['C']['positions_by_region']if d.get('cohort')=='C'or d['id'].startswith('C-stack-')else{g:list(range(100))for g in regs}
  work={'source_permutations':ref['positions_by_region'],'pair_orders_execution_index':ref['P2_pair_orders_by_region'],'positions_by_region':subset,'source_position_identities':{g:p['inputs'][g]['source_position_identity_sha256']for g in regs}}
  check('DIAG_WORKLOAD',fingerprint(work)==d.get('resolved_workload_sha256'),d['id'])
 check('C_UNCHANGED_SMALL_CORRIDOR',all(p['cohorts']['C']['positions_by_region'][g]==parent['cohorts']['C']['positions_by_region'][g]for g in [regs[0],regs[2]]))
 # Validate declared historical selection even portably; raw truth additionally checked on Mac.
 declared=p['cohorts']['C']['historical_medium_tail_evidence']['records']
 check('MEDIUM_DECLARED_MAPPING',len(declared)==18 and collections.Counter(r['variant']for r in declared)=={'baseline':9,'candidate':9}and all(r['source_id']==parent['inputs']['seremban-medium']['source_positions'][r['sample_index']]and r['wall_seconds']>=r['p99_boundary_seconds']for r in declared))
 check('MEDIUM_DECLARED_COVERAGE',p['cohorts']['C']['positions_by_region']['seremban-medium']==sorted(set(range(10))|{r['sample_index']for r in declared}))
 # Reconstruct historical cohort directly from all16 medium raw files, not stored selected metadata.
 evidence=pathlib.Path(parent['inputs']['seremban-medium']['query_file_path']).parents[3];tail=[]
 if external:
  for variant in ['baseline','candidate']:
   observations=[]
   for batch in ['final-ab','replication-ab']:
    for t in range(4):
     rawfile=evidence/'run'/batch/f'{t}-seremban-medium-{variant}.json';raw=json.loads(rawfile.read_bytes());check('HISTORICAL_SOURCE_MAPPING',[str(s['source'])for s in raw['samples']]==parent['inputs']['seremban-medium']['source_positions'])
     observations.extend((s['seconds'],str(rawfile),i,str(s['source']),batch,t)for i,s in enumerate(raw['samples']))
   cutoff=sorted(x[0]for x in observations)[791]
   tail.extend((variant,file,i,source,seconds,cutoff,batch,t)for seconds,file,i,source,batch,t in observations if seconds>=cutoff)
  stored_tail=p['cohorts']['C']['historical_medium_tail_evidence']['records'];actual=[(r['variant'],r['raw_file'],r['sample_index'],r['source_id'],r['wall_seconds'],r['p99_boundary_seconds'],r['batch'],r['trial'])for r in stored_tail];check('MEDIUM_RAW_TAIL',sorted(actual)==sorted(tail))
  expected=sorted(set(range(10))|{x[2]for x in tail});check('MEDIUM_COVERAGE',p['cohorts']['C']['positions_by_region']['seremban-medium']==expected)
  # All parent external byte identities + supplied independent reviews + new raw selection inputs.
  for path,want in list(parent['evidence_files_used'].items())+[(q,{'sha256':v})for q,v in p['amendment']['review_references'].items()]+list(p['cohorts']['C']['historical_medium_tail_evidence']['raw_input_hashes'].items()):
   check('EXTERNAL_HASH',pathlib.Path(path).is_file()and hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==want['sha256'],path)
  assessment=p['calibration']['allocation_capacity_assessment'];max_ops=0
  for record in assessment['historical_records']:
   path=pathlib.Path(record['path']);data=path.read_bytes();actual=json.loads(data);check('ALLOCATION_HASH',hashlib.sha256(data).hexdigest()==record['sha256']);check('ALLOCATION_SCOPE',len(actual['queries'])==record['queries']==10 and sum(x['new_calls']for x in actual['queries'])==record['sum_new_calls']);m=max(x['new_calls']+x['delete_calls']for x in actual['queries']);max_ops=max(max_ops,m);check('ALLOCATION_MAX',m==record['max_per_query_new_plus_delete'])
  check('ALLOCATION_MAX_ALL',max_ops==assessment['max_observed_per_query_operations']==1886462)
 else:unverified.append('EXTERNAL_HASHES_HISTORICAL_TAIL_AND_ALLOCATION_NOT_VERIFIED_PORTABLE_MODE')
 assessment=p['calibration']['allocation_capacity_assessment'];n=sum(len(x)for x in p['cohorts']['C']['positions_by_region'].values());check('EVENT_CAPACITY',p['calibration']['C_event_limit_per_query']==assessment['new_capacity']==4000000 and n==41 and assessment['worst_uncompressed_timed_C_event_bytes']==8*2*n*4000000*128 and assessment['buffer_bytes_per_worker']==512000000 and assessment['storage_preflight_GiB_min']==512)
 check('ACCEPTANCE_UNCHANGED',all(p['acceptance'].get(k)==v for k,v in parent['acceptance'].items()))
 old_b=parent['statistics']['bootstrap'];new_b=p['statistics']['bootstrap'];check('BOOTSTRAP_THRESHOLDS',all(new_b[k]==v for k,v in old_b.items()if k!='limitations'))
 check('CPU_THRESHOLDS',p['statistics']['secondary_CPU_family']==parent['statistics']['secondary_CPU_family'])
 check('CALIBRATION_THRESHOLDS',p['calibration']['diagnostic_precision_gates']==parent['calibration']['diagnostic_precision_gates'])
 check('H1_SPEC',all(p['statistics']['H1_event_rules'].get(k)for k in ['reference','precision_floor','moderate_absolute_paired_threshold','severe_absolute_paired_threshold','continuous_analysis','offCPU_accounting','heuristic_interpretation']))
 check('EQUIVALENCE_GATES',{g['id']for g in p['calibration']['diagnostic_build_equivalence']['gates']}=={'G1_source','G2_semantics','G3_ABI','G4_flags','G5_inputs','G6_A_isolation','G7_identity_lock','G8_codegen','G9_overhead','G10_approval'}and len(p['calibration']['diagnostic_build_equivalence']['gates'])==10 and p['calibration']['diagnostic_build_equivalence']['all_required']is True)
 check('BOOTSTRAP_EXECUTION_CONSTANTS',p['statistics']['bootstrap_execution_spec']['numpy_version'].startswith('1.24.4 exactly')and p['statistics']['bootstrap_execution_spec']['endpoint_fractions']=={'ordinary95':[[1,40],[39,40]],'primary99_5':[[1,400],[399,400]],'secondaryCPU':[[1,240],[239,240]]})
 check('BOOTSTRAP_SPEC',all(p['statistics']['bootstrap_execution_spec'].get(k)for k in ['primary_draw_order','sensitivity_draw_order','endpoint_fractions','failed_or_missing','deterministic_serialization','numpy_version']))
 check('NO_APPROVAL',p['amendment']['approval_status']=='NOT_INDEPENDENTLY_APPROVED'and p['amendment']['new_task15_observations_used']is False)
 return {'errors':errors,'checks':passed,'unverified':unverified,'balance':balance,'P1_combinations':{'/'.join(k):v for k,v in collections.Counter((r['startup_order'],r['P1_variant_order'])for r in p1).items()}}
def negative_controls(p,parent,repo):
 results=[]
 def run(name,fn,expected,refresh=True):
  q=copy.deepcopy(p);fn(q)
  if refresh:rehash(q)
  outcome=validate(q,parent,repo,False);codes={x['code']for x in outcome['errors']};assert expected in codes,(name,codes);results.append({'synthetic_mutation':name,'expected_failure':expected,'observed_failure_codes':sorted(codes),'rejected':True})
 g=p['design']['regions'][0];index=next(i for i,r in enumerate(p['design']['base_schedule'])if r['protocol']=='P2')
 def flip(q):
  r=q['design']['base_schedule'][index];a=r['P2_pair_orders_by_region'][g];a[0]='BA'if a[0]=='AB'else'AB'
 def swap_map(q):
  a=q['design']['base_schedule'][index]['P2_pair_orders_by_region'][g];j=next(i for i in range(1,100)if a[i]!=a[0]);a[0],a[j]=a[j],a[0]
 def duplicate(q):
  a=q['design']['base_schedule'][index]['positions_by_region'][g];a[1]=a[0]
 def source(q):
  a=q['inputs'][g]['source_positions'];rep=next(i for i,s in enumerate(a)if a.count(s)>1);a[rep]=a[next(i for i,s in enumerate(a)if s!=a[rep])]
 run('flip_one_P2_order',flip,'P2_TRIAL_BALANCE');run('wrong_execution_to_original_mapping',swap_map,'P2_MAPPING');run('duplicate_position',duplicate,'PERMUTATION');run('remove_trial',lambda q:q['design']['base_schedule'].pop(),'TRIAL_COUNT');run('corrupt_diagnostic_reference',lambda q:q['design']['diagnostic_schedule'][0].update(schedule_ref='NO_SUCH_TRIAL'),'DIAG_REFERENCE');run('corrupt_canonical_hash',lambda q:q['identity'].update(sha256='0'*64),'CANONICAL_HASH',False);run('break_repeated_source_position',source,'INPUT_IDS');run('add_cross_protocol_field',lambda q:q['design']['base_schedule'][index].update(P1_variant_order='AB'),'ROW_SCHEMA');run('relax_tail_gate',lambda q:q['acceptance'].update(B_medium_tail='R99<=1.10'),'ACCEPTANCE_UNCHANGED');run('stale_derived_workload_hash',lambda q:q['design']['diagnostic_schedule'][0].update(resolved_workload_sha256='0'*64),'DIAG_WORKLOAD')
 return results
def vector_tests(path):
 import numpy as np
 if np.__version__!='1.24.4':raise RuntimeError('Static RNG fixtures require existing NumPy1.24.4, no auto install')
 fixture=json.loads(path.read_text());rng=np.random.Generator(np.random.PCG64(15062026));observed=[]
 for repeat in range(2):
  ss=rng.integers(0,8,size=8,dtype=np.int64,endpoint=False).tolist();slots=[]
  for session in ss:slots.append({p:rng.integers(0,4,size=4,dtype=np.int64,endpoint=False).tolist()for p in ['P1','P2']})
  observed.append({'sessions':ss,'slots_by_occurrence':slots})
 assert observed==fixture['primary_first_two_draws'],'RNG_DRAW_VECTOR'
 rng2=np.random.Generator(np.random.PCG64(15062027));strat=[]
 for rep in range(2):
  strata=[]
  for session in range(8):
   row={}
   for proto in ['P1','P2']:row[proto]=rng2.integers(0,4,size=4,dtype=np.int64,endpoint=False).tolist()
   strata.append(row)
  strat.append({'sessions':list(range(8)),'slots_by_occurrence':strata})
 assert strat==fixture['stratified_first_two_draws'],'STRATIFIED_RNG_VECTOR'
 values=[]
 for draw in observed:
  row={}
  for proto in ['P1','P2']:
   baseline=[];candidate=[]
   for occurrence,s in enumerate(draw['sessions']):
    for t in draw['slots_by_occurrence'][occurrence][proto]:
     for pos in range(4):
      b=1000+100*s+10*t+pos;baseline.append(b);candidate.append(b+2*(s-4)+t-1)
   a=sorted(baseline);b=sorted(candidate);row[proto]={name:b[(len(b)*num+den-1)//den-1]/a[(len(a)*num+den-1)//den-1]for name,num,den in [('p50',1,2),('p95',19,20),('p99',99,100)]}
  values.append(row)
 assert values==fixture['dimensionless_toy_quantile_ratios'],'TOY_QUANTILE_VECTOR'
 for name,pair in fixture['interval_index_vectors_n100000'].items():
  rational=fixture['interval_fractions'][name];actual=[(100000*n+d-1)//d-1 for n,d in rational];assert actual==pair
 return {'fixture':'SYNTHETIC_DIMENSIONLESS_NOT_PERFORMANCE','numpy':np.__version__,'draw_vectors':4,'quantile_ratio_vectors':len(values)*2*3,'interval_endpoint_vectors':6,'status':'PASS'}
def main():
 a=argparse.ArgumentParser();a.add_argument('protocol',type=pathlib.Path);a.add_argument('--repo',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[2]);a.add_argument('--portable',action='store_true');a.add_argument('--self-test',action='store_true');a.add_argument('--output',type=pathlib.Path,required=True);args=a.parse_args();p=json.loads(args.protocol.read_text());parent=json.loads((args.repo/'docs/task15_tail_attribution_protocol.json').read_text());out=validate(p,parent,args.repo,not args.portable)
 if args.self_test:out['negative_controls']=negative_controls(p,parent,args.repo);out['bootstrap_vectors']=vector_tests(pathlib.Path(__file__).with_name('bootstrap_vectors.json'))
 out['status']='PASS_STATIC_HOST'if not out['errors']and not out['unverified']else'PASS_STATIC_PORTABLE_EXTERNAL_UNVERIFIED'if not out['errors']else'FAIL';out['check_count']=len(out['checks']);out['error_count']=len(out['errors']);out['no_BMSSP_workload_executed']=True;args.output.parent.mkdir(parents=True,exist_ok=True)
 with args.output.open('x')as f:json.dump(out,f,indent=2,ensure_ascii=True,allow_nan=False);f.write('\n')
 print(json.dumps({k:v for k,v in out.items()if k not in ['checks','errors']},indent=2));return bool(out['errors'])
if __name__=='__main__':sys.exit(main())
