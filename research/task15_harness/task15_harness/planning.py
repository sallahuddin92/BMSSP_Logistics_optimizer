from __future__ import annotations
from collections import Counter
from typing import Any, Iterator
from .errors import require
from .integrity import digest, read_json, schema_check
from .protocol import Protocol, PACKAGE_ROOT


def session_fields(kind: str, index: int, reference: int) -> dict[str, Any]:
    return {'session_kind': kind, 'session_id': index, 'schedule_ref_session': reference,
            'session_key': f'{kind}/{index}'}


def compile_plan(protocol: Protocol) -> dict[str, Any]:
    p = protocol.data()
    d = p['design']
    references = {r['id']: r for r in d['base_schedule']}
    units = []
    companions = []
    for session in d['sessions']:
        for cohort in session['cohort_phase_order']:
            for row in d['base_schedule']:
                if row['session'] == session['session']:
                    units.append({'id': f'{cohort}/primary/{row["id"]}', 'cohort': cohort,
                        **session_fields('PRIMARY', row['session'], row['session']), 'schedule_ref': row['id'], 'protocol': row['protocol'],
                        'mode': None, 'condition': 'ordinary', 'startup_order': row['startup_order'],
                        'subset': 'ALL', 'diagnostic_id': None})
    # Cohort order is a factor: diagnostic session filter preserves embedded list order.
    # Lanes retain their own order; their relative interleaving is unspecified.
    for session in sorted({r['session'] for r in d['diagnostic_schedule']}):
        for row in d['diagnostic_schedule']:
            if row['session'] != session:
                continue
            for condition in row['condition_order']:
                units.append({'id': f'{row["cohort"]}/{row["id"]}/{condition}', 'cohort': row['cohort'],
                    **session_fields('DIAGNOSTIC', session, references[row['schedule_ref']]['session']), 'schedule_ref': row['schedule_ref'], 'protocol': 'P2',
                    'mode': row['mode'], 'condition': condition, 'startup_order': row['variant_order'],
                    'subset': 'C' if row['cohort'] == 'C' else 'ALL', 'diagnostic_id': row['id']})
        for row in d['allocator_stack_companions']:
            if row['diagnostic_session'] == session:
                companions.append({'id': f'C/{row["id"]}/stack', 'cohort': 'C',
                    **session_fields('DIAGNOSTIC', session, references[row['schedule_ref']]['session']),
                    'schedule_ref': row['schedule_ref'], 'protocol': 'P2', 'mode': 'allocation_stacks',
                    'condition': 'trace_on_count_only', 'startup_order': row['variant_order'],
                    'subset': 'C', 'diagnostic_id': row['id']})
    # v1.1 does not order stack companions relative to other modes explicitly. This is
    # separate ordered lanes, never approval to collect; independent review required.
    plan = {'schema_version': '2', 'kind': 'STATIC_EXECUTION_PLAN_NOT_EXECUTABLE',
            'protocol_sha256': protocol.identity, 'schedule_sha256': d['schedule_sha256'],
            'diagnostic_schedule_sha256': d['diagnostic_schedule_sha256'], 'units': units,
            'stack_companions': companions,
            'collection_authorized': False,
            'ordering_caveat': 'Two partial-order lanes: main and allocation_stack_companions. Frozen protocol does not specify their cross-list interleaving. Serialization order is not execution order; future clarification requires review, no inferred cross-lane dispatch.'}
    plan['identity_sha256'] = digest(plan)
    return plan


def validate_plan(protocol: Protocol, plan: dict[str, Any]) -> None:
    require(plan == compile_plan(protocol), 'PLAN_MODIFIED', 'must equal deterministic frozen-schedule expansion')
    schema = read_json(PACKAGE_ROOT/'schemas/session-2.schema.json')
    for unit in plan.get('units', []) + plan.get('stack_companions', []):
        schema_check({k: unit[k] for k in schema['required'] if k in unit}, schema)


def _variants(order: str) -> list[str]:
    return ['baseline', 'candidate'] if order == 'AB' else ['candidate', 'baseline']


def query_records(protocol: Protocol, plan: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Lazy structural records; no timing calls, graph loading, dispatch or native import."""
    validate_plan(protocol, plan)
    p = protocol.data()
    rows = {r['id']: r for r in p['design']['base_schedule']}
    for unit in plan['units'] + plan['stack_companions']:
        row = rows[unit['schedule_ref']]
        for region in row['regions']:
            inp = p['inputs'][region]
            seen: Counter[str] = Counter()
            occurrences = []
            for source in inp['source_positions']:
                seen[source] += 1
                occurrences.append(seen[source])
            def record(variant: str, original: int, execution: int, phase: str, order: str) -> dict[str, Any]:
                identity = [protocol.identity, unit['session_key'], unit['id'], phase, region, execution, original, variant]
                return {'query_id': digest(identity), 'protocol_sha256': protocol.identity,
                    'cohort': unit['cohort'], **{k: unit[k] for k in ('session_kind', 'session_id', 'schedule_ref_session', 'session_key')}, 'trial_id': unit['id'],
                    'plan_lane': 'allocation_stack_companions' if unit['mode'] == 'allocation_stacks' else 'main',
                    'paired_cluster_id': unit['session_key'] + '/' + (unit['diagnostic_id'] or unit['id']),
                    'base_trial_id': row['id'], 'protocol': row['protocol'], 'variant': variant,
                    'region': region, 'original_position': original,
                    'source_id': inp['source_positions'][original], 'source_occurrence': occurrences[original],
                    'execution_index': execution, 'phase': phase, 'startup_order': unit['startup_order'],
                    'paired_execution_order': order, 'condition': unit['condition'], 'diagnostic_mode': unit['mode'],
                    'graph_sha256': inp['graph_sha256'], 'snapshot_id': inp['snapshot_id'],
                    'query_list_sha256': inp['query_file_sha256'],
                    'expected_binary': {'production_reference_sha256': p['binaries'][variant]['sha256'],
                        'planned_binary_sha256': p['binaries'][variant]['sha256'] if unit['cohort'] == 'A' else None,
                        'load_status': 'NOT_LOADED',
                        'status': 'PLANNED_PRODUCTION_IDENTITY' if unit['cohort'] == 'A' else 'PENDING_DIAGNOSTIC_BUILD'},
                    'provenance': 'FROZEN_PROTOCOL_STATIC_PLANNING', 'dispatchable': False}
            positions = row['positions_by_region'][region]
            subset = set(p['cohorts']['C']['positions_by_region'][region]) if unit['subset'] == 'C' else set(range(len(inp['source_positions'])))
            selected = [(i, original) for i, original in enumerate(positions) if original in subset]
            if row['protocol'] == 'P1':
                for variant in _variants(row['P1_variant_order']):
                    for i, original in enumerate(inp['warmup_positions']):
                        yield record(variant, original, i, 'warmup', row['P1_variant_order'])
                    for execution, original in selected:
                        yield record(variant, original, execution, 'target', row['P1_variant_order'])
            else:
                for variant in _variants(unit['startup_order']):
                    for i, original in enumerate(inp['warmup_positions']):
                        yield record(variant, original, i, 'warmup', unit['startup_order'])
                for execution, original in selected:
                    order = row['P2_pair_orders_by_region'][region][execution]
                    for variant in _variants(order):
                        if unit['mode'] == 'cpu_counters_cache':
                            yield record(variant, original, execution, 'untimed_hot_preparation', order)
                        yield record(variant, original, execution, 'target', order)


def plan_counts(protocol: Protocol, plan: dict[str, Any]) -> dict[str, Any]:
    validate_plan(protocol, plan)
    p = protocol.data()
    totals: Counter[str] = Counter()
    units = plan['units'] + plan['stack_companions']
    for unit in units:
        positions = sum(len(x) for x in p['cohorts']['C']['positions_by_region'].values()) if unit['subset'] == 'C' else sum(len(p['inputs'][r]['source_positions']) for r in p['inputs'])
        totals[f'{unit["cohort"]}/warmup'] += len(p['binaries']) * sum(len(i['warmup_positions']) for i in p['inputs'].values())
        totals[f'{unit["cohort"]}/target'] += len(p['binaries']) * positions
        if unit['mode'] == 'cpu_counters_cache':
            totals[f'{unit["cohort"]}/untimed_hot_preparation'] += len(p['binaries']) * positions
    return {'unit_count': len(units), 'query_record_count': sum(totals.values()),
            'by_cohort_phase': dict(totals), 'partial_order_lanes': 2}
