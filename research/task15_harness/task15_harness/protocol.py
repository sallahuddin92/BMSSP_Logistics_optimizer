from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from .errors import ControlError, require
from .integrity import canonical, digest, hash_file, read_json, schema_check, strict_json_bytes
from .schedule import validate_schedule

PROTOCOL_HASH = 'c41e45bccb68abdf03bab40ea793837a7f508fde17634c1aa8b358a3d82fceb0'
PROTOCOL_FILE_HASH = '4baf6b032fcb40a9859e1a12da319bf1a913f4634111358c53b51c5471b9bf2b'
PARENT_HASH = '6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f'
ORIGINAL_HASH = '590838e4fdde2dcd86228fe0c521845e479fcc6372fa39d3745cb21270ce8247'
LEDGER_HASH = '40ac6b8f91b24852f92f4e093d2acdf8434bff73e5bb32dce7fc87482edaf4f1'  # canonical identity
LEDGER_FILE_HASH = '84e8f34e5c47495a101ed503054747fe67fce6f1905e1a1bc3a47a395df3ee87'
AMENDMENT_MD_HASH = '71c3c85c57416fa0361a6bc4285714cb8e41d81a60bf96ebdfbbbed80fd9e109'
RESOLVED_ORDER_HASH = '3e22c8ebfbdb23af04059bece54734844ee58664a3c43abd9170625922cf20ba'
FROZEN_FILES = {
    "docs/task15_tail_attribution_amendment_v1.1.0.json": "8dde76dcb9669148ae47e8b9192c986d5a06821b2fdc5f2bb54914489613910f",
    "docs/task15_tail_attribution_amendment_v1.2.0.json": "84e8f34e5c47495a101ed503054747fe67fce6f1905e1a1bc3a47a395df3ee87",
    "docs/task15_tail_attribution_preregistration.md": "c9ae85657fd94c1d51485f06a2ea6e022d848473e79969354a36ae13cc5330c5",
    "docs/task15_tail_attribution_preregistration_v1.1.0.md": "58e2bcc83724fbbf67a3b6672e1278ec1503863f2d4faec3b5462a986a9bce8c",
    "docs/task15_tail_attribution_preregistration_v1.2.0.md": "71c3c85c57416fa0361a6bc4285714cb8e41d81a60bf96ebdfbbbed80fd9e109",
    "docs/task15_tail_attribution_protocol.json": "081b6f2cb06e59c9a0578b78f9a007be505fef11f2302ae834d4c62dd209ed17",
    "docs/task15_tail_attribution_protocol_v1.1.0.json": "c4debb684c6bf534f9942c3776d994938577270d5c2d9cbee3224cf8be242dfe",
    "docs/task15_tail_attribution_protocol_v1.2.0.json": "4baf6b032fcb40a9859e1a12da319bf1a913f4634111358c53b51c5471b9bf2b"
}
PACKAGE_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Protocol:
    """Owns immutable canonical bytes; callers only receive defensive JSON copies."""
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


def canonical_protocol_hash(value: dict[str, Any]) -> str:
    unsigned = strict_json_bytes(canonical(value))
    unsigned['identity'].pop('sha256')
    return digest(unsigned)


def changed_paths(a: Any, b: Any, path: str = '') -> list[str]:
    if type(a) is dict and type(b) is dict:
        paths = []
        for key in sorted(a.keys() | b.keys()):
            pointer = path+'/'+key.replace('~', '~0').replace('/', '~1')
            paths.extend([pointer] if key not in a or key not in b else changed_paths(a[key], b[key], pointer))
        return paths
    return [] if canonical(a) == canonical(b) else [path]


def validate_document(value: dict[str, Any]) -> dict[str, Any]:
    require(type(value) is dict, 'SCHEMA_TYPE', 'protocol object')
    require(value.get('version') == '1.2.0', 'PROTOCOL_VERSION', str(value.get('version')))
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
    schema_check(value, read_json(PACKAGE_ROOT/'schemas/protocol-1.2.0.schema.json'))
    report = validate_schedule(value)
    from .ordering import validate_resolved_order
    validate_resolved_order(value)
    amendment = value['ordering_amendment']
    require(amendment['parent_version'] == '1.1.0' and amendment['parent_canonical_sha256'] == PARENT_HASH
            and amendment['parent_commit'] == '367bbdefd279c8dc6673ed03e5bdc9f57031a08f',
            'AMENDMENT_IDENTITY', 'parent scheduling amendment')
    require(amendment['approval_status'] == 'NOT_INDEPENDENTLY_APPROVED'
            and amendment['new_task15_observations_used'] is False,
            'SCIENTIFIC_APPROVAL', 'no independent approval or observations inferred')
    require(canonical_protocol_hash(value) == value['identity']['sha256'] == PROTOCOL_HASH,
            'PROTOCOL_HASH', 'canonical frozen v1.2 identity')
    require(value['design']['resolved_diagnostic_order_sha256'] == RESOLVED_ORDER_HASH,
            'ORDER_HASH', 'pinned resolved-order identity')
    return report


def verify_file_bytes(path: Path, expected: str, code: str) -> None:
    try:
        actual = hash_file(path)[0]
    except OSError as exc:
        raise ControlError(code, str(path)) from exc
    require(actual == expected, code, str(path))


def load_protocol(repo: Path) -> Protocol:
    repo = repo.resolve()
    path = repo/'docs/task15_tail_attribution_protocol_v1.2.0.json'
    value = read_json(path)
    validate_document(value)
    verify_file_bytes(path, PROTOCOL_FILE_HASH, 'PROTOCOL_FILE_HASH')
    verify_file_bytes(repo/'docs/task15_tail_attribution_preregistration_v1.2.0.md',
                      AMENDMENT_MD_HASH, 'FROZEN_FILE_HASH')
    ledger_path = repo/'docs/task15_tail_attribution_amendment_v1.2.0.json'
    ledger = read_json(ledger_path)
    require(type(ledger) is dict, 'AMENDMENT_HASH', 'ledger object required')
    unsigned = strict_json_bytes(canonical(ledger))
    stored = unsigned.pop('identity_sha256', None)
    require(stored == digest(unsigned) == LEDGER_HASH, 'AMENDMENT_HASH', 'canonical ledger identity')
    verify_file_bytes(ledger_path, LEDGER_FILE_HASH, 'AMENDMENT_FILE_HASH')
    for filename, expected in FROZEN_FILES.items():
        try:
            actual = hash_file(repo/filename)[0]
        except OSError as exc:
            raise ControlError('HISTORICAL_FILE_MISSING', filename) from exc
        require(actual == expected, 'FROZEN_FILE_HASH', filename)
    parent = read_json(repo/'docs/task15_tail_attribution_protocol_v1.1.0.json')
    original = read_json(repo/'docs/task15_tail_attribution_protocol.json')
    require(canonical_protocol_hash(parent) == parent['identity']['sha256'] == PARENT_HASH,
            'PARENT_HASH', 'v1.1 canonical')
    require(canonical_protocol_hash(original) == original['identity']['sha256'] == ORIGINAL_HASH,
            'PARENT_HASH', 'v1.0 canonical')
    previous = read_json(repo/'docs/task15_tail_attribution_amendment_v1.1.0.json')
    require(previous['parent_canonical_sha256'] == ORIGINAL_HASH and previous['new_canonical_sha256'] == PARENT_HASH
            and parent['amendment']['parent_canonical_sha256'] == ORIGINAL_HASH,
            'AMENDMENT_IDENTITY', 'v1.0 -> v1.1 chain')
    require(ledger['changed_json_paths'] == changed_paths(parent, value), 'AMENDMENT_PATHS', 'exact changed paths')
    require(ledger['new_canonical_sha256'] == PROTOCOL_HASH and ledger['parent_canonical_sha256'] == PARENT_HASH
            and ledger['resolved_diagnostic_order_sha256'] == RESOLVED_ORDER_HASH
            and ledger['new_JSON_file_byte_sha256'] == PROTOCOL_FILE_HASH
            and ledger['new_MD_file_byte_sha256'] == AMENDMENT_MD_HASH,
            'AMENDMENT_IDENTITY', 'v1.1 -> v1.2 chain')
    require(ledger['independent_approval_status'] == 'NOT_INDEPENDENTLY_APPROVED'
            and ledger['approval_signatures'] == [] and ledger['execution_authorized'] is False
            and ledger['promotion_authorized'] is False, 'SCIENTIFIC_APPROVAL', 'unapproved ledger')
    return Protocol(canonical(value), repo)


def protocol_binding(protocol: Protocol) -> dict[str, Any]:
    """Active provenance and legacy identity namespace have distinct meanings."""
    p = protocol.data()
    return {'id': p['protocol_id'], 'version': p['version'], 'canonical_sha256': protocol.identity,
        'file_byte_sha256': PROTOCOL_FILE_HASH, 'preregistration_file_sha256': AMENDMENT_MD_HASH,
        'amendment_ledger_sha256': LEDGER_HASH, 'amendment_ledger_file_sha256': LEDGER_FILE_HASH,
        'schedule_sha256': p['design']['schedule_sha256'],
        'diagnostic_schedule_sha256': p['design']['diagnostic_schedule_sha256'],
        'allocator_stack_companions_sha256': p['design']['allocator_stack_companions_sha256'],
        'resolved_diagnostic_order_sha256': RESOLVED_ORDER_HASH,
        'query_identity_namespace_sha256': p['design']['resolved_diagnostic_order']['query_identity_policy']['namespace_protocol_sha256'],
        'scientific_approval': 'NOT_INDEPENDENTLY_APPROVED'}
