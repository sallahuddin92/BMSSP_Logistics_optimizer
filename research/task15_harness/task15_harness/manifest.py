from __future__ import annotations
from copy import deepcopy
from typing import Any
from . import __version__
from .artifacts import capacity, inspect_identities, repository_identity, source_lock
from .errors import require
from .integrity import digest, read_json, schema_check
from .planning import compile_plan, plan_counts
from .protocol import PACKAGE_ROOT, Protocol, LEDGER_HASH

SAFE_STATES = ('DRAFT', 'STATIC_VERIFIED', 'AWAITING_APPROVAL')
FUTURE_STATES = ('APPROVED_FOR_CALIBRATION', 'CALIBRATION_COMPLETE',
                 'APPROVED_FOR_COLLECTION', 'COLLECTION_COMPLETE', 'INVALID')
PROVENANCE = {'operation': 'prepare-manifest', 'scope': 'STATIC_CONTROL_PLANE_ONLY',
              'review_status': 'user reports conditional harness-preparation approval; no signed collection approval supplied'}


def seal(value: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(value)
    out.pop('identity_sha256', None)
    out['identity_sha256'] = digest(out)
    return out


def requirements_for(protocol: Protocol, plan: dict[str, Any]) -> dict[str, Any]:
    p = protocol.data()
    return {'interpreter': p['statistics']['bootstrap_execution_spec']['python_serialization'],
            'numpy_analysis': p['statistics']['bootstrap_execution_spec']['numpy_version'],
            'clock_requirements': p['instruments'][:4], 'capacity': capacity(protocol),
            'diagnostic_build_requirements': p['calibration']['diagnostic_build_equivalence'],
            'pending_preflight': p['environment']['host_verification_boundary'],
            'evidence_destination': None, 'storage_status': 'NOT_CHECKED',
            'required_approvals': ['independent harness review', 'separate calibration/collection authorization',
                                   'diagnostic G1..G10', 'Class L layout risk if applicable'],
            'partial_order_note': plan['ordering_caveat']}


def prepare_manifest(protocol: Protocol, state: str = 'DRAFT', checked: bool = True) -> dict[str, Any]:
    require(state in SAFE_STATES, 'STATE_FORBIDDEN', state)
    p = protocol.data()
    plan = compile_plan(protocol)
    value = {'schema_version': '1', 'kind': 'CONTROL_PLANE_EXECUTION_MANIFEST', 'state': 'DRAFT',
        'protocol': {'id': p['protocol_id'], 'version': p['version'], 'canonical_sha256': protocol.identity,
            'schedule_sha256': p['design']['schedule_sha256'],
            'diagnostic_schedule_sha256': p['design']['diagnostic_schedule_sha256'],
            'amendment_ledger_sha256': LEDGER_HASH},
        'repository': repository_identity(protocol),
        'harness': {'version': __version__, 'source_lock': source_lock()},
        'plan': {'identity_sha256': plan['identity_sha256'], 'counts': plan_counts(protocol, plan)},
        'identities': inspect_identities(protocol, checked=checked),
        'requirements': requirements_for(protocol, plan),
        'authorization': {'calibration': False, 'execution': False, 'promotion': False,
                          'approval_signatures': [], 'future_execution_eligible': False},
        'provenance': deepcopy(PROVENANCE),
        'transitions': []}
    value = seal(value)
    if state != 'DRAFT':
        value = transition(protocol, value, 'STATIC_VERIFIED')
    if state == 'AWAITING_APPROVAL':
        value = transition(protocol, value, 'AWAITING_APPROVAL')
    validate_manifest(protocol, value)
    return value


def transition(protocol: Protocol, value: dict[str, Any], target: str) -> dict[str, Any]:
    require(target in SAFE_STATES, 'STATE_FORBIDDEN', target)
    validate_manifest(protocol, value)
    require((value['state'], target) in {('DRAFT','STATIC_VERIFIED'),
                                       ('STATIC_VERIFIED','AWAITING_APPROVAL')},
            'STATE_TRANSITION', f'{value["state"]}->{target}')
    require(value['identities'] == inspect_identities(protocol) and
            value['identities']['all_verified'] and value['repository']['runtime_matches_task14'] and
            value['repository']['branch'] == protocol.data()['branch'] and
            value['repository']['origin'] == protocol.data()['origin'],
            'STATIC_GATE', 'artifact/runtime mismatch blocks static eligibility')
    out = deepcopy(value)
    out['transitions'].append({'from': out['state'], 'to': target,
                              'provenance': 'static_control_plane_validation; no approval granted'})
    out['state'] = target
    return seal(out)


def validate_manifest(protocol: Protocol, value: dict[str, Any]) -> dict[str, Any]:
    schema_check(value, read_json(PACKAGE_ROOT/'schemas/manifest-1.schema.json'))
    require(value['state'] in SAFE_STATES, 'STATE_FORBIDDEN', value['state'])
    auth = value['authorization']
    require(all(auth[k] is False for k in ['calibration','execution','promotion','future_execution_eligible'])
            and auth['approval_signatures'] == [], 'AUTHORIZATION', 'no Phase1 approval/dispatch')
    check = deepcopy(value)
    stored = check.pop('identity_sha256')
    require(digest(check) == stored, 'MANIFEST_HASH', 'integrity')
    p = protocol.data()
    require(value['provenance'] == PROVENANCE, 'MANIFEST_PROVENANCE', 'no invented approval provenance')
    require(value['requirements'] == requirements_for(protocol, compile_plan(protocol)),
            'MANIFEST_REQUIREMENTS', 'frozen pending gates cannot be weakened')
    require(value['harness']['version'] == __version__, 'HARNESS_CHANGED', 'version')
    require(value['protocol'] == {'id': p['protocol_id'], 'version': p['version'],
        'canonical_sha256': protocol.identity, 'schedule_sha256': p['design']['schedule_sha256'],
        'diagnostic_schedule_sha256': p['design']['diagnostic_schedule_sha256'],
        'amendment_ledger_sha256': LEDGER_HASH}, 'MANIFEST_PROTOCOL', 'frozen lock')
    require(value['plan'] == {'identity_sha256': compile_plan(protocol)['identity_sha256'],
        'counts': plan_counts(protocol, compile_plan(protocol))}, 'PLAN_MODIFIED', 'manifest plan')
    require(value['harness']['source_lock'] == source_lock(), 'HARNESS_CHANGED', 'current source identity')
    require(value['repository'] == repository_identity(protocol), 'REPOSITORY_CHANGED', 'revision/worktree')
    state = 'DRAFT'
    for item in value['transitions']:
        require(set(item) == {'from','to','provenance'} and item['provenance'] ==
                'static_control_plane_validation; no approval granted', 'STATE_TRANSITION', 'untrusted transition provenance')
        require(item['from'] == state and (state, item['to']) in
                {('DRAFT','STATIC_VERIFIED'), ('STATIC_VERIFIED','AWAITING_APPROVAL')},
                'STATE_TRANSITION', 'invalid provenance chain')
        state = item['to']
    require(state == value['state'], 'STATE_TRANSITION', 'state does not match chain')
    unchecked = all(r['status'] == 'NOT_CHECKED' for r in value['identities']['records'])
    current = inspect_identities(protocol, checked=not unchecked)
    require(value['identities'] == current, 'IDENTITY_REPORT_CHANGED', 'revalidate reported file observations')
    if state != 'DRAFT':
        current = inspect_identities(protocol)
        require(value['identities'] == current and current['all_verified'] and
                value['repository']['runtime_matches_task14'] and
                value['repository']['branch'] == p['branch'] and
                value['repository']['origin'] == p['origin'], 'STATIC_GATE', 'revalidate identities')
    return {'status': 'VALID_STATIC_MANIFEST', 'state': state, 'future_execution_eligible': False,
            'pending': ['diagnostic builds/G8', 'clock/permission/overhead/capacity/storage preflight',
                        'independent harness review and separate authorization']}
