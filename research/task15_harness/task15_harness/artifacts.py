from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from .errors import ControlError, require
from .integrity import digest, hash_file
from .protocol import PACKAGE_ROOT, Protocol, AMENDMENT_MD_HASH, LEDGER_HASH

STATUSES = {'VERIFIED', 'MISMATCH', 'MISSING', 'UNREADABLE', 'NOT_CHECKED'}


def inspect_file(identifier: str, path: Path, expected: str, checked: bool = True) -> dict[str, Any]:
    record = {'id': identifier, 'path': str(path), 'expected_sha256': expected,
              'actual_sha256': None, 'bytes': None, 'status': 'NOT_CHECKED', 'detail': ''}
    if not checked:
        return record
    try:
        if not path.exists():
            record.update(status='MISSING', detail='file does not exist')
        elif not path.is_file():
            record.update(status='UNREADABLE', detail='not a regular file')
        else:
            actual, size = hash_file(path)
            record.update(actual_sha256=actual, bytes=size,
                          status='VERIFIED' if actual == expected else 'MISMATCH')
    except FileNotFoundError:
        record.update(status='MISSING', detail='file disappeared')
    except (OSError, ControlError) as exc:
        record.update(status='UNREADABLE', detail=str(exc))
    return record


def specifications(protocol: Protocol) -> list[tuple[str, Path, str]]:
    p = protocol.data()
    specs = []
    for variant, record in p['binaries'].items():
        specs.append((f'binary/{variant}', Path(record['path']), record['sha256']))
    for region, record in p['inputs'].items():
        for prefix in ['graph', 'query_file', 'fixture_manifest', 'native_export']:
            specs.append((f'input/{region}/{prefix}', Path(record[prefix+'_path']), record[prefix+'_sha256']))
    for path, record in p['evidence_files_used'].items():
        if Path(path).name == 'evidence-index.json':
            specs.append(('evidence_index/'+digest(path)[:16], Path(path), record['sha256']))
    for path, expected in p['amendment']['parent_files'].items():
        specs.append(('parent/'+path, protocol.repository/path, expected))
    from .integrity import read_json
    ledger = read_json(protocol.repository/'docs/task15_tail_attribution_amendment_v1.1.0.json')
    specs += [('protocol/active_json', protocol.repository/'docs/task15_tail_attribution_protocol_v1.1.0.json', ledger['new_JSON_file_byte_sha256']),
              ('protocol/active_md', protocol.repository/'docs/task15_tail_attribution_preregistration_v1.1.0.md', AMENDMENT_MD_HASH),
              ('protocol/amendment_ledger', protocol.repository/'docs/task15_tail_attribution_amendment_v1.1.0.json', LEDGER_HASH)]
    return specs


def inspect_identities(protocol: Protocol, checked: bool = True) -> dict[str, Any]:
    records = [inspect_file(*spec, checked=checked) for spec in specifications(protocol)]
    return {'records': records, 'counts': {s: sum(r['status'] == s for r in records) for s in sorted(STATUSES)},
            'all_verified': all(r['status'] == 'VERIFIED' for r in records),
            'future_execution_eligible': False,
            'note': 'Byte identity only. Binaries were not loaded; compiler flags, clocks and instrumentation remain pending.'}


def source_lock() -> dict[str, Any]:
    files = {}
    for path in sorted(PACKAGE_ROOT.rglob('*')):
        if path.is_file() and path.suffix in {'.py', '.json', '.md', '.toml'}:
            files[str(path.relative_to(PACKAGE_ROOT))] = hash_file(path)[0]
    return {'files': files, 'identity_sha256': digest(files)}


def repository_identity(protocol: Protocol) -> dict[str, Any]:
    repository = protocol.repository.resolve()
    environment = {'PATH': os.defpath, 'LC_ALL': 'C', 'LANG': 'C',
                   'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                   'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0'}
    def git(*args: str) -> str:
        # Only fixed read-only Git metadata queries. No subprocess execution facility is exposed.
        try:
            result = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
                                 '-C', str(repository), *args],
                                check=False, capture_output=True, text=True, encoding='utf-8', env=environment, timeout=15)
        except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
            raise ControlError('GIT_METADATA', str(exc)) from exc
        require(result.returncode == 0, 'GIT_METADATA', result.stderr)
        return result.stdout.strip()
    require(Path(git('rev-parse', '--show-toplevel')).resolve() == repository,
            'GIT_METADATA', 'repository root mismatch')
    expected = protocol.data()['runtime_tree_identities']
    actual = {name: git('rev-parse', 'HEAD:'+name) for name in expected}
    protected = ['native','backend','frontend','tools','CMakeLists.txt']
    changes = sorted(set(git('diff','--no-ext-diff','--no-textconv','HEAD','--name-only','--',*protected).splitlines()) |
                     set(git('ls-files','--others','--exclude-standard','--',*protected).splitlines()))
    return {'path': str(protocol.repository), 'commit': git('rev-parse','HEAD'),
            'branch': git('branch','--show-current'), 'origin': git('remote','get-url','origin'),
            'runtime_trees': actual, 'runtime_matches_task14': actual == expected and not changes,
            'protected_worktree_changes': changes,
            'worktree_status': git('status','--porcelain=v1','--untracked-files=all')}


def capacity(protocol: Protocol) -> dict[str, Any]:
    p = protocol.data()
    c = p['calibration']['allocation_capacity_assessment']
    positions = sum(len(x) for x in p['cohorts']['C']['positions_by_region'].values())
    return {'event_cap_per_query': c['new_capacity'], 'event_bytes_max': c['record_size_bytes_max'],
            'selected_positions': positions, 'buffer_bytes_per_worker': c['new_capacity']*c['record_size_bytes_max'],
            'two_worker_buffer_bytes': 2*c['new_capacity']*c['record_size_bytes_max'],
            'worst_timed_C_event_bytes': p['cohorts']['C']['clusters_per_mode']*len(p['binaries'])*positions*c['new_capacity']*c['record_size_bytes_max'],
            'required_storage_bytes': c['storage_preflight_GiB_min']*2**30,
            'allocation_capacity_calibration': 'PENDING', 'buffers_allocated': False}


def inspect_storage(protocol: Protocol, destination: Path | None, *, check_hardlinks: bool = False) -> dict[str, Any]:
    needed = capacity(protocol)['required_storage_bytes']
    if destination is None:
        require(not check_hardlinks, 'STORAGE_DESTINATION', 'hard-link probe requires explicit destination')
        return {'status': 'NOT_CHECKED', 'destination': None, 'required_bytes': needed,
                'free_bytes': None, 'device': None, 'space_reserved': False,
                'verification_scope': 'NOT_CHECKED',
                'hardlink_capability': {'status': 'NOT_CHECKED', 'scope': 'PRIVATE_TINY_PROBE_ONLY', 'detail': ''}}
    destination = destination.resolve(strict=True)
    require(destination.is_dir(), 'STORAGE_DESTINATION', 'explicit existing evidence directory required')
    usage = shutil.disk_usage(destination)
    hardlinks = {'status': 'NOT_CHECKED', 'scope': 'PRIVATE_TINY_PROBE_ONLY', 'detail': ''}
    if check_hardlinks:
        from .output import safe_destination
        safe_destination(protocol, destination/'task15-hardlink-probe')
        try:
            with tempfile.TemporaryDirectory(prefix='.task15-hardlink-', dir=destination) as name:
                folder = Path(name)
                source = folder/'source'
                source.write_bytes(b'task15-capability-probe\n')
                os.link(source, folder/'linked')
                require(source.stat().st_ino == (folder/'linked').stat().st_ino
                        and source.read_bytes() == (folder/'linked').read_bytes(),
                        'STORAGE_HARDLINK', 'probe identity mismatch')
            hardlinks['status'] = 'HARDLINK_SUPPORTED_AT_CHECK'
        except (OSError, ControlError) as exc:
            hardlinks.update(status='UNSUPPORTED_OR_DENIED', detail=str(exc))
    return {'hardlink_capability': hardlinks, 'status': 'STORAGE_CAPACITY_VERIFIED' if usage.free >= needed else 'INSUFFICIENT_CAPACITY',
            'destination': str(destination), 'required_bytes': needed, 'free_bytes': usage.free,
            'device': destination.stat().st_dev, 'space_reserved': False,
            'verification_scope': 'POINT_IN_TIME_FREE_SPACE_ONLY',
            'scope': 'instantaneous free-space observation; optional private hard-link probe; no reservation or allocation-capacity calibration'}
