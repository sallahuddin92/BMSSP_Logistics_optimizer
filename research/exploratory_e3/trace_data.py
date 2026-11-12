"""Actual xctrace XML references, clock brackets and target-thread state joins."""
import collections,json,math,pathlib,re,xml.etree.ElementTree as ET
def table(path):
 tree=ET.parse(path);refs={e.attrib['id']:e for e in tree.iter() if 'id' in e.attrib}
 def resolve(e):
  visited=set()
  while 'ref' in e.attrib:
   key=e.attrib['ref'];assert key not in visited;visited.add(key);e=refs[key]
  return e
 def value(e):
  e=resolve(e)
  if e.tag=='sentinel':return None
  if e.tag=='thread':
   child=e.find('tid');return None if child is None else int(value(child))
  if e.tag=='process':
   child=e.find('pid');return None if child is None else int(value(child))
  return e.text if e.text is not None else e.attrib.get('fmt')
 output=[];schemas=[];prior_schema=None
 for node in tree.findall('./node'):
  schema=node.find('schema')
  if schema is None:schema=prior_schema
  assert schema is not None;prior_schema=schema;cols=[c.findtext('mnemonic') for c in schema.findall('col')];schemas.append({'name':schema.attrib['name'],'columns':cols,'engineering_types':[c.findtext('engineering-type') for c in schema.findall('col')]})
  for number,row in enumerate(node.findall('row')):
   children=list(row);assert len(children)==len(cols)
   data={k:value(v) for k,v in zip(cols,children)}
   data['_row']=number;data['_node']=node.attrib.get('xpath');data['_schema']=schema.attrib['name'];data['_elements']={k:ET.tostring(resolve(v),encoding='unicode') for k,v in zip(cols,children)}
   output.append(data)
 return output,schemas

def metadata(row):
 text=row.get('message') or row.get('metadata') or row.get('arguments') or ''
 # The exported mnemonic may differ: inspect actual engineering type element.
 if not text:
  for key,xml in row['_elements'].items():
   e=ET.fromstring(xml)
   if e.tag=='os-log-metadata':text=e.attrib.get('fmt','');break
 return text
def signpost_fields(row):
 vals={}
 for key,xml in row['_elements'].items():
  e=ET.fromstring(xml)
  if e.tag=='os-signpost-identifier':vals['signpost_id']=int(e.text)
  if e.tag=='signpost-name':vals['name']=e.text
  if e.tag=='event-type':vals['event']=e.text
  if e.tag=='event-time':vals['time']=int(e.text)
 vals['metadata']=metadata(row)
 return vals
def mapping(anchors,events):
 relevant=[]
 for a in anchors:
  matches=[]
  for row in events:
   if row.get('thread')!=a['thread_id'] or row.get('process')!=a['pid']:continue
   v=signpost_fields(row)
   if v.get('name')!='E3ClockAnchor':continue
   m=re.search(r'anchor=\s*(\d+)',v['metadata'])
   if m and int(m[1])==a['anchor_id']:matches.append(v)
  matches=list({(v['time'],v['signpost_id'],v['metadata']):v for v in matches}.values())
  assert len(matches)==1,('anchor missing/ambiguous after identical-view deduplication',a['anchor_id'])
  relevant.append({**a,'trace_ns':matches[0]['time']})
 relevant.sort(key=lambda a:a['raw_before_ns']);assert len(relevant)>=2
 x0=relevant[0]['raw_before_ns'];low=0.;high=float('inf')
 for i,a in enumerate(relevant):
  for b in relevant[i+1:]:
   dt=b['trace_ns']-a['trace_ns'];assert dt>0
   lower_den=b['raw_after_ns']-a['raw_before_ns'];upper_den=b['raw_before_ns']-a['raw_after_ns']
   if upper_den>0:low=max(low,dt/lower_den);high=min(high,dt/upper_den)
 assert 0<low<=high<2,('no feasible clock rate',low,high)
 slope=1. if low<=1<=high else (low+high)/2
 def offsets(s):return max(a['trace_ns']-s*(a['raw_after_ns']-x0) for a in relevant),min(a['trace_ns']-s*(a['raw_before_ns']-x0) for a in relevant)
 lo,hi=offsets(slope)
 if lo>hi:
  slope=(low+high)/2;lo,hi=offsets(slope)
 assert lo<=hi,('no affine mapping',lo,hi)
 # Conservative envelope over feasible rate range; no UTC join or equal-clock assumption.
 offset_min=min(a['trace_ns']-s*(a['raw_after_ns']-x0) for a in relevant for s in [low,high])
 offset_max=max(a['trace_ns']-s*(a['raw_before_ns']-x0) for a in relevant for s in [low,high])
 return {'raw_origin_ns':x0,'slope':slope,'offset_ns':(lo+hi)/2,'offset_interval_at_chosen_rate':[lo,hi],'rate_interval':[low,high],'conservative_offset_interval':[offset_min,offset_max],'anchors':relevant,'method':'Trace anchor event matched by PID/TID/anchor ID inside independently read RAW brackets; positive affine rate constrained by every anchor pair. No UTC-only or assumed identical timebase join.'}
def mapped(m,raw):
 return m['slope']*(raw-m['raw_origin_ns'])+m['offset_ns']
def bounds(m,raw):
 x=raw-m['raw_origin_ns'];a,b=m['rate_interval'];lo,hi=m['conservative_offset_interval'];return [min(a*x,b*x)+lo,max(a*x,b*x)+hi]
def overlap_states(states,pid,tid,start,end):
 target=[s for s in states if s.get('thread')==tid and s.get('process')==pid];durations=collections.Counter();cores=[];evidence=[]
 for s in target:
  a=int(s['start']);b=a+int(s['duration']);overlap=max(0,min(end,b)-max(start,a))
  if not overlap:continue
  durations[s['state']]+=overlap;evidence.append({'export_node':s['_node'],'row':s['_row'],'start_ns':a,'duration_ns':b-a,'overlap_ns':overlap,'state':s['state'],'core':s.get('core'),'summary':s.get('summary')})
  if s['state']=='Running' and s.get('core') is not None:cores.append((a,int(s['core'])))
 ordered=[c for _,c in sorted(cores)];migrations=sum(a!=b for a,b in zip(ordered,ordered[1:]))
 return {'state_ns':dict(durations),'state_coverage_fraction':sum(durations.values())/(end-start),'observed_running_core_ids':sorted(set(ordered)),'observed_core_transitions':migrations,'records':evidence,'loss_counter':None,'loss_reason':'No explicit lost-event counter established from this schema; interval coverage reported separately. Interrupted/Preempted kept distinct, never silently added to Runnable/Blocked.'}
