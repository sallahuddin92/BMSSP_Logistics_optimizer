"""Report every retained attempt; failed recordings never become causal evidence."""
import collections,json,pathlib,statistics,subprocess,xml.etree.ElementTree as ET
from availability import ROOT,REPO,LABEL,put,sha,size
from trace_data import table,mapping,overlap_states,mapped,bounds
def readlines(path):
 return [json.loads(s) for s in pathlib.Path(path).read_text().splitlines() if s.strip()]
def write_rows(name,rows):
 with (ROOT/name).open('x') as f:
  for row in rows:f.write(json.dumps({'label':LABEL,**row})+'\n')
def med(rows,key):return statistics.median(r[key] for r in rows)
def run():
 dispatch=readlines(ROOT/'primary-dispatch.jsonl');complete=readlines(ROOT/'primary-completion.jsonl')
 all_samples=[];footers={};records={}
 for j in dispatch:
  raw=ROOT/(j['session_id']+('.queries.jsonl' if j['mode']=='on' else '.stdout'))
  rows=readlines(raw);records[j['session_id']]=rows
  footers[j['session_id']]=next((r for r in rows if r['kind']=='footer'),None)
  for line,row in enumerate(raw.read_text().splitlines(),1):
   if not row.strip():continue
   r=json.loads(row)
   if r['kind']=='sample':all_samples.append({**r,'session_id':j['session_id'],'order_slot':j['order_slot'],'raw_file':str(raw),'raw_line':line,'recording_success':j['mode']=='off'})
 assert len(all_samples)==100 and len({s['query_id'] for s in all_samples})==100
 assert all(not any(s['clock_rc']) for s in all_samples)
 write_rows('raw-wall-cpu-observations.jsonl',all_samples)
 # Only the successful availability probe has exportable scheduler evidence.
 states,state_schema=table(ROOT/'probe-thread-state.xml');events,event_schema=table(ROOT/'probe-os-signpost.xml')
 anchors=[r for r in readlines(ROOT/'probe-query-spans.jsonl') if r['kind']=='anchor']
 m=mapping(anchors,events);joins=[]
 for r in readlines(ROOT/'probe-query-spans.jsonl'):
  if r['kind']!='probe_span':continue
  start,end=mapped(m,r['wall_start_ns']),mapped(m,r['wall_end_ns'])
  joins.append({'query_id':r['query_id'],'pid':r['pid'],'thread_id':r['thread_id'],'trace_interval_ns':[start,end],'start_bounds_ns':bounds(m,r['wall_start_ns']),'end_bounds_ns':bounds(m,r['wall_end_ns']),**overlap_states(states,r['pid'],r['thread_id'],start,end)})
 put('scheduler-evidence.json',{'scope':'availability probe only; deliberate usleep is a real probe action, never road-tail blocking evidence','schemas':state_schema,'joins':joins,'primary_query_state_records':[],'primary_reason':'Recorder hit per-trace storage guard; TOC recovery exit10 Document Missing Template Error; no scheduler export exists for any road query.','wakeups':'Context-switch probe table retained separately; no primary wakeup inference.','migration_scope':'Numeric core transitions in probe only; no validated P/E topology mapping.','event_loss':'No explicit lost-event counter established. Probe state coverage is not proof of globally lossless capture.'})
 put('query-trace-synchronization.json',{'probe_mapping':m,'probe_joins':joins,'primary_query_mappings':[],'primary_synchronization_valid':False,'reason':'Primary trace is not exportable; raw/Mach endpoints alone cannot map road queries to nonexistent exported events. No UTC-only joins.'})
 schemas={}
 for f in ['probe-toc.xml','hardware-probe-toc.xml']:
  tree=ET.parse(ROOT/f);schemas[f]=sorted({e.attrib['schema'] for e in tree.iter() if 'schema' in e.attrib})
 columns={}
 for f in ['probe-thread-state.xml','probe-context-switch.xml','probe-os-signpost.xml','probe-os-signpost-arg.xml','probe-target-capability.xml']:
  _,cols=table(ROOT/f);columns[f]=cols
 put('schema-inventory.json',{'recording_tables':schemas,'actual_export_columns_and_engineering_types':columns,'time_units':'Integer start-time/event-time/duration exports in nanoseconds, verified against exported formatted timestamps; core is an integer numeric ID.','primary_TOC_export':'FAILED exit10, no primary schemas or hardware metrics claimed'})
 put('hardware-metrics.json',{'cycles':None,'retired_instructions':None,'IPC':None,'cache_TLB_events':None,'frequency':None,'hardware_bottleneck':None,'reason':'CPU Counters combined-path probe reported No counting mode selected before target launch; Processor Trace listing/service is not recording/export validation. No hardware metrics collected.','probe_capability_file':'probe-target-capability.xml','schema_presence_is_not_attributed_measurement':True})
 observer=[]
 for g in ['seremban-medium','seremban-port-dickson']:
  for c in ['A1','A2','B','D']:
   on=[r for r in all_samples if r['graph']==g and r['condition']==c and r['trace_on']]
   off=[r for r in all_samples if r['graph']==g and r['condition']==c and not r['trace_on']]
   row={'graph':g,'condition':c,'on_count':len(on),'off_count':len(off),'complete_pair':bool(on and off),'limitation':'Only first A2 on process reached worker completion; recording failed. No completed trace export. This incomplete one-block pair is descriptive, not production latency or calibrated overhead.'}
   if on and off:
    for k in ['wall_ns','cpu_ns']:
     row[k]={'on_median':med(on,k),'off_median':med(off,k),'ratio_on_off':med(on,k)/med(off,k)}
    rs=lambda a:footers[a[0]['session_id']]['peak_rss_bytes']
    row['peak_RSS_bytes']={'on':rs(on),'off':rs(off),'ratio':rs(on)/rs(off)}
    row['per_position']=[{'position':p,**{k+'_ratio':med([r for r in on if r['position']==p],k)/med([r for r in off if r['position']==p],k) for k in ['wall_ns','cpu_ns']}} for p in sorted({r['position'] for r in on})]
   observer.append(row)
 put('observer-effect.json',{'comparisons':observer,'workload_counts':{'planned_on':480,'planned_off':480,'retained_on':20,'retained_off':80},'trace_losses':None,'missing_exports':1,'overhead_subtracted':False,'instrumented_pooled_with_off':False})
 off=[r for r in all_samples if not r['trace_on']];summary={}
 for c in ['A1','A2','B','D']:
  a=[r for r in off if r['condition']==c];summary[c]={'count':len(a),'wall_median_ns':med(a,'wall_ns'),'cpu_median_ns':med(a,'cpu_ns'),'wall_max_ns':max(r['wall_ns'] for r in a),'cpu_max_ns':max(r['cpu_ns'] for r in a)}
 compare={'scope':'Incomplete first medium block only; no corridor or block2/3 primary samples. Five repeats/source, no representative p99 estimate.','trace_off':summary,'A2_A1_wall_median_ratio':summary['A2']['wall_median_ns']/summary['A1']['wall_median_ns'],'B_A1_wall_median_ratio':summary['B']['wall_median_ns']/summary['A1']['wall_median_ns'],'B_A2_wall_median_ratio':summary['B']['wall_median_ns']/summary['A2']['wall_median_ns'],'per_position':[]}
 for p in sorted({r['position'] for r in off}):
  compare['per_position'].append({'position':p,'conditions':{c:{k:med([r for r in off if r['condition']==c and r['position']==p],k) for k in ['wall_ns','cpu_ns']} for c in ['A1','A2','B','D']}})
 put('unchanged-control-comparison.json',compare)
 thresholds={(t['graph'],t['condition'],t['position']):t for t in json.loads((ROOT/'classification-plan.json').read_text())['thresholds']}
 spikes=[]
 for r in all_samples:
  t=thresholds[(r['graph'],r['condition'],r['position'])]
  if r['wall_ns']<=t['wall_ns_p95'] and r['cpu_ns']<=t['cpu_ns_p95']:continue
  controls=[a for a in all_samples if a['block']==r['block'] and a['graph']==r['graph'] and a['position']==r['position'] and a['repeat']==r['repeat'] and a['trace_on']==r['trace_on'] and a['condition']!=r['condition']]
  spikes.append({'query_id':r['query_id'],'pid':r['pid'],'thread_id':r['thread_id'],'wall_ns':r['wall_ns'],'cpu_ns':r['cpu_ns'],'off_estimate_ns':r['off_estimate_ns'],'raw_ns':r['raw_ns'],'trace_on':r['trace_on'],'reference_threshold':t,'classification':'INSUFFICIENT_EVIDENCE','supporting_scheduler_or_hardware_events':[],'trace_interval':None,'mapping':None,'reason':'No exportable synchronized road scheduler/hardware events. CPU time alone is not an instruction/cache/work causal mechanism.','available_controls':[{'query_id':a['query_id'],'condition':a['condition'],'wall_ns':a['wall_ns'],'cpu_ns':a['cpu_ns']} for a in controls],'missing_controls':'Trace-on A1/B/D were not dispatched' if r['trace_on'] else None})
 write_rows('spike-classification.jsonl',spikes)
 work_by_position={}
 for r in all_samples:
  if r['condition']=='D':continue
  work_by_position.setdefault(r['position'],set()).add(tuple(r['work']))
 assert all(len(v)==1 for v in work_by_position.values())
 # Dijkstra may choose a different equal-length predecessor; fingerprints compared within algorithm.
 fingerprints={}
 for r in all_samples:fingerprints.setdefault((r['position'],'D' if r['condition']=='D' else 'BMSSP'),set()).add(r['fingerprint'])
 assert all(len(v)==1 for v in fingerprints.values())
 put('correctness-summary.json',{'A_native_tests':19,'B_native_tests':19,'selected_source_graph_cases_per_variant':8,'road_distance_dumps_A_B_identical':all(sha(ROOT/('A-'+g+'-distances.bin'))==sha(ROOT/('B-'+g+'-distances.bin')) for g in ['seremban-medium','seremban-port-dickson']),'checks':'All-target exact binary64 distances versus native Dijkstra and reachable/unreachable directed path validation, both A/B. Existing native suite retains zero-weight and parallel-edge checks.','all_retained_worker_clock_rc_zero':True,'retained_negative_wall_minus_CPU':sum(r['off_estimate_ns']<0 for r in all_samples),'retained_CPU_exceeds_wall_envelope':sum(r['off_upper_aperture_ns']<0 for r in all_samples),'BMSSP_work_vectors_identical_A1_A2_B_on_off_by_position':True,'fingerprints_stable_within_algorithm_by_position':True,'E2_negative_estimates':4007,'E2_not_reinterpreted_as_scheduler_evidence':True})
 put('H1-assessment.json',{'assessment':'STILL_INCONCLUSIVE','promoted':False,'evidence':'Prior E2 median and allocation reductions remain historical evidence. E3 is incomplete after a storage-guard failure; no matched trace-on control suite or synchronized road events. Small first-medium-block comparisons cannot justify acceptance or rejection. No post-data acceptance threshold.','candidate_specific_mechanism_supported':False,'tail_investigation_closed':True,'next':'Return to the measured large BMSSP-versus-native-Dijkstra algorithmic bottleneck, no E4 broad tracing.'})
 failures=[r for r in readlines(ROOT/'commands.jsonl') if r['exit'] or r['limit_reason']]
 put('failures-and-unsupported.json',{'command_failures_and_usage_exits':failures,'initial_build':'Generated wrapper had literal escaped newlines and unused trace-off field. Fixed before primary, retained original failed compiler logs; native engine untouched.','empty_lines':'xctrace target stdout contains blank lines; retained and skipped by parser, not missing samples.','unsupported_metrics_file':'hardware-metrics.json','no_new_recordings_or_replacement_sessions':True})
 put('technical-verdict.json',{'verdict':'BLOCKED','scientific_verdict':'INCONCLUSIVE','implementation_status':'PARTIAL; guards stopped incomplete campaign correctly, full E3 acceptance not achieved','reason':'First traced road recording crossed predeclared per-trace storage guard and was terminated; recovery TOC failed Document Missing Template Error. Essential query-level primary scheduler/sync evidence unavailable.','attempted_sessions':5,'successful_recorder_or_off_sessions':4,'retained_off_samples':80,'retained_on_samples':20,'valid_primary_scheduler_joins':0,'planned_sessions':48,'unattempted_sessions':43,'spikes':len(spikes),'H1_assessment':'STILL_INCONCLUSIVE','tail_investigation_closed':True})
 print(json.dumps({'controls':summary,'observer':[r for r in observer if r['complete_pair']],'spikes':len(spikes),'negative':sum(r['off_estimate_ns']<0 for r in all_samples)},indent=2))
if __name__=='__main__':run()
