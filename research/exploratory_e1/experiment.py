"""EXPLORATORY_BMSSP_PERFORMANCE orchestration and analysis; standard library only."""
import argparse,collections,hashlib,json,math,os,pathlib,platform,random,statistics,struct,subprocess,time,xml.etree.ElementTree as ET
LABEL='EXPLORATORY_BMSSP_PERFORMANCE'
ENV={**os.environ,'DEVELOPER_DIR':'/Library/Developer/CommandLineTools','SDKROOT':'/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'}

def digest(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  while data:=f.read(1048576):h.update(data)
 return h.hexdigest()

def rows(path):return [json.loads(s) for s in pathlib.Path(path).read_text().splitlines() if s.startswith('{')]

def command(root,name,argv):
 out=root/(name+'.jsonl');err=root/(name+'.stderr')
 if out.exists() or err.exists():raise ValueError('Refusing to overwrite '+name)
 before={'load_average':os.getloadavg(),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 start=time.monotonic()
 with out.open('xb') as f,err.open('xb') as e:r=subprocess.run(list(map(str,argv)),stdout=f,stderr=e,env=ENV)
 record={'label':LABEL,'name':name,'argv':list(map(str,argv)),'seconds':time.monotonic()-start,'exit':r.returncode,'host_before':before,'load_after':os.getloadavg(),'stdout_sha256':digest(out),'stderr_sha256':digest(err)}
 with (root/'invocations.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
 print(json.dumps(record),flush=True)
 if r.returncode:raise RuntimeError('Retained failed process '+name)
 return rows(out)

def verify_graphs(root):
 ns={'g':'http://graphml.graphdrawing.org/xmlns'};manifest=json.loads((root/'input-identities.json').read_text());report={}
 for name,v in manifest['inputs'].items():
  data=pathlib.Path(v['graph_path']).read_bytes();assert hashlib.sha256(data).hexdigest()==v['graph_sha256'];tree=ET.fromstring(data);graph=tree.find('g:graph',ns);assert graph.attrib['edgedefault']=='directed'
  keys={x.attrib['id']:x.attrib.get('attr.name') for x in tree.findall('g:key',ns)}
  vertices=sorted(int(x.attrib['id']) for x in graph.findall('g:node',ns));edges=[]
  for e in graph.findall('g:edge',ns):
   attrs={keys[x.attrib['key']]:x.text for x in e.findall('g:data',ns)};weight=float(attrs['length']);assert math.isfinite(weight) and weight>=0;edges.append((int(e.attrib['source']),int(e.attrib['target']),struct.pack('<d',weight)))
  native=pathlib.Path(v['native_export_path']);assert digest(native)==v['native_export_sha256'];lines=native.read_text().splitlines();n,m=map(int,lines[0].split());assert vertices==list(map(int,lines[1:n+1]));ne=[];eids=set()
  for line in lines[n+1:]:
   eid,u,w,weight=line.split();assert int(eid) not in eids;eids.add(int(eid));ne.append((int(u),int(w),struct.pack('<d',float(weight))))
  assert len(ne)==m==len(edges);assert collections.Counter(edges)==collections.Counter(ne);assert len(v['source_positions'])==100 and all(int(x) in vertices for x in v['source_positions'])
  report[name]={'vertices':n,'edges':m,'directed_parallel_binary64_multiset_equal':True,'source_positions':100,'native_sha256':digest(native),'graphml_sha256':v['graph_sha256']}
 (root/'graph-equivalence.json').write_text(json.dumps(report,indent=2));return report

def measure(root):
 inputs=json.loads((root/'input-identities.json').read_text())['inputs'];names=list(inputs);conditions=[('baseline','bmssp'),('candidate','bmssp'),('baseline','dijkstra'),('candidate','dijkstra')]
 plan=[]
 for block in range(10):
  for name in names[block%3:]+names[:block%3]:
   source_path=root/(f'block{block:02d}-'+name+'.sources');sources=list(enumerate(inputs[name]['source_positions'][:10]));sources=sources[block:]+sources[:block];source_path.write_text(''.join(f'{i} {s}\n' for i,s in sources))
   for variant,algorithm in (conditions if block%2==0 else list(reversed(conditions))):plan.append({'block':block,'graph':name,'variant':variant,'algorithm':algorithm,'sources':str(source_path)})
 (root/'measurement-plan.json').write_text(json.dumps({'label':LABEL,'repetitions_per_process_source':5,'warmups_per_process_source':1,'conditions':plan},indent=2))
 for p in plan:
  exe=root/('build-'+p['variant'])/'e1_native';name=f"matrix-b{p['block']:02d}-{p['graph']}-{p['variant']}-{p['algorithm']}"
  command(root,name,[exe,'bench',inputs[p['graph']]['native_export_path'],p['sources'],p['algorithm'],'5','1','unused'])

def quantiles(values):
 v=sorted(values);return {f'p{p}':v[math.ceil(len(v)*p/100)-1] for p in [50,95,99]}

def analyze(root):
 plan=json.loads((root/'measurement-plan.json').read_text())['conditions'];samples=[];headers=[];memory=[]
 for p in plan:
  stem=f"matrix-b{p['block']:02d}-{p['graph']}-{p['variant']}-{p['algorithm']}";data=rows(root/(stem+'.jsonl'));assert data[0]['kind']=='header' and data[-1]['kind']=='footer';headers.append({**p,**data[0]});memory.append({**p,**data[-1]})
  q=[r for r in data if r['kind']=='sample'];assert len(q)==50
  for row in q:
   assert row['seconds']>0 and math.isfinite(row['seconds']);samples.append({**p,**row})
 bykey={}
 for row in samples:
  key=(row['graph'],row['variant'],row['algorithm'],row['block'],row['position'],row['repeat']);assert key not in bykey;bykey[key]=row
 report={};rng=random.Random(20261112)
 for graph in dict.fromkeys(p['graph'] for p in plan):
  summary={};groups={}
  for variant in ['baseline','candidate']:
   for algorithm in ['bmssp','dijkstra']:
    subset=[r for r in samples if (r['graph'],r['variant'],r['algorithm'])==(graph,variant,algorithm)];assert len(subset)==500
    assert collections.Counter(r['position'] for r in subset)=={i:50 for i in range(10)}
    for i in range(10):assert len({r['fingerprint'] for r in subset if r['position']==i})==1
    groups[variant,algorithm]=subset;summary[variant+'_'+algorithm]={'samples':len(subset),**quantiles([r['seconds'] for r in subset]),'per_source':{str(i):quantiles([r['seconds'] for r in subset if r['position']==i]) for i in range(10)},'peak_rss_bytes':[r['peak_rss_bytes'] for r in memory if (r['graph'],r['variant'],r['algorithm'])==(graph,variant,algorithm)],'preprocessing_seconds':[h['preprocessing_seconds'] for h in headers if (h['graph'],h['variant'],h['algorithm'])==(graph,variant,algorithm)]}
  pair=[];block_ratios=[]
  for r in groups['baseline','bmssp']:
   key=(graph,'candidate','bmssp',r['block'],r['position'],r['repeat']);other=bykey[key];assert r['fingerprint']==other['fingerprint'];assert r['work']==other['work'];assert not any(r['profile_calls']) and not any(other['profile_calls']);pair.append(other['seconds']/r['seconds'])
  for b in range(10):
   a=[r['seconds'] for r in groups['baseline','bmssp'] if r['block']==b];c=[r['seconds'] for r in groups['candidate','bmssp'] if r['block']==b];block_ratios.append(statistics.median(c)/statistics.median(a))
  boot=[]
  for _ in range(10000):
   selected=[rng.randrange(10) for _ in range(10)];a=[];c=[]
   for b in selected:
    a.extend(r['seconds'] for r in groups['baseline','bmssp'] if r['block']==b);c.extend(r['seconds'] for r in groups['candidate','bmssp'] if r['block']==b)
   boot.append(quantiles(c)['p50']/quantiles(a)['p50'])
  boot.sort();summary['candidate_over_baseline']={'quantile_ratios':{p:summary['candidate_bmssp'][p]/summary['baseline_bmssp'][p] for p in ['p50','p95','p99']},'paired_sample_ratio_median':statistics.median(pair),'block_median_ratios':block_ratios,'block_bootstrap_p50_ratio_95pct':[boot[249],boot[9749]],'uncertainty':'exploratory descriptive sensitivity; only10 blocks, one host, no confirmatory inference'}
  summary['bmssp_over_dijkstra']={variant:{p:summary[variant+'_bmssp'][p]/summary[variant+'_dijkstra'][p] for p in ['p50','p95','p99']} for variant in ['baseline','candidate']}
  for variant in ['baseline','candidate']:
   paired=[r['seconds']/bykey[(graph,variant,'dijkstra',r['block'],r['position'],r['repeat'])]['seconds'] for r in groups[variant,'bmssp']]
   summary['bmssp_over_dijkstra'][variant]['paired_query_ratio_median']=statistics.median(paired)
  report[graph]=summary
 (root/'controlled-comparison.json').write_text(json.dumps({'label':LABEL,'graphs':report,'sample_count':len(samples),'definition':'p50/p95/p99 nearest rank; candidate/base <1 favors candidate; raw latencies seconds'},indent=2));return report

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['verify-graphs','measure','analyze']);ap.add_argument('--evidence',type=pathlib.Path,required=True);a=ap.parse_args()
 if a.phase=='verify-graphs':verify_graphs(a.evidence)
 elif a.phase=='measure':measure(a.evidence)
 else:analyze(a.evidence)
