"""Independent static verifier for v1.2.0. Does not import the generator or harness."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

PARENT_COMMIT = '367bbdefd279c8dc6673ed03e5bdc9f57031a08f'
PARENT_HASH = '6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f'
EXPECTED_PROTOCOL_HASH = 'c41e45bccb68abdf03bab40ea793837a7f508fde17634c1aa8b358a3d82fceb0'
EXPECTED_LEDGER_HASH = '40ac6b8f91b24852f92f4e093d2acdf8434bff73e5bb32dce7fc87482edaf4f1'
HISTORICAL = {
    'docs/task15_tail_attribution_protocol.json': '081b6f2cb06e59c9a0578b78f9a007be505fef11f2302ae834d4c62dd209ed17',
    'docs/task15_tail_attribution_preregistration.md': 'c9ae85657fd94c1d51485f06a2ea6e022d848473e79969354a36ae13cc5330c5',
    'docs/task15_tail_attribution_protocol_v1.1.0.json': 'c4debb684c6bf534f9942c3776d994938577270d5c2d9cbee3224cf8be242dfe',
    'docs/task15_tail_attribution_preregistration_v1.1.0.md': '58e2bcc83724fbbf67a3b6672e1278ec1503863f2d4faec3b5462a986a9bce8c',
    'docs/task15_tail_attribution_amendment_v1.1.0.json': '8dde76dcb9669148ae47e8b9192c986d5a06821b2fdc5f2bb54914489613910f'}
HARNESS_TREE = 'ba09f98425f48ddab7c5b2596eac70ad77db3935'


class Invalid(ValueError):
    def __init__(self, code, detail=''):
        self.code = code
        super().__init__(f'{code}: {detail}')


def check(condition, code, detail=''):
    if not condition:
        raise Invalid(code, detail)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def same(a, b):
    return encoded(a) == encoded(b)  # distinguishes bool from int


def strict_read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            check(key not in result, 'JSON_DUPLICATE_KEY', key)
            result[key] = value
        return result
    def finite(token):
        number = float(token)
        check(math.isfinite(number), 'JSON_NONFINITE', token)
        return number
    def reject(token):
        raise Invalid('JSON_NONFINITE', token)
    try:
        return json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=reject, parse_float=finite)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Invalid('INPUT_JSON', str(exc)) from exc


def protocol_digest(document):
    unsigned = deepcopy(document)
    unsigned['identity'].pop('sha256')
    return digest(unsigned)


def json_differences(a, b, prefix=''):
    differences = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            pointer = prefix+'/'+key.replace('~', '~0').replace('/', '~1')
            if key not in a or key not in b:
                differences.append(pointer)
            else:
                differences += json_differences(a[key], b[key], pointer)
    elif not same(a, b):
        differences.append(prefix)
    return differences


def verify_order(document, parent):
    check(document.get('version') == '1.2.0', 'VERSION')
    check(document.get('execution_authorized') is False and document.get('promotion_authorized') is False, 'AUTHORIZATION')
    d, original = document['design'], parent['design']
    # Diagnose altered scientific assignments before checking the complete parent projection.
    if not same(d['base_schedule'], original['base_schedule']):
        old = {r['id']:r for r in original['base_schedule']}
        for row in d['base_schedule']:
            if row['id'] in old and not same(row.get('P2_pair_orders_by_region'), old[row['id']].get('P2_pair_orders_by_region')):
                raise Invalid('P2_QUERY_ORDER', row['id'])
        raise Invalid('BASE_SCHEDULE_CHANGED')
    check(same(d['diagnostic_schedule'], original['diagnostic_schedule']) and
          same(d['allocator_stack_companions'], original['allocator_stack_companions']), 'SOURCE_LANE_CHANGED')
    for array, hash_key in [('base_schedule','schedule_sha256'), ('diagnostic_schedule','diagnostic_schedule_sha256'),
                            ('allocator_stack_companions','allocator_stack_companions_sha256')]:
        check(digest(d[array]) == d[hash_key] == original[hash_key], 'SOURCE_SCHEDULE_HASH', array)
    resolved = d['resolved_diagnostic_order']
    entries, blocks = resolved['entries'], resolved['condition_blocks']
    check(resolved['rule'] == 'SESSION_END' and same(resolved['session_order'], [0,1,2,3]), 'ORDER_RULE')
    check(resolved['execution_authorized'] is False and resolved['promotion_authorized'] is False, 'AUTHORIZATION')
    sources = {}
    for lane, array, field in [('MAIN', original['diagnostic_schedule'], 'session'),
                               ('COMPANION', original['allocator_stack_companions'], 'diagnostic_session')]:
        session_indices = Counter()
        for index, row in enumerate(array):
            sources[row['id']] = (lane, index, session_indices[row[field]], row[field], row)
            session_indices[row[field]] += 1
    ids = [e['diagnostic_entry_id'] for e in entries]
    for lane in ('COMPANION', 'MAIN'):
        wanted = {key for key, value in sources.items() if value[0] == lane}
        check(all(ids.count(key) <= 1 for key in wanted), 'DUPLICATE_'+lane)
        check(wanted <= set(ids), 'MISSING_'+lane)
    check(set(ids) == set(sources) and len(entries) == 52, 'ENTRY_MEMBERSHIP')
    base = {r['id']:r for r in original['base_schedule']}
    entry_fields = {'diagnostic_session','session_key','sequence_index','lane','diagnostic_entry_id','cohort',
                    'mode','schedule_ref','schedule_ref_session','source_lane_index','source_lane_session_index',
                    'startup_order','condition','condition_order','source_condition'}
    for entry in entries:
        check(set(entry) == entry_fields, 'ENTRY_SCHEMA')
        lane, index, session_index, session, row = sources[entry['diagnostic_entry_id']]
        check(type(entry['diagnostic_session']) is int and entry['diagnostic_session'] == session, 'SESSION_ASSIGNMENT', row['id'])
        check(entry['lane'] == lane, 'LANE_ASSIGNMENT', row['id'])
        check(entry['schedule_ref'] == row['schedule_ref'] and
              entry['schedule_ref_session'] == base[row['schedule_ref']]['session'], 'SCHEDULE_REFERENCE', row['id'])
        conditions = ['trace_on_count_only'] if lane == 'COMPANION' else row['condition_order']
        check(same(entry['condition_order'], conditions), 'CONDITION_ORDER', row['id'])
        expected_values = {'session_key':f'DIAGNOSTIC/{session}', 'source_lane_index':index,
            'source_lane_session_index':session_index, 'cohort':'C' if lane == 'COMPANION' else row['cohort'],
            'mode':'allocation_stacks' if lane == 'COMPANION' else row['mode'], 'startup_order':row['variant_order'],
            'condition':'trace_on_count_only' if lane == 'COMPANION' else None,
            'source_condition':row['condition'] if lane == 'COMPANION' else None}
        check(all(same(entry[k],v) for k,v in expected_values.items()), 'ENTRY_METADATA', row['id'])
    # An independent stable sort/join over source metadata; never call generator.resolve().
    expected_ids = sorted(sources, key=lambda key: (sources[key][3], sources[key][0] == 'COMPANION', sources[key][1]))
    for session in range(4):
        actual_session = [e for e in entries if e['diagnostic_session'] == session]
        for lane in ('MAIN','COMPANION'):
            actual_ids = [e['diagnostic_entry_id'] for e in actual_session if e['lane'] == lane]
            wanted = [key for key in expected_ids if sources[key][3] == session and sources[key][0] == lane]
            check(actual_ids == wanted, lane+'_ORDER', str(session))
        check([e['sequence_index'] for e in actual_session] == list(range(len(actual_session))), 'ENTRY_SEQUENCE')
    check(ids == expected_ids, 'CROSS_LANE_ORDER')
    check(len(blocks) == 100 and len({b['unit_id'] for b in blocks}) == 100, 'UNIT_MEMBERSHIP')
    offset = Counter()
    expected_blocks = []
    for entry in entries:
        for condition_index, condition in enumerate(entry['condition_order']):
            block = {k:v for k,v in entry.items() if k not in ('condition_order','source_condition')}
            unit_id = f'C/{entry["diagnostic_entry_id"]}/stack' if entry['lane'] == 'COMPANION' else f'{entry["cohort"]}/{entry["diagnostic_entry_id"]}/{condition}'
            block.update(unit_id=unit_id, condition=condition, condition_index=condition_index,
                         entry_sequence_index=entry['sequence_index'], sequence_index=offset[entry['diagnostic_session']])
            offset[entry['diagnostic_session']] += 1
            expected_blocks.append(block)
    # Classify a reversed order even if indices and hashes were repaired by the fixture.
    check([(b['diagnostic_entry_id'],b['condition']) for b in blocks] ==
          [(b['diagnostic_entry_id'],b['condition']) for b in expected_blocks], 'CONDITION_ORDER')
    check(same(blocks, expected_blocks), 'UNIT_METADATA')
    policy = resolved['query_identity_policy']
    check(policy['namespace_protocol_sha256'] == PARENT_HASH and policy['fields'] ==
          ['namespace_protocol_sha256','session_key','unit_id','phase','region','execution_index','original_position','variant'], 'QUERY_ID_NAMESPACE')
    check(digest(resolved) == d['resolved_diagnostic_order_sha256'], 'ORDER_HASH')
    # Remove only explicit new fields; restoring allowed scalar changes must recover all parent bytes canonically.
    projected = deepcopy(document)
    for key in ('resolved_diagnostic_order','resolved_diagnostic_order_sha256'):
        del projected['design'][key]
    del projected['ordering_amendment']
    for key in ('version','identity'):
        projected[key] = deepcopy(parent[key])
    projected['design']['diagnostic_order'] = original['diagnostic_order']
    for key in ('active_protocol_file','approval_gate'):
        projected['future_execution'][key] = parent['future_execution'][key]
    check(same(projected,parent), 'SCIENTIFIC_FIELDS_CHANGED')
    check(document['ordering_amendment']['parent_commit'] == PARENT_COMMIT and
          document['ordering_amendment']['parent_canonical_sha256'] == PARENT_HASH and
          document['ordering_amendment']['approval_status'] == 'NOT_INDEPENDENTLY_APPROVED' and
          document['ordering_amendment']['new_task15_observations_used'] is False, 'AMENDMENT_PROVENANCE')
    check(protocol_digest(document) == document['identity']['sha256'] == EXPECTED_PROTOCOL_HASH, 'PROTOCOL_HASH')
    return {'diagnostic_entries':len(entries), 'diagnostic_units':len(blocks),
            'blocks_by_session':dict(sorted(Counter(b['diagnostic_session'] for b in blocks).items()))}


def static_jobs(document):
    """Structural identities only; no graph/native imports, clocks, workers or workloads."""
    d = document['design']; base = {r['id']:r for r in d['base_schedule']}
    units = []
    for session in d['sessions']:
        for cohort in session['cohort_phase_order']:
            for row in d['base_schedule']:
                if row['session'] == session['session']:
                    units.append((f'{cohort}/primary/{row["id"]}', f'PRIMARY/{row["session"]}', row, cohort, None, row['startup_order']))
    for block in d['resolved_diagnostic_order']['condition_blocks']:
        units.append((block['unit_id'], block['session_key'], base[block['schedule_ref']], block['cohort'],block['mode'],block['startup_order']))
    for unit_id, session_key, row, cohort, mode, startup in units:
        for region in row['regions']:
            inp = document['inputs'][region]
            occurrences = [inp['source_positions'][:i+1].count(source) for i,source in enumerate(inp['source_positions'])]
            def job(variant, original, execution, phase):
                query_id = digest([PARENT_HASH,session_key,unit_id,phase,region,execution,original,variant])
                return (query_id,unit_id,phase,region,execution,original,inp['source_positions'][original],occurrences[original],variant)
            startup_variants = ('baseline','candidate') if startup == 'AB' else ('candidate','baseline')
            selected = [(i,pos) for i,pos in enumerate(row['positions_by_region'][region])
                        if cohort != 'C' or pos in document['cohorts']['C']['positions_by_region'][region]]
            if row['protocol'] == 'P1':
                variants = ('baseline','candidate') if row['P1_variant_order'] == 'AB' else ('candidate','baseline')
                for variant in variants:
                    for i,pos in enumerate(inp['warmup_positions']): yield job(variant,pos,i,'warmup')
                    for i,pos in selected: yield job(variant,pos,i,'target')
            else:
                for variant in startup_variants:
                    for i,pos in enumerate(inp['warmup_positions']): yield job(variant,pos,i,'warmup')
                for i,pos in selected:
                    variants = ('baseline','candidate') if row['P2_pair_orders_by_region'][region][i] == 'AB' else ('candidate','baseline')
                    for variant in variants:
                        if mode == 'cpu_counters_cache':yield job(variant,pos,i,'untimed_hot_preparation')
                        yield job(variant,pos,i,'target')


def verify_science(document):
    rows=document['design']['base_schedule']
    check(len(rows)==64 and Counter(r['protocol'] for r in rows)=={'P1':32,'P2':32}, 'PRIMARY_COUNTS')
    check(len(document['design']['sessions']) == 8, 'PRIMARY_SESSIONS')
    for region in document['inputs']:
        position_counts=Counter();session_counts=Counter()
        for row in rows:
            if row['protocol']!='P2':continue
            positions=row['positions_by_region'][region];orders=row['P2_pair_orders_by_region'][region]
            check(sorted(positions)==list(range(100)), 'SOURCE_POSITIONS')
            check(Counter(orders)=={'AB':50,'BA':50}, 'P2_TRIAL_BALANCE')
            for pos,order in zip(positions,orders):
                position_counts[(pos,order)]+=1;session_counts[(row['session'],pos,order)]+=1
        check(all(position_counts[(p,o)]==16 for p in range(100) for o in ('AB','BA')), 'P2_POSITION_BALANCE')
        check(all(session_counts[(s,p,o)]==2 for s in range(8) for p in range(100) for o in ('AB','BA')), 'P2_SESSION_BALANCE')
    check(sum(map(len,document['cohorts']['C']['positions_by_region'].values()))==41,'C_SUBSET')
    records=list(static_jobs(document)); ids=[r[0] for r in records]
    check(len(records)==len(set(ids))==138696, 'QUERY_COUNTS')
    check(len({r[1] for r in records})==228,'UNIT_COUNTS')
    return {'primary_units':128,'total_units':228,'structural_query_records':len(records),
            'query_id_set_sha256':digest(sorted(ids)), 'logical_job_set_sha256':digest(sorted(records)),
            'P2_balance':'50/50 per trial;16/16 per original position;2/2 per position/session;all three regions'}


def verify_runtime(repo,parent):
    env={'PATH':os.defpath,'LC_ALL':'C','LANG':'C','GIT_CONFIG_NOSYSTEM':'1',
         'GIT_CONFIG_GLOBAL':os.devnull,'GIT_OPTIONAL_LOCKS':'0','GIT_TERMINAL_PROMPT':'0'}
    def git(args):
        try:
            r=subprocess.run(['git','-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null',
                              '-C',str(repo.resolve()),*args],env=env,capture_output=True,text=True,timeout=15)
        except (OSError,subprocess.TimeoutExpired) as exc:raise Invalid('GIT_METADATA',str(exc)) from exc
        check(r.returncode==0,'GIT_METADATA',r.stderr)
        return r.stdout.strip()
    protected={**parent['runtime_tree_identities'],'research/task15_harness':HARNESS_TREE}
    actual={name:git(['rev-parse','HEAD:'+name]) for name in protected}
    check(actual==protected,'PROTECTED_GIT_OBJECT')
    check(not git(['diff','--no-ext-diff','--no-textconv','HEAD','--name-only','--',*protected]),'PROTECTED_WORKTREE')
    check(not git(['ls-files','--others','--exclude-standard','--',*protected]),'PROTECTED_WORKTREE')
    return actual


def verify_files(repo,docs=None,check_runtime=True):
    docs=docs or repo/'docs'
    for name,expected in HISTORICAL.items():
        check(hashlib.sha256((repo/name).read_bytes()).hexdigest()==expected,'HISTORICAL_FILE',name)
    parent=strict_read(repo/'docs/task15_tail_attribution_protocol_v1.1.0.json')
    check(protocol_digest(parent)==parent['identity']['sha256']==PARENT_HASH,'PARENT_HASH')
    original=strict_read(repo/'docs/task15_tail_attribution_protocol.json')
    check(protocol_digest(original)==original['identity']['sha256']=='590838e4fdde2dcd86228fe0c521845e479fcc6372fa39d3745cb21270ce8247','ORIGINAL_HASH')
    document=strict_read(docs/'task15_tail_attribution_protocol_v1.2.0.json')
    report=verify_order(document,parent)
    report.update(verify_science(document))
    ledger=strict_read(docs/'task15_tail_attribution_amendment_v1.2.0.json')
    unsigned=deepcopy(ledger);stored=unsigned.pop('identity_sha256')
    check(digest(unsigned)==stored==EXPECTED_LEDGER_HASH,'LEDGER_HASH')
    check(ledger['changed_json_paths']==json_differences(parent,document),'LEDGER_PATHS')
    check(ledger['parent_commit']==PARENT_COMMIT and ledger['parent_canonical_sha256']==PARENT_HASH and
          ledger['parent_file_byte_sha256']==HISTORICAL and document['ordering_amendment']['parent_files_sha256']==HISTORICAL,'LEDGER_PARENT')
    check(ledger['new_canonical_sha256']==document['identity']['sha256'] and
          ledger['resolved_diagnostic_order_sha256']==document['design']['resolved_diagnostic_order_sha256'],'LEDGER_IDENTITIES')
    for key,name in [('new_JSON_file_byte_sha256','task15_tail_attribution_protocol_v1.2.0.json'),
                     ('new_MD_file_byte_sha256','task15_tail_attribution_preregistration_v1.2.0.md')]:
        check(hashlib.sha256((docs/name).read_bytes()).hexdigest()==ledger[key],'NEW_FILE_BYTES',name)
    check(ledger['execution_authorized'] is False and ledger['promotion_authorized'] is False and
          ledger['approval_signatures']==[] and ledger['independent_approval_status']=='NOT_INDEPENDENTLY_APPROVED','LEDGER_AUTHORIZATION')
    report.update(status='PASS_STATIC_ONLY_NOT_EXECUTION_APPROVAL',protocol_sha256=document['identity']['sha256'],
                  resolved_order_sha256=document['design']['resolved_diagnostic_order_sha256'],ledger_identity_sha256=stored,
                  historical_file_sha256=HISTORICAL,execution_authorized=False,promotion_authorized=False)
    if check_runtime:report['protected_git_objects']=verify_runtime(repo,parent)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--docs',type=Path,help='optional freshly regenerated documents directory')
    parser.add_argument('--output',type=Path,required=True,help='new exclusive external result file')
    args=parser.parse_args()
    try:
        result=verify_files(args.repo.resolve(),args.docs)
        with args.output.open('xb') as stream:stream.write(encoded(result)+b'\n')
        print(json.dumps({'status':result['status'],'output':str(args.output)}))
    except (Invalid,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'FAIL','error':getattr(exc,'code','INVALID_STRUCTURE'),'detail':str(exc)}))
        raise SystemExit(2)
