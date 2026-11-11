"""Report separate instrumentation effects and supported sampling evidence."""
import collections,math,statistics,re
from campaign import ROOT,read,rows,put,LABEL
from quality import q

def summarize():
 primary=read(ROOT/'primary-summary.json')['graphs'];inputs=read(ROOT/'input-identities.json')['inputs'];allocation={};profiles={};endpoints={}
 for graph in inputs:
  paired={}
  for v in ['A','B']:
   data=[];footers=[];headers=[]
   for replicate in range(2):
    r=rows(ROOT/f'allocator-{replicate}-{graph}-{v}.log');headers.append(r[0]);footers.append(r[-1]);group=[x for x in r if x['kind']=='allocator_query'];assert len(group)==30
    data.extend({**x,'replicate':replicate} for x in group)
   assert all(x['table_overflow']==x['unknown_frees']==x['double_live']==0 for x in data)
   assert all(x['tracked_live_after_result_destroy']==0 for x in data)
   c='A1' if v=='A' else 'B'
   paired[v]=data
   allocation.setdefault(graph,{})[v]={'queries':60,'median_allocations':statistics.median(x['allocations'] for x in data),'median_requested_bytes':statistics.median(x['requested_bytes'] for x in data),'median_insertion_32byte_allocations':statistics.median(x['insert_32_allocations'] for x in data),'median_same_insertion_32byte_frees':statistics.median(x['insert_32_same_scope_frees'] for x in data),'address_reuse_fraction':q([x['reused_addresses']/x['allocations'] for x in data]),'rss_after_destroy':q([x['rss_destroy'] for x in data]),'tracked_cpp_live_on_return':q([x['tracked_live_on_return'] for x in data]),'tracked_live_after_destroy_max':max(x['tracked_live_after_result_destroy'] for x in data),'buffer_bytes':headers[0]['static_buffer_bytes'],'event_records':sum(x['event_records'] for x in footers),'event_records_not_retained':sum(x['event_records_not_retained'] for x in footers),'table_overflow':0,'unknown_frees':0,'instrumented_wall_p50_over_primary_wall_p50':q([x['wall_ns'] for x in data])['p50']/primary[graph]['conditions'][c]['wall_ns']['p50'],'histograms':{key:[sum(x[key][i] for x in data) for i in range(32)] for key in ['allocation_size_pow2_upper_bins','insert_size_pow2_upper_bins','lifetime_in_observed_events_pow2_upper_bins']},'phase_deallocations':[sum(x['phase_deallocations'][i] for x in data) for i in range(3)]}
  index={(x['replicate'],x['position'],x['repeat']):x for x in paired['A']};differences=[]
  for b in paired['B']:
   a=index[b['replicate'],b['position'],b['repeat']];assert a['work']==b['work'];calls=a['allocations']-b['allocations'];bytes_=a['requested_bytes']-b['requested_bytes'];assert calls>0 and bytes_==calls*32
   assert a['insert_32_allocations']-b['insert_32_allocations']==calls
   differences.append({'position':a['position'],'replicate':a['replicate'],'repeat':a['repeat'],'allocation_calls_saved':calls,'requested_bytes_saved':bytes_,'fraction':calls/a['allocations']})
  allocation[graph]['paired_difference']={'queries':differences,'median_call_reduction':statistics.median(x['fraction'] for x in differences),'mechanism':'Saved ordinary new calls equal saved32-byte allocations in insertion; each had same-scope frees. This establishes temporary removal, not a cause for E1 tail regression.'}
  endpoints[graph]={}
  for c in ['A1','B']:
   groups={mode:[x for x in rows(ROOT/f'endpoint-raw-{graph}-{c}-{mode}.log') if x['kind']=='sample'] for mode in ['plain','paired']}
   assert all(len(x)==30 for x in groups.values());endpoints[graph][c]={'plain_wall_ns':q([x['wall_ns'] for x in groups['plain']]),'paired_wall_ns':q([x['wall_ns'] for x in groups['paired']]),'paired_over_plain_p50':q([x['wall_ns'] for x in groups['paired']])['p50']/q([x['wall_ns'] for x in groups['plain']])['p50'],'warning':'Separate processes,n30; not a calibrated causal overhead correction.'}
  profiles[graph]={}
  for v in ['A','B']:
   path=ROOT/f'sampling-{graph}-{v}.sample.txt'
   if not path.exists():profiles[graph][v]={'supported':False};continue
   text=path.read_text();tree=text.split('Call graph:')[1].split('Total number in stack')[0].split('Sort by top of stack')[0];nodes=[];stack=[]
   for line in tree.splitlines():
    m=re.match(r'^([ +!|:]*)(\d+) (.*?)  \(in ([^)]+)\)',line)
    if not m:continue
    node={'depth':len(m[1]),'count':int(m[2]),'name':m[3],'image':m[4],'children':[]}
    while stack and stack[-1]['depth']>=node['depth']:stack.pop()
    if stack:stack[-1]['children'].append(node)
    nodes.append(node);stack.append(node)
   for n in nodes:n['exclusive']=n['count']-sum(x['count'] for x in n['children'])
   assert all(n['exclusive']>=0 for n in nodes);total=next(n['count'] for n in nodes if n['name']=='start')
   alloc=sum(n['exclusive'] for n in nodes if n['image']=='libsystem_malloc.dylib' or 'operator new' in n['name'] or 'operator delete' in n['name'])
   profiles[graph][v]={'supported':True,'thread_samples':total,'allocator_exclusive_fraction_lower_bound':alloc/total,'comparison_exclusive_fraction':sum(n['exclusive'] for n in nodes if 'SymbolicLabel::compare_nodes(' in n['name'])/total,'insertion_inclusive_fraction':sum(n['count'] for n in nodes if 'BoundedFrontier::insert(' in n['name'])/total,'top_exclusive':sorted([{k:n[k] for k in ['name','image','exclusive']} for n in nodes],key=lambda x:x['exclusive'],reverse=True)[:20],'warning':'Exclusive allocator image samples omit calls into other images; inclusive insertion overlaps. No summation of these categories.'}
 put('allocator-summary.json',{'graphs':allocation,'coverage':'Ordinary/aligned C++ callbacks only, no full malloc/realloc/cache tracing. Event buffers truncated; aggregate callbacks and address table show no overflow. RSS includes5.375MiB static observer buffers.'})
 put('cpu-sampling-summary.json',{'graphs':profiles})
 put('endpoint-perturbation-summary.json',{'graphs':endpoints,'clock_correction':'Original quantized-clock controls retained separately, not pooled; no overhead subtraction.'})
if __name__=='__main__':summarize()
