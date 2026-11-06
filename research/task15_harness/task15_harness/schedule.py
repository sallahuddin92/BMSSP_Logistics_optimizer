from __future__ import annotations
from collections import Counter
from typing import Any
from .errors import require
from .integrity import digest

SOURCE_IDENTITIES = {
 'seremban-small': '63f637f7424b5feda1ab562cc212cd97b93ae41387ea9fd11a4cb1bbff992caf',
 'seremban-medium': '09c7bd58b3e0e5fba129062a6bfc9b7986b0e741cc64bcbd4b7ce97a8ec2d856',
 'seremban-port-dickson': '69248f44e945d1e74b2166a09353e1af8edcea325d55f51565872a1b557c5984'}


def validate_schedule(p: dict[str, Any]) -> dict[str, Any]:
    """Evaluate STORED instructions. No generator import, seed reconstruction or routing."""
    d, inputs = p['design'], p['inputs']
    regions = d['regions']
    require(set(regions) == set(SOURCE_IDENTITIES) and len(regions) == 3,
            'REGION_IDENTITY', str(regions))
    sources = {}
    for g in regions:
        ids = inputs[g]['source_positions']
        require(len(ids) == 100 and all(type(x) is str and x.isdecimal() for x in ids),
                'SOURCE_POSITION', g)
        require(digest(ids) == SOURCE_IDENTITIES[g], 'SOURCE_IDENTITY', g)
        require(len(set(ids)) == (96 if g == 'seremban-small' else 100),
                'SOURCE_MULTIPLICITY', g)
        sources[g] = {'positions': len(ids), 'distinct': len(set(ids)),
                      'occurrences': dict(Counter(ids))}
    rows = d['base_schedule']
    require(len(rows) == 64 and Counter(r['protocol'] for r in rows) == {'P1': 32, 'P2': 32},
            'TRIAL_COUNT', 'require 32 P1 and 32 P2')
    require(len({r['id'] for r in rows}) == 64, 'TRIAL_DUPLICATE', 'base IDs')
    common = {'id', 'session', 'protocol', 'trial_within_protocol', 'startup_order',
              'regions', 'positions_by_region'}
    trial_ids = {'P1': set(), 'P2': set()}
    for r in rows:
        proto, sid, tid = r['protocol'], r['session'], r['trial_within_protocol']
        require(proto in trial_ids and type(sid) is int and type(tid) is int and
                0 <= sid < 8 and 0 <= tid < 32 and tid // 4 == sid and
                r['id'] == f'S{sid:02d}-{proto}-T{tid:02d}', 'TRIAL_ID', r['id'])
        extra = {'P1_variant_order'} if proto == 'P1' else {'P2_pair_orders_by_region'}
        require(set(r) == common | extra, 'CROSS_PROTOCOL_FIELD', r['id'])
        require(r['startup_order'] in ['AB', 'BA'], 'ORDER_ENUM', r['id'])
        trial_ids[proto].add(tid)
        require(len(r['regions']) == 3 and set(r['regions']) == set(regions),
                'REGION_PERMUTATION', r['id'])
        require(set(r['positions_by_region']) == set(regions), 'REGION_IDENTITY', r['id'])
        for g in regions:
            positions = r['positions_by_region'][g]
            require(len(set(positions)) == len(positions), 'POSITION_DUPLICATE', r['id']+g)
            require(len(positions) == 100 and all(type(x) is int for x in positions) and
                    set(positions) == set(range(100)), 'POSITION_MISSING', r['id']+g)
    require(all(v == set(range(32)) for v in trial_ids.values()), 'TRIAL_ID', 'coverage')
    counts = {}
    for proto in ['P1', 'P2']:
        subset = [r for r in rows if r['protocol'] == proto]
        session_counts, joint = {}, Counter()
        for s in range(8):
            rr = [r for r in subset if r['session'] == s]
            require(len(rr) == 4, 'SESSION_COUNT', f'{proto}/{s}')
            startup = Counter(r['startup_order'] for r in rr)
            require(startup == {'AB': 2, 'BA': 2}, 'STARTUP_BALANCE', f'{proto}/{s}')
            item = {'trials': len(rr), 'startup': dict(startup)}
            if proto == 'P1':
                combos = Counter((r['startup_order'], r['P1_variant_order']) for r in rr)
                require(combos == {('AB','AB'):1, ('AB','BA'):1, ('BA','AB'):1,
                                   ('BA','BA'):1}, 'P1_ORTHOGONALITY', str(s))
                joint.update(combos)
                item['combinations'] = {'/'.join(k): v for k, v in combos.items()}
            session_counts[str(s)] = item
        region_slots = {g: dict(Counter(r['regions'].index(g) for r in subset)) for g in regions}
        require(all(sorted(v.values()) == [10, 11, 11] for v in region_slots.values()),
                'REGION_BALANCE', proto)
        counts[proto] = {'trials': len(subset), 'sessions': session_counts,
                         'region_slots': region_slots,
                         'combinations': {'/'.join(k): v for k, v in joint.items()}}
    p2 = [r for r in rows if r['protocol'] == 'P2']
    counts['P2']['regions'] = {}
    for g in regions:
        global_ab = [0] * 100
        session_ab = [[0] * 100 for _ in range(8)]
        trial_counts = {}
        for r in p2:
            orders = r['P2_pair_orders_by_region'][g]
            cc = Counter(orders)
            require(len(orders) == 100 and cc == {'AB': 50, 'BA': 50},
                    'P2_TRIAL_BALANCE', r['id']+g)
            trial_counts[r['id']] = dict(cc)
            for execution, original in enumerate(r['positions_by_region'][g]):
                # The important mapping: labels are EXECUTION-indexed; counts are ORIGINAL-indexed.
                if orders[execution] == 'AB':
                    global_ab[original] += 1
                    session_ab[r['session']][original] += 1
        require(global_ab == [16] * 100, 'P2_POSITION_BALANCE', g)
        require(all(x == [2] * 100 for x in session_ab), 'P2_SESSION_BALANCE', g)
        counts['P2']['regions'][g] = {'per_trial': trial_counts,
            'AB_by_original_position': global_ab, 'BA_by_original_position': [32-x for x in global_ab],
            'AB_by_session_original_position': session_ab,
            'BA_by_session_original_position': [[4-x for x in row] for row in session_ab]}
    require(digest(rows) == d['schedule_sha256'], 'SCHEDULE_HASH', 'base')
    lookup = {r['id']: r for r in rows}
    diag = d['diagnostic_schedule']
    require(len(diag) == 48 and len({r['id'] for r in diag}) == 48,
            'DIAGNOSTIC_COUNT', '48 distinct IDs')
    for r in diag + d['allocator_stack_companions']:
        require(r['schedule_ref'] in lookup and lookup[r['schedule_ref']]['protocol'] == 'P2',
                'DIAGNOSTIC_REFERENCE', r['id'])
        ref = lookup[r['schedule_ref']]
        subset = p['cohorts']['C']['positions_by_region'] if r.get('cohort') == 'C' or r['id'].startswith('C-stack-') else {g: list(range(100)) for g in regions}
        work = {'source_permutations': ref['positions_by_region'],
                'pair_orders_execution_index': ref['P2_pair_orders_by_region'],
                'positions_by_region': subset,
                'source_position_identities': {g: inputs[g]['source_position_identity_sha256'] for g in regions}}
        require(digest(work) == r['resolved_workload_sha256'], 'DIAGNOSTIC_WORKLOAD', r['id'])
    require(digest(diag) == d['diagnostic_schedule_sha256'], 'SCHEDULE_HASH', 'diagnostic')
    require(digest(d['allocator_stack_companions']) == d['allocator_stack_companions_sha256'],
            'SCHEDULE_HASH', 'stack companions')
    require(sum(map(len, p['cohorts']['C']['positions_by_region'].values())) == 41,
            'DIAGNOSTIC_SUBSET', '41 C positions')
    return {'status': 'STATIC_SCHEDULE_VERIFIED',
            'computed_schedule_sha256': digest(rows),
            'computed_diagnostic_schedule_sha256': digest(diag),
            'computed_stack_companions_sha256': digest(d['allocator_stack_companions']), 'protocols': counts, 'sources': sources,
            'diagnostic_modes': dict(Counter(r['mode'] for r in diag)),
            'diagnostic_trials': 48, 'stack_companions': len(d['allocator_stack_companions'])}
