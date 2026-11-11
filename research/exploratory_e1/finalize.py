"""Produce explicit E1 evidence reports without promoting the tested candidate."""
import collections,hashlib,json,pathlib,statistics,struct,subprocess,sys,shlex
from experiment import rows,digest,LABEL
root=pathlib.Path(sys.argv[1]);repo=pathlib.Path(__file__).resolve().parents[2];inputs=json.loads((root/'input-identities.json').read_text())['inputs'];comparison=json.loads((root/'controlled-comparison.json').read_text());assert comparison['sample_count']==6000
manifest=json.loads((root/'native-build-manifest.json').read_text());correct={};allocation={}
for variant in ['baseline','candidate']:
 report={}
 for graph,v in inputs.items():
  records=rows(root/('correctness-'+variant+'-'+graph+'.jsonl'));q=[x for x in records if x['kind']=='correctness'];assert len(q)==100 and [r['position'] for r in q]==list(range(100));assert [str(x['source']) for x in q]==v['source_positions'];assert all(not x['mismatches'] for x in q)
  n=records[0]['vertices'];binary=root/(graph+'-'+variant+'-vectors.bin');data=binary.read_bytes();assert len(data)==n*100*16;assert all(a==b for a,b in struct.iter_unpack('<QQ',data))
  report[graph]={'positions':100,'distance_entries':n*100,'distance_bit_mismatches':0,'reachable_path_checks':sum(x['reachable_paths'] for x in q),'unreachable_path_checks':sum(x['unreachable_paths'] for x in q),'vectors_sha256':digest(binary),'native_report_sha256':digest(root/('correctness-'+variant+'-'+graph+'.jsonl'))}
  if variant=='candidate':assert digest(binary)==correct['baseline'][graph]['vectors_sha256']
 correct[variant]=report;(root/(variant+'-correctness-report.json')).write_text(json.dumps({'label':LABEL,'passed':True,'graphs':report,'contract':'exact binary64, all100 original occurrences, all-target directed path reconstruction in both engines; no tolerance'},indent=2))
 for graph in inputs:
  group=[r for r in comparison['graphs'][graph].items() if r[0].startswith(variant+'_')];(root/(variant+'-statistical-summary.json')).write_text(json.dumps({'label':LABEL,'graphs':{g:{a:comparison['graphs'][g][variant+'_'+a] for a in ['bmssp','dijkstra']} for g in inputs}},indent=2))
for graph in inputs:
 a=[x for x in rows(root/('allocations-baseline-'+graph+'.jsonl')) if x['kind']=='allocation_diagnostic'];b=[x for x in rows(root/('allocations-candidate-'+graph+'.jsonl')) if x['kind']=='allocation_diagnostic'];assert len(a)==len(b)==10;query=[]
 for x,y in zip(a,b):
  assert (x['position'],x['source'],x['frontier_inserts'],x['label_nodes_materialized'])==(y['position'],y['source'],y['frontier_inserts'],y['label_nodes_materialized'])
  saved=x['new_calls']-y['new_calls'];saved_bytes=x['requested_bytes']-y['requested_bytes'];assert saved>0 and saved_bytes==saved*32;assert saved<=x['frontier_inserts']
  query.append({'position':x['position'],'source':x['source'],'baseline':x,'candidate':y,'calls_saved':saved,'bytes_saved':saved_bytes,'call_reduction_fraction':saved/x['new_calls']})
 allocation[graph]={'queries':query,'median_calls_saved':statistics.median(x['calls_saved'] for x in query),'median_requested_bytes_saved':statistics.median(x['bytes_saved'] for x in query),'median_allocation_call_reduction_fraction':statistics.median(x['call_reduction_fraction'] for x in query),'rss_baseline_median_bytes':statistics.median(comparison['graphs'][graph]['baseline_bmssp']['peak_rss_bytes']),'rss_candidate_median_bytes':statistics.median(comparison['graphs'][graph]['candidate_bmssp']['peak_rss_bytes'])}
(root/'allocation-and-memory-comparison.json').write_text(json.dumps({'label':LABEL,'graphs':allocation,'scope':'ordinary/aligned C++ requested allocations, includes result destruction; excludes C malloc/allocator metadata/OS allocations. RSS is separate whole-process Darwin high water.'},indent=2))
for variant in ['baseline','candidate']:
 output=root/('raw-'+variant+'-measurements.jsonl');count=0
 with output.open('w') as f:
  for p in json.loads((root/'measurement-plan.json').read_text())['conditions']:
   if p['variant']!=variant:continue
   name=f"matrix-b{p['block']:02d}-{p['graph']}-{p['variant']}-{p['algorithm']}"
   for r in rows(root/(name+'.jsonl')):
    if r['kind']=='sample':f.write(json.dumps({**p,**r})+'\n');count+=1
 assert count==3000
# Compare complete native library compiler argv after replacing only source/build roots.
def arguments(variant):
 build=root/('build-'+variant);source=root/'baseline-source' if variant=='baseline' else repo;out={}
 for record in manifest['builds'][variant]['compile_commands']:
  path=pathlib.Path(record['file'])
  if str(path).startswith(str(source/'native/src')):
   argv=shlex.split(record['command']);out[path.name]=[arg.replace(str(source),'<SOURCE>').replace(str(build),'<BUILD>') for arg in argv]
 return out
assert arguments('baseline')==arguments('candidate');assert len(arguments('baseline'))==8
for variant in ['baseline','candidate']:
 assert digest(root/('build-'+variant)/'e1_native')==manifest['builds'][variant]['executable_sha256'];assert digest(root/('build-'+variant)/'libbmssp_foundation.a')==manifest['builds'][variant]['library_sha256']
base='5e8b11b4db8a0883969e7fe1405b048f419d7f07';assert subprocess.check_output(['git','rev-parse','codex/genuine-bmssp-engine'],cwd=repo,text=True).strip()==base
assert subprocess.check_output(['git','diff','--name-only',base,'--'],cwd=repo,text=True).strip()==''
p=json.loads((repo/'docs/task15_tail_attribution_protocol_v1.3.0.json').read_text());expected=p['identity'].pop('sha256');assert hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()==expected=='b639d9960353f00c5a3d5efc58255206d5dd7d7f701311ebe7f715f5ad277ddd'
for artifact in p['binaries'].values():assert digest(artifact['path'])==artifact['sha256']
files=subprocess.check_output(['git','ls-tree','-r','--name-only',base],cwd=repo,text=True).splitlines();integrity={'label':LABEL,'starting_commit':base,'original_branch_commit':base,'active_native_source':'baseline restored; unaccepted candidate retained as patch/snapshot/binaries','protected_files':{name:digest(repo/name) for name in files},'candidate_patch_sha256':digest(root/'candidate-engine.diff'),'candidate_source_snapshot_sha256':digest(root/'candidate-source-snapshot.tar'),'protocol_canonical_sha256':expected,'task15_unchanged_and_blocked':True,'engine_compiler_flags_equal_after_only_path_normalization':True,'native_source_differences':[name for name,h in manifest['builds']['candidate']['source_sha256'].items() if h!=manifest['builds']['baseline']['source_sha256'][name]]};assert integrity['native_source_differences']==['native/src/bounded_frontier.cpp'];(root/'source-integrity.json').write_text(json.dumps(integrity,indent=2))
print('Validated all6000 samples, exact vectors, allocation mechanism, build flags and preserved sources.')
