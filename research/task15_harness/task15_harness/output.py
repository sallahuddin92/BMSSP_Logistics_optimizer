from __future__ import annotations
import hashlib
import os
import re
from pathlib import Path
from typing import Iterable
from .errors import ControlError, require
from .integrity import canonical, read_json, hash_file, strict_json_bytes, schema_check
from .protocol import Protocol, PACKAGE_ROOT


def safe_destination(protocol: Protocol, destination: Path) -> Path:
    dest = destination.absolute()
    resolved = dest.resolve()
    protected = [protocol.repository]
    protected += [Path(record['path']).parent for record in protocol.data()['binaries'].values()]
    protected.append(Path(protocol.data()['audit_artifacts']['independent_review']))
    for key in protocol.data()['evidence_files_used']:
        if Path(key).name == 'evidence-index.json':
            protected.append(Path(key).parent)
    amendment = protocol.data().get('analysis_environment_amendment')
    if amendment is not None:
        protected += [Path(amendment['replacement']['environment_path']).parent,
                      Path(amendment['numpy']['offline_source']),
                      Path(amendment['historical_recovery']['original_executable']).parents[1],
                      Path(amendment['historical_recovery']['evidence_manifest']['path']).parent]
    for root in protected:
        require(not resolved.is_relative_to(root.resolve()), 'OUTPUT_PROTECTED', str(root))
    return dest


def create_bundle(protocol: Protocol, destination: Path,
                  files: dict[str, bytes | Iterable[bytes]]) -> None:
    """Exclusive directory, atomic files, completion marker LAST. Never reuse incomplete runs."""
    require(bool(files) and all(re.fullmatch(r'[a-z0-9][a-z0-9_.-]*', name)
            and name not in {'.', '..'} for name in files), 'OUTPUT_NAME', 'safe lowercase payload names required')
    dest = safe_destination(protocol, destination)
    try:
        dest.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ControlError('OUTPUT_EXISTS', str(dest)) from exc
    except OSError as exc:
        raise ControlError('OUTPUT_UNWRITABLE', str(exc)) from exc
    ledger = {}
    try:
        for name, content in files.items():
            require(Path(name).name == name and name not in {'COMPLETED.json', 'INTERRUPTED.json'},
                    'OUTPUT_NAME', name)
            temporary = dest/('.'+name+'.partial')
            h = hashlib.sha256()
            with temporary.open('xb') as stream:
                chunks = [content] if isinstance(content, bytes) else content
                for block in chunks:
                    require(type(block) is bytes, 'OUTPUT_TYPE', name)
                    stream.write(block)
                    h.update(block)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, dest/name)  # link is atomic and refuses replacement
            temporary.unlink()
            ledger[name] = h.hexdigest()
        marker = canonical({'schema_version': '1', 'files_sha256': ledger,
                            'scope': 'CONTROL_PLANE_ONLY_NOT_MEASUREMENT'})+b'\n'
        tmp = dest/'.completion.partial'
        with tmp.open('xb') as stream:
            stream.write(marker)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(tmp, dest/'COMPLETED.json')
        tmp.unlink()
        fd = os.open(dest, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException as exc:
        # A partial directory is retained for audit, not deleted/retried. Readers reject it.
        try:
            with (dest/'INTERRUPTED.json').open('xb') as interruption:
                interruption.write(canonical({'scope': 'CONTROL_PLANE_ONLY',
                    'error': type(exc).__name__, 'detail': str(exc), 'completed': False})+b'\n')
        except OSError:
            pass
        raise ControlError('OUTPUT_INTERRUPTED', f'{dest}: {exc}') from exc


SUPPORTED_PAYLOAD_SETS = tuple(map(frozenset, [
    {'manifest.json'}, {'report.json'}, {'report.json', 'plan.json'},
    {'report.json', 'plan.json', 'queries.jsonl'},
    {'report.json', 'synthetic-events.jsonl'}, {'tests.json', 'tests.log'}]))


def read_bundle(path: Path, *, expected_payloads: set[str] | None = None) -> dict[str, str]:
    """Validate a closed inventory. Hashes detect modification, not authentication."""
    require(not (path/'INTERRUPTED.json').exists() and (path/'COMPLETED.json').is_file(),
            'BUNDLE_INCOMPLETE', str(path))
    require(not (path/'COMPLETED.json').is_symlink(), 'BUNDLE_PAYLOAD_REFERENCE', 'marker symlink')
    try:
        marker = read_json(path/'COMPLETED.json')
        schema_check(marker, read_json(PACKAGE_ROOT/'schemas/completion-1.schema.json'))
    except ControlError as exc:
        raise ControlError('BUNDLE_MARKER_SCHEMA', str(exc)) from exc
    require(type(marker) is dict and set(marker) == {'schema_version', 'files_sha256', 'scope'},
            'BUNDLE_MARKER_SCHEMA', 'closed completion marker')
    require(marker['schema_version'] == '1' and marker['scope'] == 'CONTROL_PLANE_ONLY_NOT_MEASUREMENT'
            and type(marker['files_sha256']) is dict and bool(marker['files_sha256']),
            'BUNDLE_MARKER_SCHEMA', 'version, scope and nonempty inventory required')
    inventory = marker['files_sha256']
    for name, expected in inventory.items():
        require(re.fullmatch(r'[a-z0-9][a-z0-9_.-]*', name) is not None
                and name not in {'.', '..', 'COMPLETED.json', 'INTERRUPTED.json'},
                'BUNDLE_PAYLOAD_NAME', name)
        require(type(expected) is str and re.fullmatch(r'[0-9a-f]{64}', expected) is not None,
                'BUNDLE_HASH_FORMAT', name)
    require(len({n.casefold() for n in inventory}) == len(inventory), 'BUNDLE_PAYLOAD_NAME', 'aliases')
    require(set(inventory) == expected_payloads if expected_payloads is not None
            else frozenset(inventory) in SUPPORTED_PAYLOAD_SETS,
            'BUNDLE_PAYLOAD_SET', 'consumer requires an exact supported inventory')
    try:
        actual = {p.name for p in path.iterdir()}
        require(not (set(inventory) - actual), 'BUNDLE_PAYLOAD_MISSING', 'declared payload absent')
        require(actual == set(inventory) | {'COMPLETED.json'}, 'BUNDLE_UNEXPECTED_PAYLOAD', 'unlisted entry')
        inodes = set()
        for name, expected in inventory.items():
            payload = path/name
            require(payload.is_file() and not payload.is_symlink(), 'BUNDLE_PAYLOAD_REFERENCE', name)
            stat = payload.stat()
            inode = (stat.st_dev, stat.st_ino)
            require(inode not in inodes, 'BUNDLE_PAYLOAD_REFERENCE', 'aliased payload')
            inodes.add(inode)
            require(hash_file(payload)[0] == expected, 'BUNDLE_HASH', name)
    except OSError as exc:
        raise ControlError('BUNDLE_UNREADABLE', str(exc)) from exc
    return inventory


def read_bundle_json(path: Path, name: str, *, expected_payloads: set[str]) -> object:
    inventory = read_bundle(path, expected_payloads=expected_payloads)
    require(name in inventory, 'BUNDLE_PAYLOAD_SET', name)
    try:
        with (path/name).open('rb') as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
    except OSError as exc:
        raise ControlError('BUNDLE_UNREADABLE', str(exc)) from exc
    require(len(raw) <= 8 * 1024 * 1024, 'JSON_SIZE', name)
    require(hashlib.sha256(raw).hexdigest() == inventory[name], 'BUNDLE_HASH', name)
    return strict_json_bytes(raw)  # parse exactly the bytes whose hash was checked
