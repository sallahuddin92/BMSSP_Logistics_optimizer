"""Retain and attribute observed tail locations, without deleting or excusing them."""
import json,pathlib,statistics,sys,collections
from experiment import rows,quantiles
root=pathlib.Path(sys.argv[1]);plan=json.loads((root/'measurement-plan.json').read_text())['conditions'];data=[];invocations={x['name']:x for x in rows(root/'invocations.jsonl') if x['name'].startswith('matrix-')}
for p in plan:
 name=f"matrix-b{p['block']:02d}-{p['graph']}-{p['variant']}-{p['algorithm']}"
 for r in rows(root/(name+'.jsonl')):
  if r['kind']=='sample':data.append({**p,**r,'invocation':name,'host_before':invocations[name]['host_before']})
report={}
for graph in dict.fromkeys(p['graph'] for p in plan):
 groups={(v,a):[r for r in data if (r['graph'],r['variant'],r['algorithm'])==(graph,v,a)] for v in ['baseline','candidate'] for a in ['bmssp','dijkstra']};base=quantiles([r['seconds'] for r in groups['baseline','bmssp']]);candidate=groups['candidate','bmssp'];excess=[r for r in candidate if r['seconds']>base['p99']];per_block=[]
 for b in range(10):
  q={k:quantiles([r['seconds'] for r in group if r['block']==b]) for k,group in groups.items()}
  per_block.append({'block':b,'bmssp_candidate_base':{p:q['candidate','bmssp'][p]/q['baseline','bmssp'][p] for p in ['p50','p95','p99']},'dijkstra_candidate_base':{p:q['candidate','dijkstra'][p]/q['baseline','dijkstra'][p] for p in ['p50','p95','p99']}})
 report[graph]={'candidate_over_baseline_p99_count':len(excess),'candidate_excess_by_block':dict(collections.Counter(r['block'] for r in excess)),'candidate_excess_by_source_position':dict(collections.Counter(r['position'] for r in excess)),'top20_each_variant':{v:sorted(groups[v,'bmssp'],key=lambda r:r['seconds'],reverse=True)[:20] for v in ['baseline','candidate']},'per_block':per_block,'per_source_p99_ratios':{str(i):quantiles([r['seconds'] for r in candidate if r['position']==i])['p99']/quantiles([r['seconds'] for r in groups['baseline','bmssp'] if r['position']==i])['p99'] for i in range(10)},'finding':'All samples retained. Equal work counters rule out different recorded logical workload, not CPU/cache/scheduling effects. Wall samples and coarse load averages cannot establish a causal explanation for tail changes. No environment-based exclusions.'}
(root/'tail-investigation.json').write_text(json.dumps(report,indent=2))
for graph,r in report.items():print(graph,'excess',r['candidate_over_baseline_p99_count'],'byblock',r['candidate_excess_by_block'],'bysource',r['candidate_excess_by_source_position'],'top',[(x['block'],x['position'],round(x['seconds']*1000,3)) for x in r['top20_each_variant']['candidate'][:8]])
