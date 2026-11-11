"""Summarize sample's stored call-tree counts; do not treat them as wall time."""
import json,pathlib,re,sys
root=pathlib.Path(sys.argv[1]);report={}
for name in ['seremban-small','seremban-medium','seremban-port-dickson']:
 text=(root/('sample-baseline-'+name+'.txt')).read_text();tree=text.split('Call graph:')[1].split('Total number in stack')[0].split('Sort by top of stack')[0];nodes=[];stack=[]
 for line in tree.splitlines():
  m=re.match(r'^([ +!|:]*)(\d+) (.*?)  \(in ([^)]+)\)',line)
  if not m:continue
  depth=len(m[1]);node={'depth':depth,'count':int(m[2]),'name':m[3],'image':m[4],'children':[]}
  while stack and stack[-1]['depth']>=depth:stack.pop()
  if stack:stack[-1]['children'].append(node)
  node['insert_ancestor']=any('BoundedFrontier::insert(' in n['name'] for n in stack)
  nodes.append(node);stack.append(node)
 for n in nodes:n['exclusive']=n['count']-sum(c['count'] for c in n['children'])
 total=next(n['count'] for n in nodes if n['name']=='start');assert all(n['exclusive']>=0 for n in nodes)
 insert=sum(n['count'] for n in nodes if 'BoundedFrontier::insert(' in n['name']);alloc=sum(n['exclusive'] for n in nodes if n['image']=='libsystem_malloc.dylib' or 'operator new' in n['name'] or 'operator delete' in n['name']);insertalloc=sum(n['exclusive'] for n in nodes if n['insert_ancestor'] and (n['image']=='libsystem_malloc.dylib' or 'operator new' in n['name'] or 'operator delete' in n['name']));comparison=sum(n['exclusive'] for n in nodes if 'SymbolicLabel::compare_nodes(' in n['name'])
 report[name]={'samples':total,'insert_inclusive_samples':insert,'insert_inclusive_fraction':insert/total,'allocator_exclusive_samples':alloc,'allocator_exclusive_fraction':alloc/total,'allocator_inside_insert_samples':insertalloc,'comparison_exclusive_samples':comparison,'comparison_exclusive_fraction':comparison/total,'unaccounted_or_double_counted_samples':total-sum(n['exclusive'] for n in nodes),'source':'sample-baseline-'+name+'.txt','interpretation':'Allocator image/new-delete exclusive samples are a lower bound; allocator calls into other images are excluded. Insert inclusive includes comparison, splitting and allocation, not solely the temporary vector.'}
(root/'bottleneck-attribution.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
