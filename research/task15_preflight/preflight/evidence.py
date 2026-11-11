"""Anchored inventory plus independent semantic reconciliation of original Phase7 records."""
import json
import math
from pathlib import Path
import re
import struct
from .core import require,read,sha,canonical,road_marks,boundary,ROAD_MARKS
from production_adapter.graphs import frozen_graph
from production_adapter.artifacts import verify_artifact
from roadcheck.inputs import REGIONS,COUNTS,selection
from roadcheck.validation import check_path
from smoke.contract import safe_diagnostics
from task15_harness.output import read_bundle

INDEX_SHA='b2127c4339feead02e4af97be7559eaa82d3ab292620547e75e20bbae839306a'
CAMPAIGN_SHA='67f6b619e3142401254903ce6ee95c5be9bc1624c9e81b99430d993a47e9a02c'
REGRESSION_MARKERS={'runner-final':'76bcc2ef44fbdc3bac7de346d6513f24c2d7f34d4689043c8b26f4f5363a073d','harness-final':'ede956c7f0ac079cb3ecf12092184c0e89e8d825b118a9367764ca86f8c8dc4b'}
PHASE7_COMMIT='9b267fb0986ea099b4f3464c93f8587dd1bf10fd'
DEPS={'/usr/lib/libc++.1.dylib':'5013c0f884a93b569febc353816a750f','/usr/lib/libSystem.B.dylib':'d65e4112c1513ff8beb74841436012d6'}


def inventory(root,marker,key,*,closed):
    require(not root.is_symlink(),'EVIDENCE_ROOT_REDIRECT')
    value=read(root/marker);items=value[key];require(type(items) is dict and items,'EMPTY_INVENTORY')
    inodes=set()
    for name,wanted in items.items():
        require(type(name) is str and Path(name).name==name and name not in {'.','..',marker},'UNSAFE_INVENTORY_PATH')
        path=root/name;require(path.is_file() and not path.is_symlink(),'MISSING_OR_REDIRECTED_PAYLOAD:'+name)
        st=path.stat();require((st.st_dev,st.st_ino) not in inodes,'ALIASED_PAYLOAD');inodes.add((st.st_dev,st.st_ino))
        require(sha(path.read_bytes())==wanted,'PAYLOAD_HASH:'+name)
    if closed:require({p.name for p in root.iterdir()}==set(items)|{marker},'UNLISTED_PAYLOAD')
    return value


def dependencies(value):
    require(set(value)==set(DEPS),'DEPENDENCY_SET')
    for name,uuid in DEPS.items():
        d=value[name]
        require(d['loaded_path']==d['install_name']==name and d['architecture']=='arm64' and d['loaded_uuid']==uuid,'LOADED_DEPENDENCY_IDENTITY')
        require(d['file_sha256'] is None,'FABRICATED_DEPENDENCY_HASH')


def reconcile(root,p):
    """Semantic validation also used on disposable resealed negative fixtures."""
    root=Path(root);campaign=read(root/'campaign.json');summary=read(root/'summary.json');started=read(root/'STARTED.json')
    for value in [campaign,summary,started]:road_marks(value)
    require(campaign['protocol_sha256']==started['protocol_sha256']==p['identity']['sha256'],'PROTOCOL_IDENTITY')
    require(campaign['native_order']==['baseline','candidate'] and campaign['region_order']==list(REGIONS) and campaign['source_policy']=='ORIGINAL_POSITION_ZERO_ONLY','FIXED_SOURCE_POLICY')
    require(started['maximum_bmssp_solves']==6 and started['maximum_road_oracle_queries']==3,'BOUNDED_BUDGET')
    require(summary['status']=='PASS' and summary['error'] is None and summary['retries']==0 and summary['performance_collection'] is False and summary['production_gate_changed'] is False,'CAMPAIGN_FAILURE_OR_RETRY')
    graphs={};oracles={};selections={};comparisons=0;paths=0;query_records=[];prior_work={}
    for index,region in enumerate(REGIONS):
        graph=frozen_graph(p['inputs'][region]);require((len(graph.vertices),len(graph.edges))==COUNTS[index],'GRAPH_DIMENSIONS')
        chosen=selection(p,region);selections[region]=chosen;graphs[region]=graph
        attempt=read(root/(region+'.oracle-attempt.json'));road_marks(attempt)
        require(attempt['selection']==chosen and attempt['oracle_attempt']==index+1,'ORACLE_ATTEMPT_POLICY')
        data=(root/(region+'.oracle.json')).read_bytes();require(sha(data)==campaign['oracle_files'][region],'ORACLE_FILE_HASH')
        oracle=read(root/(region+'.oracle.json'));road_marks(oracle)
        require(oracle['selection']==chosen and oracle['vertices']==list(graph.vertices) and (oracle['vertex_count'],oracle['edge_count'])==COUNTS[index],'ORACLE_GRAPH_SOURCE')
        require(oracle['frozen_artifact_hashes']=={k:p['inputs'][region][k] for k in ('graph_sha256','native_export_sha256','fixture_manifest_sha256','query_file_sha256')},'ORACLE_ARTIFACT_IDENTITY')
        raw=oracle['distances_le_hex'];require(len(raw)==len(graph.vertices) and all(type(v) is str and re.fullmatch('[0-9a-f]{16}',v) for v in raw),'ORACLE_BINARY64_VECTOR')
        require(sha(bytes.fromhex(''.join(raw)))==oracle['distance_sha256'],'ORACLE_FINGERPRINT')
        distances=[struct.unpack('<d',bytes.fromhex(v))[0] for v in raw]
        require(all(not math.isnan(v) and v>=0 for v in distances) and raw[graph.vertices.index(chosen['source_id'])]=='0000000000000000','ORACLE_DISTANCE_VALUES')
        oracles[region]=(oracle,distances)
    require(set(campaign['oracle_files'])==set(REGIONS),'ORACLE_INVENTORY')
    exits=[]
    for variant in ['baseline','candidate']:
        identity=verify_artifact(p,variant,p['binaries'][variant]['path'])
        require(campaign['binaries'][variant]==started['binaries'][variant]==identity,'BINARY_IDENTITY')
        lines=(root/(variant+'.events.jsonl')).read_bytes().splitlines();events=[]
        from .core import pairs
        for line in lines:
            e=json.loads(line,object_pairs_hook=pairs);canonical(e);road_marks(e);events.append(e)
        require([e['event'] for e in events]==['IMPORT_VERIFIED']+['GRAPH_PREPARED','SOLVE_ATTEMPT','QUERY_VERIFIED']*3,'DUPLICATED_OR_INCOMPLETE_QUERY_JOURNAL')
        imported=events[0];require(imported['binary_preimport_identity']==identity and imported['loaded_module_path']==identity['path'],'LOADED_EXTENSION_IDENTITY')
        dependencies(imported['dependencies'])
        pid=imported['pid'];require(type(pid) is int and pid>0,'CHILD_PID')
        for e in events:require(e['pid']==pid and e['variant']==variant,'EVENT_PROCESS_BINDING')
        for index,region in enumerate(REGIONS):
            prepared,attempt,result=events[1+3*index:4+3*index];chosen=selections[region]
            require(prepared['selection']==attempt['selection']==chosen and attempt['attempt']==index+1,'NATIVE_SOURCE_ORDER')
            require(prepared['metadata_without_timing']['preprocessing_count']==1,'PREPROCESSING')
            proof=result['evidence'];oracle,distances=oracles[region];graph=graphs[region]
            require(proof['selection']==chosen and proof['oracle_sha256']==proof['native_sha256']==oracle['distance_sha256'],'NATIVE_ORACLE_FINGERPRINT')
            require(proof['valid'] is True and proof['errors']==[] and proof['distance_mismatches']==[] and proof['first_differing_vertex'] is None,'NATIVE_DISTANCE_MISMATCH')
            require(proof['native_reachable']==proof['oracle_reachable']==sum(math.isfinite(v) for v in distances),'REACHABILITY')
            d=proof['diagnostics_without_timing'];safe_diagnostics(json.loads(canonical(d)))
            if region in prior_work:require(prior_work[region]==d,'VARIANT_WORK_MISMATCH')
            prior_work[region]=d
            require(len(proof['paths'])==4 and [v['target'] for v in proof['paths']]==chosen['path_targets'],'PATH_TARGET_INVENTORY')
            for path in proof['paths']:
                require(path['valid'] is True,'INCORRECT_PATH_ACCEPTANCE')
                rawpath={'reachable':path['reachable'],'distance':struct.unpack('<d',bytes.fromhex(path['distance_le_hex']))[0],'vertices':path['vertices'],'edges':path['edges']}
                check_path(rawpath,chosen['source_id'],path['target'],graph,distances,distances);paths+=1
            for name in ['result_release','engine_release','graph_release']:
                r=result[name];require(r['python_reference_dropped'] is True and r['weakref_supported'] is True and r['weakref_dead'] is True,'RESULT_LIFETIME')
            comparisons+=len(graph.vertices);query_records.append({'variant':variant,'selection':chosen,'distance_sha256':proof['native_sha256']})
        receipt=read(root/(variant+'.receipt.json'));exit_record=read(root/(variant+'.exit.json'))
        for obj in [receipt,exit_record]:road_marks(obj)
        require(receipt['status']=='PASS' and receipt['variant']==variant and receipt['pid']==pid and receipt['query_attempts']==3 and receipt['binary_preimport_identity']==identity and receipt['dependencies']==imported['dependencies'],'CHILD_RECEIPT')
        require(exit_record['receipt']==receipt and exit_record['variant']==variant and exit_record['pid']==pid and exit_record['exit_code']==0 and exit_record['process_reaped'] is True and exit_record['timeout'] is False and exit_record['recorded_attempts']==3,'CHILD_EXIT')
        require((root/(variant+'.stdout')).read_bytes()==(root/(variant+'.stderr')).read_bytes()==b'','UNEXPECTED_NATIVE_OUTPUT')
        claim=read(root/(variant+'.child-claimed.json'));launch=read(root/(variant+'.launch.json'))
        require(claim['pid']==pid and claim['variant']==launch['variant']==variant and launch['launch_claimed_once'] is True,'CHILD_LAUNCH_CLAIM')
        exits.append(exit_record)
    require(exits[0]['pid']!=exits[1]['pid'],'VARIANT_PROCESS_ALIAS')
    require(summary['outcomes']==[{k:v for k,v in e.items() if k not in ROAD_MARKS} for e in exits] and summary['oracle_attempts']==len(REGIONS)==3 and summary['native_attempts']==len(query_records)==6,'QUERY_COUNT_RECONCILIATION')
    require(comparisons==80068 and paths==24,'DIMENSION_RECONCILIATION')
    for region in REGIONS:
        require(summary['agreement'][region]=={'distance_sha256':oracles[region][0]['distance_sha256'],'exact_distance_agreement':True,'identical_path_sequence_required':False,'work_agreement':True},'AGREEMENT_SUMMARY')
    return {'status':'VERIFIED','native_queries':len(query_records),'independent_road_oracles':len(oracles),'recorded_full_vector_comparisons':comparisons,'paths_revalidated':paths,'binary64_mismatches':0,'queries':query_records,
            'limitation':'Native full vectors were not retained in Phase7; validates anchored native comparison receipts/fingerprints against stored complete independent oracle vectors; no native or oracle rerun.'}


def verify(root,protocol):
    root=Path(root).absolute();require(root.is_dir() and not root.is_symlink(),'PHASE7_ROOT')
    require(sha((root/'audit-index.json').read_bytes())==INDEX_SHA,'PHASE7_TRUST_ANCHOR')
    inventory(root,'audit-index.json','files',closed=False)
    require(sha((root/'campaign/COMPLETED.json').read_bytes())==CAMPAIGN_SHA,'PHASE7_CAMPAIGN_ANCHOR')
    marker=inventory(root/'campaign','COMPLETED.json','files',closed=True);road_marks(marker);require(marker['status']=='PASS','INCOMPLETE_CAMPAIGN')
    result=reconcile(root/'campaign',protocol.data())
    delivery=read(root/'delivery.json');require(delivery['commit']==delivery['remote_commit']==PHASE7_COMMIT and delivery['verdict']=='PASS','PHASE7_DELIVERY')
    for file,count in [('closure.log',3),('adapter-final.log',35),('runner-final.log',32),('harness-final.log',107),('smoke-fake-final.log',22),('road-fake-final.log',17)]:
        text=(root/file).read_text();require(re.search(r'Ran '+str(count)+r' tests? in [0-9.]+s\n\nOK\s*$',text) is not None,'REGRESSION_ACCEPTANCE:'+file)
    for folder,count in [('runner-final',32),('harness-final',107)]:
        require(sha((root/folder/'COMPLETED.json').read_bytes())==REGRESSION_MARKERS[folder],'REGRESSION_COMPLETION_ANCHOR')
        read_bundle(root/folder,expected_payloads={'tests.json','tests.log'})
        tests=read(root/folder/'tests.json');require(tests['tests_run']==count and tests['successful'] is True and tests['failures']==tests['errors']==tests['skipped']==0,'REGRESSION_COUNTS')
    for filename,key in [('before.json','files'),('implementation-source-before-campaign.json','files')]:
        for name,wanted in read(root/filename)[key].items():
            path=protocol.repository/name;require(not Path(name).is_absolute() and '..' not in Path(name).parts,'SOURCE_PATH')
            require(path.is_file() and not path.is_symlink() and sha(path.read_bytes())==wanted,'STALE_SOURCE_LOCK:'+name)
    result.update({'audit_index_sha256':INDEX_SHA,'campaign_completion_sha256':CAMPAIGN_SHA,'phase7_commit':PHASE7_COMMIT,'regressions_verified':{'deferred':3,'adapter':35,'runner':32,'harness':107,'phase6_fake':22,'phase7_fake':17}})
    return result
