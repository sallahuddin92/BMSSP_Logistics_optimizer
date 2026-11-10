"""Frozen v1.3 environment provenance; static validation only, no execution adapter."""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
from typing import Any
from . import historical_v12 as historical
from .errors import ControlError, require
from .integrity import canonical, digest, hash_file, read_json, schema_check, strict_json_bytes
from .schedule import validate_schedule
from .ordering import validate_resolved_order

PROTOCOL_HASH = 'b639d9960353f00c5a3d5efc58255206d5dd7d7f701311ebe7f715f5ad277ddd'
PROTOCOL_FILE_HASH = 'd561f8c313400d72ffaa0290cb5df055a53ef270e79aa452dd91cfffba90bb0e'
PARENT_HASH = 'c41e45bccb68abdf03bab40ea793837a7f508fde17634c1aa8b358a3d82fceb0'
ORIGINAL_HASH = '590838e4fdde2dcd86228fe0c521845e479fcc6372fa39d3745cb21270ce8247'
LEDGER_HASH = '7363631745b5666dac6bf4b598ced4cc4373e9de491a10bbe3cd780e8e1bd800'
LEDGER_FILE_HASH = 'cbfa8e49e8e8fe48df1711a24ca110cedaff382924d1ea97197774f7a8116f52'
AMENDMENT_MD_HASH = '45aa925620346fab8dc012623b1f9de2d37949b9afc7c5ecccee7585b887a659'
RESOLVED_ORDER_HASH = '3e22c8ebfbdb23af04059bece54734844ee58664a3c43abd9170625922cf20ba'
ENVIRONMENT_AMENDMENT_HASH = '872d08f37b65e77aa63b5f47d3c8a6e3a2b0a55d1ddc93386aa24b46f61f7459'
ENVIRONMENT_INVENTORY_ID = '7e170e5cce91bc4092db793b0023d3f2b1c55d5580c912e737a5bc6af7e8d728'
ENVIRONMENT_PATH = '/Users/sallahuddin/Projects/BMSSP-task15-offline-reconstruction-jgt6c3vy/environment'
PYTHON_EXECUTABLE_HASH = 'd918e0f86b91facb5e5b0a3620d5c9190037697cae074b05e81be1bfb6e54568'
NUMPY_INSTALLED_ID = '3119c086dccc3e41c7c1ee69464289fd2dd5d18fbc61911c3c886981ebb22079'
PARENT_NUMPY_RULE = '1.24.4 exactly, already installed historical analysis environment; no upgrade/install authorized. Unavailable version blocks reproducible analysis pending explicit amendment.'
PARENT_APPROVAL_GATE = 'v1.2.0 NOT_INDEPENDENTLY_APPROVED; this scheduling amendment grants no harness adaptation, calibration, collection or promotion authorization. Future host preflight, diagnostic equivalence and separate signed authorization remain mandatory.'
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FROZEN_FILES = {**historical.FROZEN_FILES,
    'docs/task15_tail_attribution_protocol_v1.3.0.json': 'd561f8c313400d72ffaa0290cb5df055a53ef270e79aa452dd91cfffba90bb0e',
    'docs/task15_tail_attribution_preregistration_v1.3.0.md': '45aa925620346fab8dc012623b1f9de2d37949b9afc7c5ecccee7585b887a659',
    'docs/task15_tail_attribution_amendment_v1.3.0.json': 'cbfa8e49e8e8fe48df1711a24ca110cedaff382924d1ea97197774f7a8116f52',
}

canonical_protocol_hash = historical.canonical_protocol_hash
changed_paths = historical.changed_paths
verify_file_bytes = historical.verify_file_bytes


def parent_projection(value: dict[str, Any]) -> dict[str, Any]:
    """Remove only declared v1.3 provenance changes; all science must equal v1.2."""
    out = deepcopy(value)
    out.pop('analysis_environment_amendment', None)
    out['version'] = '1.2.0'
    out['identity']['sha256'] = PARENT_HASH
    out['statistics']['bootstrap_execution_spec']['numpy_version'] = PARENT_NUMPY_RULE
    out['future_execution']['active_protocol_file'] = 'docs/task15_tail_attribution_protocol_v1.2.0.json'
    out['future_execution']['approval_gate'] = PARENT_APPROVAL_GATE
    return out


def validate_environment(a: dict[str, Any]) -> None:
    require(a['parent_version'] == '1.2.0' and a['parent_canonical_sha256'] == PARENT_HASH
            and a['parent_commit'] == 'a8a021399da77935b7f66d1157bfac3d6fa93442',
            'AMENDMENT_IDENTITY', 'immediate v1.2 parent')
    require(a['python']['implementation'] == 'CPython' and a['python']['version'] == '3.11.15',
            'ANALYSIS_PYTHON_VERSION', 'exact frozen serialization runtime')
    require(a['python']['architecture'] == 'arm64' and a['numpy']['wheel_tag'] == 'cp311-cp311-macosx_11_0_arm64',
            'ANALYSIS_ARCHITECTURE', 'macOS arm64/cp311')
    require(a['numpy']['version'] == '1.24.4', 'ANALYSIS_NUMPY_VERSION', 'no NumPy2 substitution')
    require(a['python']['executable_sha256'] == PYTHON_EXECUTABLE_HASH
            and a['python']['base_executable_sha256'] == PYTHON_EXECUTABLE_HASH,
            'ANALYSIS_INTERPRETER_HASH', 'pinned current runtime, not historical-byte claim')
    require(a['numpy']['installed_file_identity_sha256'] == NUMPY_INSTALLED_ID,
            'ANALYSIS_PACKAGE_IDENTITY', 'exact installed distribution')
    require(a['replacement']['environment_path'] == ENVIRONMENT_PATH
            and a['replacement']['inventory_identity_sha256'] == ENVIRONMENT_INVENTORY_ID,
            'ANALYSIS_ENVIRONMENT_REPLACEMENT', 'no unapproved replacement')
    accept = a['scientific_acceptance']
    require(accept['status'] == 'SCIENTIFIC_ACCEPTANCE_PENDING'
            and accept['independent_approval_status'] == 'NOT_INDEPENDENTLY_APPROVED'
            and accept['approval_signatures'] == []
            and all(accept[k] is False for k in ['confirmatory_analysis_authorized', 'execution_authorized',
                'calibration_authorized', 'collection_authorized', 'promotion_authorized']),
            'SCIENTIFIC_APPROVAL', 'technical evidence cannot create signed acceptance')
    require(a['technical_verification']['status'] == 'TECHNICALLY_VERIFIED',
            'ANALYSIS_ENVIRONMENT_IDENTITY', 'recorded technical status')
    require(digest(a) == ENVIRONMENT_AMENDMENT_HASH,
            'ANALYSIS_ENVIRONMENT_IDENTITY', 'entire environment/provenance lock')


@dataclass(frozen=True)
class Protocol:
    _encoded: bytes
    repository: Path
    def __post_init__(self) -> None:
        require(type(self._encoded) is bytes, 'SCHEMA_TYPE', 'owned immutable bytes required')
        validate_document(strict_json_bytes(self._encoded))

    def data(self) -> dict[str, Any]:
        return strict_json_bytes(self._encoded)

    @property
    def identity(self) -> str:
        return PROTOCOL_HASH


def validate_document(value: dict[str, Any]) -> dict[str, Any]:
    require(type(value) is dict, 'SCHEMA_TYPE', 'protocol object')
    require(value.get('version') == '1.3.0', 'PROTOCOL_VERSION', str(value.get('version')))
    require(value.get('protocol_id') == 'BMSSP-T15-tail-attribution', 'PROTOCOL_ID', 'identifier')
    require(value.get('execution_authorized') is False and value.get('promotion_authorized') is False,
            'AUTHORIZATION', 'frozen false flags required')
    require(type(value.get('design')) is dict, 'SCHEMA_TYPE', '$.design')
    require(type(value['design'].get('base_schedule')) is list, 'SCHEMA_TYPE', '$.design.base_schedule')
    for row in value['design']['base_schedule']:
        require(type(row) is dict, 'SCHEMA_TYPE', '$.design.base_schedule[]')
        if row.get('protocol') == 'P1':
            require('P2_pair_orders_by_region' not in row, 'CROSS_PROTOCOL_FIELD', row.get('id',''))
        elif row.get('protocol') == 'P2':
            require('P1_variant_order' not in row, 'CROSS_PROTOCOL_FIELD', row.get('id',''))
    schema_check(value, read_json(PACKAGE_ROOT/'schemas/protocol-1.3.0.schema.json'))
    report = validate_schedule(value)
    validate_resolved_order(value)
    validate_environment(value['analysis_environment_amendment'])
    historical.validate_document(parent_projection(value))
    require(canonical_protocol_hash(value) == value['identity']['sha256'] == PROTOCOL_HASH,
            'PROTOCOL_HASH', 'canonical frozen v1.3 identity')
    return report


def load_protocol(repo: Path) -> Protocol:
    repo = repo.resolve()
    path = repo/'docs/task15_tail_attribution_protocol_v1.3.0.json'
    value = read_json(path)
    validate_document(value)
    verify_file_bytes(path, PROTOCOL_FILE_HASH, 'PROTOCOL_FILE_HASH')
    verify_file_bytes(repo/'docs/task15_tail_attribution_preregistration_v1.3.0.md', AMENDMENT_MD_HASH, 'FROZEN_FILE_HASH')
    ledger_path = repo/'docs/task15_tail_attribution_amendment_v1.3.0.json'
    ledger = read_json(ledger_path)
    require(type(ledger) is dict, 'AMENDMENT_HASH', 'ledger object required')
    unsigned = strict_json_bytes(canonical(ledger)); stored = unsigned.pop('identity_sha256', None)
    require(stored == digest(unsigned) == LEDGER_HASH, 'AMENDMENT_HASH', 'v1.3 ledger identity')
    verify_file_bytes(ledger_path, LEDGER_FILE_HASH, 'AMENDMENT_FILE_HASH')
    for filename, expected in FROZEN_FILES.items():
        try:
            actual = hash_file(repo/filename)[0]
        except OSError as exc:
            raise ControlError('HISTORICAL_FILE_MISSING', filename) from exc
        require(actual == expected, 'FROZEN_FILE_HASH', filename)
    parent = historical.load_protocol(repo).data()
    require(parent_projection(value) == parent, 'SCIENTIFIC_FIELDS_CHANGED', 'v1.3 only allowed environment/provenance delta')
    require(ledger['changed_json_paths'] == changed_paths(parent, value), 'AMENDMENT_PATHS', 'exact v1.2->v1.3 changes')
    require(ledger['parent_canonical_sha256'] == PARENT_HASH and ledger['new_canonical_sha256'] == PROTOCOL_HASH
            and ledger['new_JSON_file_byte_sha256'] == PROTOCOL_FILE_HASH
            and ledger['new_MD_file_byte_sha256'] == AMENDMENT_MD_HASH
            and ledger['analysis_environment_amendment_sha256'] == ENVIRONMENT_AMENDMENT_HASH,
            'AMENDMENT_IDENTITY', 'v1.2->v1.3 chain')
    require(ledger['approval_signatures'] == [] and ledger['independent_approval_status'] == 'NOT_INDEPENDENTLY_APPROVED'
            and all(ledger[k] is False for k in ['execution_authorized', 'promotion_authorized',
                'calibration_authorized', 'collection_authorized', 'confirmatory_analysis_authorized', 'new_task15_observations_used']),
            'SCIENTIFIC_APPROVAL', 'pending acceptance and disabled execution')
    return Protocol(canonical(value), repo)


def protocol_binding(protocol: Protocol) -> dict[str, Any]:
    p = protocol.data()
    return {'id': p['protocol_id'], 'version': p['version'], 'canonical_sha256': protocol.identity,
        'file_byte_sha256': PROTOCOL_FILE_HASH, 'preregistration_file_sha256': AMENDMENT_MD_HASH,
        'amendment_ledger_sha256': LEDGER_HASH, 'amendment_ledger_file_sha256': LEDGER_FILE_HASH,
        'schedule_sha256': p['design']['schedule_sha256'], 'diagnostic_schedule_sha256': p['design']['diagnostic_schedule_sha256'],
        'allocator_stack_companions_sha256': p['design']['allocator_stack_companions_sha256'],
        'resolved_diagnostic_order_sha256': RESOLVED_ORDER_HASH,
        'query_identity_namespace_sha256': p['design']['resolved_diagnostic_order']['query_identity_policy']['namespace_protocol_sha256'],
        'scientific_approval': 'NOT_INDEPENDENTLY_APPROVED'}
