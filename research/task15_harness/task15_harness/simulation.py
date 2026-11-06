from __future__ import annotations
from typing import Any, Iterator
from .errors import require
from .planning import query_records
from .protocol import Protocol, protocol_binding

LABEL = 'SYNTHETIC_CONTROL_PLANE_TEST'


def reject_synthetic_for_measurement(record: dict[str, Any]) -> None:
    require(record.get('label') != LABEL and record.get('synthetic') is not True,
            'SYNTHETIC_NOT_MEASUREMENT', 'structural events cannot enter performance evidence')


def simulate(protocol: Protocol, plan: dict[str, Any], fail_query: str | None = None,
             interrupt_after: int | None = None, attempt: int = 1) -> Iterator[dict[str, Any]]:
    require(attempt == 1, 'RETRY_FORBIDDEN', 'no synthetic retry/resume; attempts archived separately')
    require(interrupt_after is None or interrupt_after >= 0, 'SIMULATION_INPUT', 'nonnegative event limit')
    provenance = {'protocol': protocol_binding(protocol), 'plan_identity_sha256': plan['identity_sha256']}
    invalid: set[str] = set()
    visited: set[str] = set()
    seen_ids: set[str] = set()
    failure_seen = False
    cluster_sessions = {}
    count = 0
    for item in query_records(protocol, plan):
        session = {k: item[k] for k in ('session_kind', 'session_id', 'schedule_ref_session', 'session_key')}
        cluster_sessions[item['paired_cluster_id']] = session
        if interrupt_after is not None and count >= interrupt_after:
            invalid.add(item['paired_cluster_id'])
            yield {**provenance, 'label': LABEL, 'synthetic': True, 'event': 'INTERRUPTION',
                   **session, 'cluster': item['paired_cluster_id'], 'no_retry': True}
            break
        qid, cluster = item['query_id'], item['paired_cluster_id']
        require(qid not in seen_ids, 'QUERY_DUPLICATE', qid)
        seen_ids.add(qid)
        visited.add(cluster)
        status = 'SKIPPED_INVALID_CLUSTER' if cluster in invalid else 'STRUCTURAL_VISIT'
        if qid == fail_query:
            invalid.add(cluster)
            status = 'SYNTHETIC_FAILURE'
            failure_seen = True
        yield {**provenance, 'label': LABEL, 'synthetic': True, 'event': status, 'attempt': 1,
               **session, 'query': item, 'provisional_until_cluster_verdict': True}
        count += 1
    require(fail_query is None or failure_seen, 'SIMULATION_FAILURE_ID', 'requested synthetic failure was not visited')
    for cluster in sorted(visited | invalid):
        yield {**provenance, 'label': LABEL, 'synthetic': True, 'event': 'CLUSTER_VERDICT', **cluster_sessions[cluster], 'cluster': cluster,
               'status': 'INVALID' if cluster in invalid else 'STRUCTURALLY_VISITED',
               'whole_cluster_all_regions_both_variants': True, 'no_retry': True}
    yield {**provenance, 'label': LABEL, 'synthetic': True, 'event': 'SIMULATION_SUMMARY',
           'session_keys': sorted({s['session_key'] for s in cluster_sessions.values()}),
           'query_records_visited': count, 'invalid_clusters': sorted(invalid),
           'performance_values': 'NONE', 'measurement_eligible': False}
