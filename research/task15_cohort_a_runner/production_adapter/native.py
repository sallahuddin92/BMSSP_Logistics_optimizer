"""Actual production operations. Every dangerous operation has an unconditional gate."""
from . import production_gate, require
from .artifacts import verify_artifact


class NativeClock:
    synthetic = False
    metadata = {'api': 'perf_counter_ns', 'units': 'ns', 'representation_ratio': [1, 1],
                'mapping': None, 'effective_quantum': None, 'calibration': 'PENDING'}

    def read(self):
        production_gate()
        import time
        return time.perf_counter_ns()


class NativeBinding:
    synthetic = False

    def __init__(self, p, variant):
        production_gate()
        import os
        import sys
        require(not any(k.startswith(('DYLD_', 'LD_PRELOAD')) for k in os.environ), 'INJECTED_LOADER_ENVIRONMENT')
        require(sys.getprofile() is None and sys.gettrace() is None, 'PROFILER_OR_TRACER_ACTIVE')
        from .loading import import_verified
        self.identity = verify_artifact(p, variant, p['binaries'][variant]['path'])
        ops = NativeImports(p, variant)
        self.module, dependencies = import_verified(self.identity, {b['path'] for b in p['binaries'].values()}, ops)
        self.identity['dependency_runtime_identities'] = dependencies
        self.identity['dependency_resolution'] = 'LOADED_IMAGES_VERIFIED'

    def prepare(self, graph):
        production_gate()
        require(not graph.synthetic, 'PRODUCTION_GRAPH_REQUIRED')
        native_graph = self.module.NativeGraph(graph.vertices, graph.edges)
        require(tuple(native_graph.vertex_ids) == graph.vertices, 'NATIVE_VERTEX_ORDER')
        engine = self.module.BMSSP2025Engine(native_graph)
        require(engine.metadata['preprocessing_count'] == 1, 'PREPROCESSING_COUNT')
        return native_graph, engine

    def solve(self, engine, source, *, profile=False):
        production_gate()
        require(profile is False, 'PROFILING_FORBIDDEN')
        return engine.solve(source, profile=False)


def runtime_dependencies(names):
    """dyld image UUIDs identify shared-cache system libraries; no fabricated file SHA."""
    production_gate()
    import ctypes
    import struct
    dyld = ctypes.CDLL(None)
    dyld._dyld_image_count.restype = ctypes.c_uint32
    dyld._dyld_get_image_name.argtypes = [ctypes.c_uint32]
    dyld._dyld_get_image_name.restype = ctypes.c_char_p
    dyld._dyld_get_image_header.argtypes = [ctypes.c_uint32]
    dyld._dyld_get_image_header.restype = ctypes.c_void_p
    found = {}
    for i in range(dyld._dyld_image_count()):
        name = dyld._dyld_get_image_name(i).decode()
        if name not in names:
            continue
        address = dyld._dyld_get_image_header(i)
        header = ctypes.string_at(address, 32)
        magic, cpu, _, _, count, size, _, _ = struct.unpack('<8I', header)
        require(magic == 0xfeedfacf and cpu == 0x0100000c and size < 16*1024*1024, 'DYLD_HEADER')
        data = ctypes.string_at(address, 32+size)
        cursor = 32
        for _ in range(count):
            require(cursor+8 <= len(data), 'DYLD_COMMAND')
            cmd, length = struct.unpack_from('<II', data, cursor)
            require(length >= 8 and cursor+length <= len(data), 'DYLD_COMMAND')
            if cmd == 0x1b:
                require(length == 24, 'DYLD_UUID')
                found[name] = {'loaded_uuid': data[cursor+8:cursor+24].hex(),
                               'file_sha256': None, 'sha_unavailable_reason': 'SYSTEM_DYLD_IMAGE_UUID_IDENTITY'}
            cursor += length
    require(set(found) == set(names), 'DEPENDENCY_IMAGE_MISSING')
    return found


class NativeImports:
    def __init__(self, p, variant):
        production_gate()
        import sys
        self.registry = sys.modules
        self.p, self.variant = p, variant

    def create(self, path):
        production_gate()
        import importlib.machinery
        import importlib.util
        self.loader = importlib.machinery.ExtensionFileLoader('bmssp_native', path)
        spec = importlib.util.spec_from_file_location('bmssp_native', path, loader=self.loader)
        return importlib.util.module_from_spec(spec)

    def execute(self, module):
        production_gate()
        self.loader.exec_module(module)

    def verify(self, path):
        production_gate()
        return verify_artifact(self.p, self.variant, path)

    def dependencies(self, names):
        production_gate()
        return runtime_dependencies(names)
