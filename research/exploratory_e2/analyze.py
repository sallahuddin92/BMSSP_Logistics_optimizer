"""Exploratory paired/block analyses; no exclusions, clock-overhead subtraction or promotion."""
import collections,math,random,statistics
from campaign import ROOT,LABEL,read,rows,put
from quality import q

CONDITIONS=['A1','A2','B','D']
PAIRS=[('B','A1'),('B','A2'),('A2','A1')]
METRICS=['wall_ns','cpu_ns','off_estimate_ns']
def collect():
 plan=read(ROOT/'predeclared-plan-raw.json');inputs=read(ROOT/'input-identities.json')['inputs'];samples=[];headers=[]
 logs={r['name']:r for r in rows(ROOT/'invocations.jsonl')}
 for job in plan['jobs']:
  name=f"primary-{job['block']:02d}-{job['graph']}-{job['condition']}";r=rows(ROOT/(name+'.log'));assert logs[name]['exit']==0 and r[0]['kind']=='header' and r[-1]['kind']=='footer'
  assert r[-1]['samples']==50;headers.append({**job,**r[0]})
  group=[s for s in r if s['kind']=='sample'];assert len(group)==50
  for s in group:
   assert s['label']==LABEL and not any(s['clock_rc']) and s['wall_ns']>0 and s['cpu_ns']>=0
   assert str(s['source'])==inputs[s['graph']]['source_positions'][s['position']]
   assert s['off_estimate_ns']==s['wall_ns']-s['cpu_ns']
   samples.append({**job,**s,'host_before':logs[name]['load_before'],'invocation_utc':logs[name]['utc']})
 assert len(samples)==7200
 keys=[(s['graph'],s['condition'],s['block'],s['position'],s['repeat']) for s in samples];assert len(set(keys))==7200
 for g in inputs:
  expected={s['position']:s['fingerprint'] for s in rows(ROOT/('correctness-A-'+g+'.log')) if s['kind']=='correctness'}
  for s in samples:
   if s['graph']==g and s['condition']!='D':assert s['fingerprint']==expected[s['position']] and not any(s['profile_calls'])
  for c in CONDITIONS:
   group=[s for s in samples if s['graph']==g and s['condition']==c];assert collections.Counter(s['position'] for s in group)=={i:60 for i in range(10)}
   for i in range(10):
    subset=[s for s in group if s['position']==i];assert len({s['fingerprint'] for s in subset})==1
    if c!='D':
     compare=[s['work'] for s in samples if s['graph']==g and s['position']==i and s['condition']!='D'];assert all(w==compare[0] for w in compare)
 return samples,headers

def analyze():
 samples,headers=collect();graphs=list(read(ROOT/'input-identities.json')['inputs']);summary={};tails={};rng=random.Random(20261112)
 for graph in graphs:
  groups={c:[s for s in samples if s['graph']==graph and s['condition']==c] for c in CONDITIONS}
  stats={c:{'sample_count':600,**{m:q([s[m] for s in group]) for m in METRICS},'off_upper_aperture_ns':q([s['off_upper_aperture_ns'] for s in group]),'negative_off_count':sum(s['off_estimate_ns']<0 for s in group),'cpu_outside_envelope_count':sum(s['off_upper_aperture_ns']<0 for s in group),'start_aperture_ns':q([s['start_aperture_ns'] for s in group]),'end_aperture_ns':q([s['end_aperture_ns'] for s in group]),'cpu_to_wall_ratio':q([s['cpu_ns']/s['wall_ns'] for s in group])} for c,group in groups.items()}
  per_source={str(i):{c:{m:q([s[m] for s in group if s['position']==i]) for m in METRICS} for c,group in groups.items()} for i in range(10)}
  per_block={str(b):{c:{m:q([s[m] for s in group if s['block']==b]) for m in METRICS} for c,group in groups.items()} for b in range(12)}
  paired={}
  bootstrap={a+'_over_'+b:{m:{p:[] for p in ['p50','p95','p99']} for m in METRICS} for a,b in PAIRS}
  blocks={c:{m:[[s[m] for s in group if s['block']==b] for b in range(12)] for m in METRICS} for c,group in groups.items()}
  for _ in range(10000):
   choices=[rng.randrange(12) for _ in range(12)];result={c:{m:q([value for b in choices for value in blocks[c][m][b]]) for m in METRICS} for c in CONDITIONS}
   for a,b in PAIRS:
    for m in METRICS:
     for p in ['p50','p95','p99']:bootstrap[a+'_over_'+b][m][p].append(result[a][m][p]-result[b][m][p] if m=='off_estimate_ns' else result[a][m][p]/result[b][m][p])
  for a,b in PAIRS:
   key=a+'_over_'+b;effects={m:{p:(stats[a][m][p]-stats[b][m][p] if m=='off_estimate_ns' else stats[a][m][p]/stats[b][m][p]) for p in ['p50','p95','p99']} for m in METRICS}
   intervals={m:{p:[sorted(values)[249],sorted(values)[9749]] for p,values in points.items()} for m,points in bootstrap[key].items()}
   index={(s['block'],s['position'],s['repeat']):s for s in groups[b]}
   paired[key]={'pooled_effects':effects,'block_resampling_95pct':intervals,'paired_query_ratio_median':{m:statistics.median(s[m]/index[s['block'],s['position'],s['repeat']][m] for s in groups[a]) for m in ['wall_ns','cpu_ns']},'block_p50_ratios':{m:[per_block[str(k)][a][m]['p50']/per_block[str(k)][b][m]['p50'] for k in range(12)] for m in ['wall_ns','cpu_ns']}}
  classes={}
  for c,group in groups.items():
   events=[]
   for s in group:
    ref=per_source[str(s['position'])]['A1'];flags={'wall_above_A1_source_p95':s['wall_ns']>ref['wall_ns']['p95'],'cpu_above_A1_source_p95':s['cpu_ns']>ref['cpu_ns']['p95'],'off_above_A1_source_p95':s['off_estimate_ns']>ref['off_estimate_ns']['p95']}
    if flags['wall_above_A1_source_p95']:events.append({**s,**flags})
   classes[c]={'wall_reference_exceedances':len(events),'wall_and_cpu_exceedances':sum(s['cpu_above_A1_source_p95'] for s in events),'wall_without_cpu_exceedance':sum(not s['cpu_above_A1_source_p95'] for s in events),'elevated_off_among_wall_exceedances':sum(s['off_above_A1_source_p95'] for s in events),'by_block':dict(collections.Counter(s['block'] for s in events)),'by_source':dict(collections.Counter(s['position'] for s in events)),'events':events}
  tails[graph]={'source_quantiles':per_source,'block_quantiles':per_block,'A1_source_p95_reference':classes,'top20_wall':{c:sorted(group,key=lambda s:s['wall_ns'],reverse=True)[:20] for c,group in groups.items()},'order_slot_quantiles':{c:{str(slot):{m:q([s[m] for s in group if s['order_slot']==slot]) for m in METRICS} for slot in range(4)} for c,group in groups.items()},'warning':'Per-source p99 at n60 is the observed maximum; block p99 at n50 is also the maximum. No tail events excluded.'}
  summary[graph]={'conditions':stats,'comparisons':paired};print('Analyzed',graph,flush=True)
 put('primary-summary.json',{'graphs':summary,'observations':7200,'interval_scope':'Exploratory paired block bootstrap; only12 blocks/one host; off effects are differences in ns, others ratios; no confirmatory guarantee'})
 put('tail-source-block-data.json',{'graphs':tails})
 with (ROOT/'raw-wall-cpu-observations.jsonl').open('x') as f:
  import json
  for s in samples:f.write(json.dumps(s)+'\n')
 put('primary-quality.json',{'observations':7200,'processes':len(headers),'negative_off_estimates':sum(s['off_estimate_ns']<0 for s in samples),'cpu_outside_envelope':sum(s['off_upper_aperture_ns']<0 for s in samples),'clock_failures':0,'primary_exclusions':[],'profile_calls_zero':True,'BMSSP_fingerprints_and_work_identical':True,'headers':headers})

if __name__=='__main__':analyze()
