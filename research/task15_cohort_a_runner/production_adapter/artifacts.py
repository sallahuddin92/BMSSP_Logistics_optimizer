"""Read-only original Mach-O identity checks, independent of dynamic loading."""
import hashlib
import platform
import struct
import sys
from pathlib import Path
from . import require


def macho(data):
    require(len(data) >= 32, 'MACHO_HEADER')
    magic, cpu, _, _, ncmds, size, _, _ = struct.unpack_from('<8I', data)
    require(magic == 0xfeedfacf and cpu == 0x0100000c, 'ARCHITECTURE_NOT_ARM64')
    require(32 + size <= len(data), 'MACHO_COMMAND_BOUNDS')
    cursor = 32
    dependencies = []
    uuid = None
    for _ in range(ncmds):
        require(cursor + 8 <= 32 + size, 'MACHO_COMMAND_BOUNDS')
        cmd, length = struct.unpack_from('<II', data, cursor)
        require(length >= 8 and cursor + length <= 32 + size, 'MACHO_COMMAND_BOUNDS')
        if cmd == 0x1b:
            require(length == 24 and uuid is None, 'MACHO_UUID')
            uuid = data[cursor+8:cursor+24].hex()
        if cmd in {0xc, 0x80000018, 0x8000001f, 0x20, 0x80000023}:
            require(length >= 24, 'MACHO_DYLIB')
            offset = struct.unpack_from('<I', data, cursor+8)[0]
            require(24 <= offset < length, 'MACHO_DYLIB')
            name = data[cursor+offset:cursor+length]
            require(b'\0' in name, 'MACHO_DYLIB')
            dependencies.append(name.split(b'\0', 1)[0].decode('utf8'))
        cursor += length
    require(cursor == 32+size and uuid is not None, 'MACHO_COMMANDS_OR_UUID')
    return {'architecture': 'arm64', 'uuid': uuid, 'dependencies': dependencies}


def verify_artifact(p, variant, path, *, abi=None, machine=None):
    require(variant in {'baseline', 'candidate'}, 'VARIANT')
    expected = p['binaries'][variant]
    path = Path(path)
    require(str(path) == expected['path'] and str(path.resolve()) == expected['path'] and not path.is_symlink(), 'BINARY_PATH')
    require((abi or sys.implementation.cache_tag) == 'cpython-311', 'CPYTHON_ABI')
    require((machine or platform.machine()) == 'arm64', 'HOST_ARCHITECTURE')
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    require(sha == expected['sha256'], 'BINARY_HASH')
    meta = macho(data)
    require(meta['dependencies'] == ['/usr/lib/libc++.1.dylib', '/usr/lib/libSystem.B.dylib'], 'BINARY_DEPENDENCIES')
    return {**expected, **meta, 'variant': variant, 'dependency_resolution': 'NOT_LOADED',
            'dependency_runtime_identities': None}
