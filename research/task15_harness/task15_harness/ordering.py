"""Closed, static reconstruction of v1.2 session-end ordering from original lanes."""
from typing import Any
from .errors import require
from .integrity import canonical, digest

QUERY_NAMESPACE = '6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f'
QUERY_FIELDS = ['namespace_protocol_sha256', 'session_key', 'unit_id', 'phase', 'region',
                'execution_index', 'original_position', 'variant']


def validate_resolved_order(p: dict[str, Any]) -> None:
    d = p['design']
    order = d['resolved_diagnostic_order']
    require(order['rule'] == 'SESSION_END' and order['session_order'] == [0, 1, 2, 3],
            'ORDER_RULE', 'frozen session-end rule')
    require(order['execution_authorized'] is False and order['promotion_authorized'] is False,
            'AUTHORIZATION', 'ordering metadata cannot authorize execution')
    policy = order['query_identity_policy']
    require(policy['namespace_protocol_sha256'] == QUERY_NAMESPACE and policy['fields'] == QUERY_FIELDS,
            'QUERY_NAMESPACE', 'stable v1.1 identity namespace required')
    refs = {row['id']: row for row in d['base_schedule']}
    expected_entries: list[dict[str, Any]] = []
    expected_blocks: list[dict[str, Any]] = []
    for session in order['session_order']:
        entry_sequence = block_sequence = 0
        for lane, array, session_field in (
                ('MAIN', d['diagnostic_schedule'], 'session'),
                ('COMPANION', d['allocator_stack_companions'], 'diagnostic_session')):
            filtered = [(index, row) for index, row in enumerate(array) if row[session_field] == session]
            for local_index, (source_index, row) in enumerate(filtered):
                stack = lane == 'COMPANION'
                conditions = ['trace_on_count_only'] if stack else row['condition_order']
                entry = {'diagnostic_session': session, 'session_key': f'DIAGNOSTIC/{session}',
                    'sequence_index': entry_sequence, 'lane': lane, 'diagnostic_entry_id': row['id'],
                    'cohort': 'C' if stack else row['cohort'], 'mode': 'allocation_stacks' if stack else row['mode'],
                    'schedule_ref': row['schedule_ref'], 'schedule_ref_session': refs[row['schedule_ref']]['session'],
                    'source_lane_index': source_index, 'source_lane_session_index': local_index,
                    'startup_order': row['variant_order'], 'condition': 'trace_on_count_only' if stack else None,
                    'condition_order': conditions, 'source_condition': row['condition'] if stack else None}
                expected_entries.append(entry)
                for index, condition in enumerate(conditions):
                    block = {k: v for k, v in entry.items() if k not in ('condition_order', 'source_condition')}
                    block.update(sequence_index=block_sequence, entry_sequence_index=entry_sequence,
                        condition_index=index, condition=condition,
                        unit_id=f'C/{row["id"]}/stack' if stack else f'{row["cohort"]}/{row["id"]}/{condition}')
                    expected_blocks.append(block)
                    block_sequence += 1
                entry_sequence += 1
    for actual, expected, id_key, label in (
            (order['entries'], expected_entries, 'diagnostic_entry_id', 'ENTRY'),
            (order['condition_blocks'], expected_blocks, 'unit_id', 'UNIT')):
        actual_ids = [row[id_key] for row in actual]
        wanted = {row[id_key]: row for row in expected}
        require(len(actual_ids) == len(set(actual_ids)) == len(wanted) and set(actual_ids) == set(wanted),
                'ORDER_'+label+'_MEMBERSHIP', 'missing, duplicate or unexpected '+label.lower())
        for row in actual:
            reference = wanted[row[id_key]]
            for keys, code in ((('diagnostic_session', 'session_key'), 'ORDER_SESSION'),
                    (('schedule_ref', 'schedule_ref_session'), 'ORDER_REFERENCE'),
                    (('startup_order',), 'ORDER_VARIANT'),
                    (('condition',) if label == 'UNIT' else ('condition', 'condition_order'), 'ORDER_CONDITION'),
                    (('cohort', 'mode'), 'ORDER_WORKLOAD'),
                    (('lane', 'source_lane_index', 'source_lane_session_index'), 'ORDER_PROVENANCE')):
                require(all(canonical(row[k]) == canonical(reference[k]) for k in keys), code, row[id_key])
        require(canonical(actual) == canonical(expected), 'ORDER_SEQUENCE', label+' order/indices/metadata')
    require(digest(order) == d['resolved_diagnostic_order_sha256'], 'ORDER_HASH', 'resolved content digest')
