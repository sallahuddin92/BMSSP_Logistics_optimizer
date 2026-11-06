from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from .errors import require
from .integrity import canonical, digest, hash_file, read_json, schema_check, strict_json_bytes
from .schedule import validate_schedule

PROTOCOL_HASH = '6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f'
PARENT_HASH = '590838e4fdde2dcd86228fe0c521845e479fcc6372fa39d3745cb21270ce8247'
LEDGER_HASH = '8dde76dcb9669148ae47e8b9192c986d5a06821b2fdc5f2bb54914489613910f'
AMENDMENT_MD_HASH = '58e2bcc83724fbbf67a3b6672e1278ec1503863f2d4faec3b5462a986a9bce8c'
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


def validate_document(value: dict[str, Any]) -> dict[str, Any]:
    require(type(value) is dict, 'SCHEMA_TYPE', 'protocol object')
    require(value.get('version') == '1.1.0', 'PROTOCOL_VERSION', str(value.get('version')))
    require(value.get('protocol_id') == 'BMSSP-T15-tail-attribution', 'PROTOCOL_ID', 'identifier')
    require(value.get('execution_authorized') is False and value.get('promotion_authorized') is False,
            'AUTHORIZATION', 'frozen false flags required')
    # Strict row semantics first, so malformed cross-protocol fields have a stable classification.
    for row in value.get('design', {}).get('base_schedule', []):
        if row.get('protocol') == 'P1':
            require('P2_pair_orders_by_region' not in row, 'CROSS_PROTOCOL_FIELD', row.get('id',''))
        elif row.get('protocol') == 'P2':
            require('P1_variant_order' not in row, 'CROSS_PROTOCOL_FIELD', row.get('id',''))
    schema_check(value, read_json(PACKAGE_ROOT/'schemas/protocol-1.1.0.schema.json'))
    report = validate_schedule(value)
    amendment = value['amendment']
    require(amendment['parent_version'] == '1.0.0' and
            amendment['parent_canonical_sha256'] == PARENT_HASH and
            amendment['parent_documentation_commit'] == 'afc1867f57f663ac56104521474c582e72461882',
            'AMENDMENT_IDENTITY', 'parent')
    copy = strict_json_bytes(canonical(value))
    stored = copy['identity'].pop('sha256')
    require(stored == digest(copy) == PROTOCOL_HASH, 'PROTOCOL_HASH', 'canonical frozen identity')
    return report


def load_protocol(repo: Path) -> Protocol:
    repo = repo.resolve()
    path = repo/'docs/task15_tail_attribution_protocol_v1.1.0.json'
    value = read_json(path)
    validate_document(value)
    ledger_path = repo/'docs/task15_tail_attribution_amendment_v1.1.0.json'
    require(hash_file(ledger_path)[0] == LEDGER_HASH, 'AMENDMENT_HASH', str(ledger_path))
    require(hash_file(repo/'docs/task15_tail_attribution_preregistration_v1.1.0.md')[0] == AMENDMENT_MD_HASH,
            'FROZEN_FILE_HASH', 'active preregistration')
    ledger = read_json(ledger_path)
    require(ledger['new_canonical_sha256'] == PROTOCOL_HASH and
            ledger['parent_canonical_sha256'] == PARENT_HASH and
            hash_file(path)[0] == ledger['new_JSON_file_byte_sha256'],
            'AMENDMENT_IDENTITY', 'new protocol file bytes')
    for filename, expected in value['amendment']['parent_files'].items():
        require(hash_file(repo/filename)[0] == expected, 'FROZEN_FILE_HASH', filename)
    parent = read_json(repo/'docs/task15_tail_attribution_protocol.json')
    stored = parent['identity'].pop('sha256')
    require(stored == digest(parent) == PARENT_HASH, 'PARENT_HASH', 'v1.0 canonical')
    return Protocol(canonical(value), repo)
