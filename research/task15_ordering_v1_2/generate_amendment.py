"""Deterministic pre-data document generator; no experiment execution facilities."""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path

PARENT_COMMIT = '367bbdefd279c8dc6673ed03e5bdc9f57031a08f'
PARENT_HASH = '6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f'
INITIATED_UTC = '2026-11-06T16:03:10.072221+00:00'  # 2026-11-07 in Asia/Kuala_Lumpur
STEM = 'task15_tail_attribution_'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_paths(old, new, path=''):
    if type(old) is dict and type(new) is dict:
        result = []
        for key in sorted(old.keys() | new.keys()):
            pointer = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in old or key not in new:
                result.append(pointer)
            else:
                result.extend(changed_paths(old[key], new[key], pointer))
        return result
    return [] if canonical(old) == canonical(new) else [path]


def resolve(parent):
    design = parent['design']
    references = {r['id']: r for r in design['base_schedule']}
    entries, units = [], []
    for session in range(4):
        entry_index = unit_index = 0
        for lane, source, session_field in (
                ('MAIN', design['diagnostic_schedule'], 'session'),
                ('COMPANION', design['allocator_stack_companions'], 'diagnostic_session')):
            lane_index = 0
            for original_index, row in enumerate(source):
                if row[session_field] != session:
                    continue
                companion = lane == 'COMPANION'
                conditions = ['trace_on_count_only'] if companion else row['condition_order']
                entry = {'diagnostic_session': session, 'session_key': f'DIAGNOSTIC/{session}',
                         'sequence_index': entry_index, 'lane': lane,
                         'diagnostic_entry_id': row['id'], 'cohort': 'C' if companion else row['cohort'],
                         'mode': 'allocation_stacks' if companion else row['mode'],
                         'schedule_ref': row['schedule_ref'],
                         'schedule_ref_session': references[row['schedule_ref']]['session'],
                         'source_lane_index': original_index, 'source_lane_session_index': lane_index,
                         'startup_order': row['variant_order'],
                         'condition': 'trace_on_count_only' if companion else None,
                         'condition_order': list(conditions),
                         'source_condition': row['condition'] if companion else None}
                entries.append(entry)
                for condition_index, condition in enumerate(conditions):
                    unit = {k: v for k, v in entry.items() if k not in ('condition_order', 'source_condition')}
                    unit.update(sequence_index=unit_index, entry_sequence_index=entry_index,
                                condition_index=condition_index, condition=condition,
                                unit_id=f'C/{row["id"]}/stack' if companion else f'{row["cohort"]}/{row["id"]}/{condition}')
                    units.append(unit)
                    unit_index += 1
                entry_index += 1
                lane_index += 1
    return {'schema_version': '1', 'kind': 'PREREGISTERED_ORDERING_METADATA_NOT_MEASUREMENTS',
            'rule': 'SESSION_END', 'session_order': [0, 1, 2, 3],
            'indexing': 'zero-based; entry and condition-block sequence_index are separate within-session domains',
            'source_lane_order_scope': 'original source arrays unchanged; main order is the inherited session-filtered subsequence, not global source-array index order across sessions',
            'worker_isolation': 'inherit fresh baseline/candidate pair per main condition and per stack companion; existing warmups, non-overlap, exit checks and failure rules unchanged',
            'stack_interpretation': 'supplementary session-end count-only allocation-stack context; never pooled with ordinary A/B latency or timed allocator evidence; not a contemporaneous causal contrast',
            'timing_limitation': 'late-session drift, memory/cache state and profiler effects may affect stack evidence despite fresh workers; no timing neutrality claim or added washout condition',
            'query_identity_policy': {'namespace_protocol_sha256': PARENT_HASH,
                                      'algorithm': 'SHA-256 of canonical JSON array',
                                      'fields': ['namespace_protocol_sha256', 'session_key', 'unit_id', 'phase', 'region', 'execution_index', 'original_position', 'variant'],
                                      'active_protocol_sha256': 'record new v1.2.0 canonical hash separately from the stable v1.1.0 query-ID namespace'},
            'execution_authorized': False, 'promotion_authorized': False,
            'entries': entries, 'condition_blocks': units}


def markdown(protocol):
    d = protocol['design']; order = d['resolved_diagnostic_order']
    header = f'''# Task 15 — Diagnostic Ordering Amendment v1.2.0

## Status and authority

**FROZEN PRE-DATA DESIGN; NOT INDEPENDENTLY APPROVED.** Execution and promotion
remain false. This amendment authorizes no harness adaptation, diagnostic build,
calibration, collection or dispatcher. The current 0.1.1 harness remains pinned
to v1.1.0. The old proposed clarification remains a historical proposal; this new
version explicitly chooses the scheduling rule without editing that proposal.

Parent commit: `{PARENT_COMMIT}`. Parent canonical SHA-256: `{PARENT_HASH}`.
New canonical SHA-256: `{protocol['identity']['sha256']}`.
Resolved cross-lane SHA-256: `{d['resolved_diagnostic_order_sha256']}`.

The complete [v1.2.0 JSON](task15_tail_attribution_protocol_v1.2.0.json) inherits
v1.1.0 verbatim except the precise paths in the [ledger](task15_tail_attribution_amendment_v1.2.0.json).
The retained `amendment` object documents the historical v1.1.0 amendment;
`ordering_amendment` identifies this v1.2.0 change. No historical file is superseded
in place. The versioned document is frozen for review, not execution approval.

## Scientific decision and alternatives

This comparison is a pre-data design inference from the frozen process lifecycle,
non-overlap rules, source lists and supplementary role of stacks. No new latency,
CPU, allocator or profiling observations were inspected to choose placement.
No quantitative performance or bias reduction is claimed.

| Alternative | Temporal confounding and comparability | Cache/memory and profiler interference | Fresh-worker isolation, frozen constraints and complexity |
| --- | --- | --- | --- |
| A: session-end (chosen) | Makes stacks systematically late; not contemporaneous with count/timed blocks. Suitable for supplementary stack context, not causal timing comparison. | Stack profiler activity is placed after that session's main work, avoiding its placement before later main blocks in the same session. Existing main diagnostics and host drift can still affect late stacks; effects can persist across sessions. | Retains all main order/condition constraints, assigned sessions and original companion order; existing fresh pairs remain required. Simplest deterministic merge. |
| B: adjacent to related allocator-count entry | Reduces temporal distance to a related entry, but does not establish a matched contemporaneous contrast; does not justify pooling. | Inserts stack-profiler work between existing main blocks and may perturb subsequent main work. | Still needs fresh pairs. Requires an additional choice of anchor mode and position relative to both frozen conditions; higher complexity without evidence of superior stack interpretation. |
| C: isolated within-session blocks | Fixed internal blocks make position explicit, but block placement remains confounded with time. Isolation is not proven by naming a block. | Internal blocks may perturb later main work; fresh workers do not reset host state. A real cooldown/washout would add an uncalibrated condition. | Requires more placement decisions; no existing evidence justifies changing conditions or adding a washout. An isolated final block reduces to A. |

Choose **SESSION_END**. For diagnostic sessions 0, 1, 2, 3 in order: filter the
original main source list by assigned session, retain its stored relative order,
expand each entry's frozen conditions contiguously, then complete that session's
assigned companions in their original source-list order before the next session.
All operations/regions/variants within a condition retain the frozen P2 mapping.
No random draws, runtime options or observation-dependent selection enter this rule.

Late-session placement could materially affect stack frequencies or which paths
are observed. Fresh process pairs limit reuse of worker-local state; they do not
reset thermal, OS cache, memory pressure, background work or profiler state.
Session-end placement is defensible specifically because stack evidence is
supplementary, not a confirmatory or timed allocator contrast. A stack supports
location/context for observed allocator activity; it cannot establish temporal
causation, quantify ordinary A/B latency, or be pooled with C timed requests.
Retain existing host/profiler records, attribution uncertainty, stop/failure and
no-retry rules. Do not delete inconvenient late stacks, move them earlier after
observations, or add a cooldown. Any later placement/condition change requires
another versioned, pre-data amendment and review.

No data are collected by this task. No new Task 15 observations inform the design.
The supplied task declares pre-data intent; repository metadata cannot prove no
Task 15 collection occurred anywhere. That global absence remains UNVERIFIED.
No independent approval signature is supplied or manufactured.

## Complete diagnostic entry order

Indices below are zero-based within each diagnostic session. Main condition order
is contiguous within each entry. `source_lane_index` in JSON preserves the original
global source-array index; `source_lane_session_index` preserves its filtered lane
index. Across sessions the inherited main rule is session filtering, so global
source-array order is not itself a chronological constraint.

| Session | Entry index | Lane | Original entry | Cohort / mode | Frozen P2 reference | Ordered conditions |
| --- | --- | --- | --- | --- | --- | --- |
'''
    rows = []
    for e in order['entries']:
        rows.append(f"| {e['diagnostic_session']} | {e['sequence_index']} | {e['lane']} | {e['diagnostic_entry_id']} | {e['cohort']} / {e['mode']} | {e['schedule_ref']} | {', '.join(e['condition_order'])} |")
    footer = '''
## Counts, provenance and stable identities

| Diagnostic session | Main entries | Main condition blocks | Companions | Total blocks |
| --- | --- | --- | --- | --- |
| 0 | 12 | 24 | C-stack-0, C-stack-1 | 26 |
| 1 | 12 | 24 | none | 24 |
| 2 | 12 | 24 | C-stack-4, C-stack-5 | 26 |
| 3 | 12 | 24 | none | 24 |
| Total | 48 | 96 | 4 | 100 |

The two original arrays remain byte-identical as canonical values and retain their
original digests. They remain authoritative provenance for entry contents.
`design.resolved_diagnostic_order.entries` contains 52 distinct entries;
`condition_blocks` contains the complete 100-unit order. The separate resolved-order
hash covers all ordering metadata, including both arrays, rule and identity policy.
No latency, timing sample or other scientific measurement is stored in this object.
128 primary A/B units are unchanged; total remains 228 units and 138,696 structural
records, including all warmups and untimed hot preparation records. All 64 base
rows, eight primary sessions, four diagnostic sessions, P1/P2 assignments,
permutations, original position/source/occurrence identities and variant orders
remain unchanged. C retains 41 selected positions. P2 remains 50/50 per trial,
16/16 per original position, 2/2 per original position/session, in each region.
Clock/CPU boundaries, H1, bootstrap, multiplicity, strict p99, G1-G10, binary/graph
identities, no adaptive retry/exclusion, and stop rules remain verbatim.

The new protocol hash changes provenance, not the logical workload/query IDs.
For continuity, structural query IDs retain the exact 0.1.1 derivation with the
v1.1.0 canonical hash as their **identity namespace**, along with namespaced session,
unit ID, phase, region, execution index, original position and variant. Record the
active v1.2.0 protocol hash separately. This explicit namespace is not permission
to validate v1.2.0 with a v1.1.0 manifest. Future adaptation must verify the unchanged
ID set and each unit's internal query order while adopting the new cross-unit order.

## Hash and validation contract

Canonical protocol hash: remove only `identity.sha256`; sorted-key compact
ASCII-escaped UTF-8 JSON; SHA-256. Resolved-order hash: same canonical serialization
of `design.resolved_diagnostic_order`. The JSON file-byte hash includes its pretty
printing/trailing LF and is distinct. The ledger has its own canonical
`identity_sha256`, computed after removing only that field; its final file-byte
hash is recorded by external evidence, avoiding circular self-hashes.

The separate static generator and validator share no imports or order constructor.
The validator independently checks source membership, within-session lane order,
conditions, sessions, references, contiguous indices, exact metadata, parent-only
projection, counts, source occurrences, P2 balances, workload/query identities,
all parent file hashes and protected Git objects. Negative fixtures test missing,
duplicate and moved companions; reordered main entries; reversed conditions;
wrong reference; altered P2 mapping; stale order and canonical hashes. Invalid
fixtures have classified reasons even when their outer digests are repaired.
All mutable test logs/results and generation comparisons are outside Git.

## Required future harness adaptation — separately authorized

Do not change the existing package in this task. Future work must:

1. Update `protocol.py` PROTOCOL_HASH, PARENT_HASH, LEDGER_HASH, AMENDMENT_MD_HASH,
   explicit accepted version/file paths, parent-chain validation and the closed
   protocol schema. Retain the entire v1.0 -> v1.1 -> v1.2 historical chain.
2. Retain original two-lane entry structures for provenance; introduce a separate
   resolved condition-block sequence. Do not append all companions after all four
   sessions. Resolve by session-local sequence index exactly as frozen here.
3. Preserve primary unit IDs and all per-unit jobs; preserve query IDs with the
   declared stable namespace while recording active v1.2.0 provenance separately.
   Recompute plan identity and version/source locks; do not reuse a v1.1 plan hash.
4. Adapt tests for pinned hashes/version/schema, resolved ordering and deliberately
   unchanged query IDs/occurrences/counts, while preserving all F-01 through F-11
   controls, partial-lane provenance tests and no-execution restrictions.
5. Create new exclusive manifests locking v1.2 canonical and file-byte hashes,
   new ledger/Markdown/order hashes and future adapted harness source/version,
   plan, dependency, runtime and artifact identities. Old v1.1 manifests remain
   historical and cannot authorize v1.2 execution. They remain valid only under
   their unchanged v1.1 harness/repository observation constraints.

A future dispatcher must consume the reviewed 100-block sequence exactly after
all primary A/B work, with inherited lifecycle/failure gates. This amendment
implements no dispatcher. Loader adaptation itself grants no calibration or
collection authorization. G8, diagnostic builds, host capabilities, sufficient
storage, capacity/clock/instrument calibration and separate signed authorization
remain pending. Independent review status remains NOT_INDEPENDENTLY_APPROVED.
'''
    return header + '\n'.join(rows) + '\n' + footer


def build(repo):
    parent_file = repo/'docs'/f'{STEM}protocol_v1.1.0.json'
    parent = json.loads(parent_file.read_bytes())
    check = deepcopy(parent); stored = check['identity'].pop('sha256')
    if stored != PARENT_HASH or sha(check) != PARENT_HASH:
        raise ValueError('parent canonical mismatch')
    new = deepcopy(parent); new['version'] = '1.2.0'
    order = resolve(parent)
    new['design']['resolved_diagnostic_order'] = order
    new['design']['resolved_diagnostic_order_sha256'] = sha(order)
    new['design']['diagnostic_order'] = 'SESSION_END: sessions0..3; each session retains its embedded main-list filtered order and contiguous frozen conditions, followed by its assigned companions in original companion-list order; authoritative expanded order is design.resolved_diagnostic_order.condition_blocks'
    new['future_execution']['active_protocol_file'] = 'docs/task15_tail_attribution_protocol_v1.2.0.json'
    new['future_execution']['approval_gate'] = 'v1.2.0 NOT_INDEPENDENTLY_APPROVED; this scheduling amendment grants no harness adaptation, calibration, collection or promotion authorization. Future host preflight, diagnostic equivalence and separate signed authorization remain mandatory.'
    frozen_names = [f'{STEM}protocol.json', f'{STEM}preregistration.md', f'{STEM}protocol_v1.1.0.json', f'{STEM}preregistration_v1.1.0.md', f'{STEM}amendment_v1.1.0.json']
    parent_files = {'docs/'+name: file_sha(repo/'docs'/name) for name in frozen_names}
    new['ordering_amendment'] = {'parent_version': '1.1.0', 'parent_commit': PARENT_COMMIT,
        'parent_canonical_sha256': PARENT_HASH, 'parent_files_sha256': parent_files,
        'ledger': f'{STEM}amendment_v1.2.0.json', 'approval_status': 'NOT_INDEPENDENTLY_APPROVED',
        'pre_data_declaration': 'Chosen before any Task15 diagnostic collection authorized by this amendment; no new Task15 performance observations used or generated here.',
        'global_collection_absence': 'UNVERIFIED; supplied task declares pre-data intent, repository metadata cannot prove absence everywhere',
        'new_task15_observations_used': False, 'declaration_date_local': '2026-11-07',
        'declaration_timezone': 'Asia/Kuala_Lumpur'}
    del new['identity']['sha256']; new['identity']['sha256'] = sha(new)
    raw = (json.dumps(new,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode()
    md = markdown(new).encode()
    ledger = {'amendment_version': '1.2.0', 'parent_version': '1.1.0', 'parent_commit': PARENT_COMMIT,
        'initiated_utc': INITIATED_UTC,
        'parent_canonical_sha256': PARENT_HASH, 'parent_file_byte_sha256': parent_files,
        'declaration_date_local': '2026-11-07', 'declaration_timezone': 'Asia/Kuala_Lumpur',
        'new_canonical_sha256': new['identity']['sha256'],
        'new_JSON_file_byte_sha256': hashlib.sha256(raw).hexdigest(),
        'new_MD_file_byte_sha256': hashlib.sha256(md).hexdigest(),
        'original_main_diagnostic_schedule_sha256': parent['design']['diagnostic_schedule_sha256'],
        'original_companion_schedule_sha256': parent['design']['allocator_stack_companions_sha256'],
        'unchanged_base_schedule_sha256': parent['design']['schedule_sha256'],
        'resolved_diagnostic_order_sha256': sha(order),
        'changed_json_paths': changed_paths(parent,new),
        'scientific_rationale': 'Session-end placement preserves every existing main condition sequence and keeps stack profiling after that session main work. Late-session stack evidence remains temporally confounded and supplementary, never pooled with A/B latency or timed allocator evidence.',
        'original_scheduling_rule': parent['design']['diagnostic_order'] + '; companion cross-lane interleaving unspecified',
        'new_scheduling_rule': new['design']['diagnostic_order'],
        'data_dependence_assessment': 'No new Task15 observations, source latency rankings, random draws or adaptive choices used; rule depends only on frozen session and source-lane metadata.',
        'pre_data_declaration': new['ordering_amendment']['pre_data_declaration'],
        'global_collection_absence': new['ordering_amendment']['global_collection_absence'],
        'new_task15_observations_used': False,
        'comparability_impact': 'Primary work and every per-unit query/condition/variant order are unchanged; cross-lane chronology becomes explicit. Stacks are systematically late and not contemporaneous causal contrasts. No claim of timing neutrality.',
        'independent_approval_status': 'NOT_INDEPENDENTLY_APPROVED', 'approval_signatures': [],
        'execution_authorized': False, 'promotion_authorized': False,
        'counts': {'main_entries':48,'companion_entries':4,'diagnostic_entries':52,'main_condition_blocks':96,'companion_blocks':4,'diagnostic_units':100,'primary_units':128,'total_units':228,'structural_query_records':138696},
        'identity_canonicalization': 'SHA-256 canonical sorted compact ASCII UTF-8 JSON after removing only identity_sha256'}
    ledger['identity_sha256'] = sha(ledger)
    return {f'{STEM}protocol_v1.2.0.json':raw, f'{STEM}preregistration_v1.2.0.md':md,
            f'{STEM}amendment_v1.2.0.json':(json.dumps(ledger,indent=2)+'\n').encode()}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True,help='existing directory; files exclusively created')
    args=parser.parse_args()
    payloads=build(args.repo.resolve())
    if any((args.output_dir/name).exists() for name in payloads):
        parser.error('refusing to overwrite any amendment file')
    for name,raw in payloads.items():
        with (args.output_dir/name).open('xb') as stream:stream.write(raw)
    print(json.dumps({name:hashlib.sha256(raw).hexdigest() for name,raw in payloads.items()},sort_keys=True))
