from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from .errors import ControlError, require


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_json_bytes(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            require(key not in out, 'JSON_DUPLICATE_KEY', key)
            out[key] = value
        return out
    def invalid(value: str) -> Any:
        raise ControlError('JSON_NONFINITE', value)
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ControlError('JSON_PARSE', str(exc)) from exc


def read_json(path: Path) -> Any:
    try:
        with path.open('rb') as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        require(len(raw) <= 8 * 1024 * 1024, 'JSON_SIZE', str(path))
        return strict_json_bytes(raw)
    except OSError as exc:
        raise ControlError('INPUT_UNREADABLE', f'{path}: {exc}') from exc


def hash_file(path: Path) -> tuple[str, int]:
    """Streaming file identity. A changing file is not certified."""
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        require(before.st_mode & 0o444 != 0, 'FILE_UNREADABLE', str(path))
        h = hashlib.sha256()
        count = 0
        while block := stream.read(1024 * 1024):
            h.update(block)
            count += len(block)
        after = os.fstat(stream.fileno())
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
             before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size,
             after.st_mtime_ns, after.st_ctime_ns) and count == after.st_size,
            'FILE_CHANGED', str(path))
    current = path.stat()
    require((current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            'FILE_CHANGED', str(path))
    return h.hexdigest(), count


def schema_check(value: Any, schema: dict[str, Any], path: str = '$') -> None:
    """Closed JSON Schema subset used by bundled schemas; unsupported rules fail closed."""
    allowed = {'$schema', 'title', 'description', 'type', 'properties', 'required',
               'additionalProperties', 'items', 'anyOf', 'enum'}
    require(set(schema) <= allowed, 'SCHEMA_UNSUPPORTED', path)
    if 'anyOf' in schema:
        failures = []
        for branch in schema['anyOf']:
            try:
                schema_check(value, branch, path)
                return
            except ControlError as exc:
                failures.append(exc.code)
        raise ControlError('SCHEMA_VARIANT', f'{path}: {failures}')
    typ = schema.get('type')
    valid = {None: True, 'object': type(value) is dict, 'array': type(value) is list,
             'string': type(value) is str, 'integer': type(value) is int,
             'number': type(value) in (int, float), 'boolean': type(value) is bool,
             'null': value is None}
    require(typ in valid and valid[typ], 'SCHEMA_TYPE', f'{path}: expected {typ}')
    if 'enum' in schema:
        require(value in schema['enum'], 'SCHEMA_ENUM', path)
    if typ == 'object':
        require(set(schema.get('required', [])) <= set(value), 'SCHEMA_REQUIRED', path)
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False:
            require(set(value) <= set(props), 'SCHEMA_UNKNOWN', path)
        for key, item in value.items():
            if key in props:
                schema_check(item, props[key], f'{path}.{key}')
    elif typ == 'array':
        for i, item in enumerate(value):
            schema_check(item, schema.get('items', {}), f'{path}[{i}]')
