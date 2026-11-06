from __future__ import annotations
import hashlib
import os
from pathlib import Path
from typing import Iterable
from .errors import ControlError, require
from .integrity import canonical, read_json, hash_file
from .protocol import Protocol


def safe_destination(protocol: Protocol, destination: Path) -> Path:
    dest = destination.absolute()
    resolved = dest.resolve()
    protected = [protocol.repository]
    protected += [Path(record['path']).parent for record in protocol.data()['binaries'].values()]
    protected.append(Path(protocol.data()['audit_artifacts']['independent_review']))
    for key in protocol.data()['evidence_files_used']:
        if Path(key).name == 'evidence-index.json':
            protected.append(Path(key).parent)
    for root in protected:
        require(not resolved.is_relative_to(root.resolve()), 'OUTPUT_PROTECTED', str(root))
    return dest


def create_bundle(protocol: Protocol, destination: Path,
                  files: dict[str, bytes | Iterable[bytes]]) -> None:
    """Exclusive directory, atomic files, completion marker LAST. Never reuse incomplete runs."""
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


def read_bundle(path: Path) -> dict[str, str]:
    require(not (path/'INTERRUPTED.json').exists() and (path/'COMPLETED.json').is_file(),
            'BUNDLE_INCOMPLETE', str(path))
    marker = read_json(path/'COMPLETED.json')
    for name, expected in marker['files_sha256'].items():
        require(Path(name).name == name, 'OUTPUT_NAME', name)
        require(hash_file(path/name)[0] == expected, 'BUNDLE_HASH', name)
    return marker['files_sha256']
