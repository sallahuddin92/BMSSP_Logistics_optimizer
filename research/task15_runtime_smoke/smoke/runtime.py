"""Only the Phase 6 fixed fixture is executable here; production gate is untouched."""
import gc
import importlib.machinery
import importlib.util
import os
import platform
from pathlib import Path
import sys
import traceback
import weakref
from production_adapter import require
from production_adapter.artifacts import verify_artifact
from production_adapter.loading import import_verified
from .contract import VERTICES,EDGES,SOURCES,Budget,validate_result
from .dependencies import loaded_images,verify_dependencies
from .io import event,publish


def preflight(p,variant):
    require(sys.implementation.name == 'cpython' and sys.version_info[:2] == (3,11),'CPYTHON_ABI')
    require(sys.platform == 'darwin' and platform.machine() == 'arm64','HOST_ARCHITECTURE')
    require(sys.flags.isolated == 1 and sys.flags.ignore_environment == 1,'ISOLATED_PYTHON_REQUIRED')
    require(not any(k.startswith(('DYLD_','LD_PRELOAD')) for k in os.environ),'INJECTED_LOADER_ENVIRONMENT')
    require(sys.gettrace() is None and sys.getprofile() is None,'PROFILER_OR_TRACER_ACTIVE')
    require('bmssp_native' not in sys.modules,'NATIVE_MODULE_ALREADY_LOADED')
    return verify_artifact(p,variant,p['binaries'][variant]['path'])


class SmokeImports:
    # Constructed only after runtime preflight in a private, one-variant child.
    def __init__(self,p,variant,identity):
        self.p,self.variant,self.identity = p,variant,identity
        self.registry = sys.modules
    def create(self,path):
        require(path == self.p['binaries'][self.variant]['path'],'BINARY_PATH')
        self.loader = importlib.machinery.ExtensionFileLoader('bmssp_native',path)
        spec = importlib.util.spec_from_file_location('bmssp_native',path,loader=self.loader)
        return importlib.util.module_from_spec(spec)
    def execute(self,module):self.loader.exec_module(module)
    def verify(self,path):return verify_artifact(self.p,self.variant,path)
    def dependencies(self,names):
        all_images = loaded_images(set(names)|{self.identity['path']},
                                  {b['path'] for v,b in self.p['binaries'].items() if v != self.variant})
        require(all_images[self.identity['path']]['loaded_uuid'] == self.identity['uuid'],'LOADED_EXTENSION_UUID')
        return verify_dependencies({k:all_images[k] for k in names},names)


def ref(value):
    try:return weakref.ref(value)
    except TypeError:return None


def observed_release(reference):
    return {'python_reference_dropped':True,'weakref_supported':reference is not None,
            'weakref_dead':reference() is None if reference is not None else None,
            'limitation':None if reference is not None else 'BINDING_DOES_NOT_SUPPORT_WEAKREF;_NO_COMPLETE_NATIVE_MEMORY_RECLAMATION_PROOF'}


def fixed_queries(module,record):
    graph = engine = result = None
    budget = Budget()
    prior = None
    try:
        graph = module.NativeGraph(VERTICES,EDGES)
        require(tuple(graph.vertex_ids) == VERTICES,'VERTEX_ORDER')
        require(graph.metadata == {'vertex_count':6,'edge_count':7,'directed':True,'immutable':True},'GRAPH_METADATA')
        record({'event':'GRAPH_CONSTRUCTED','vertex_count':6,'edge_count':7})
        engine = module.BMSSP2025Engine(graph)
        metadata = engine.metadata
        metadata.pop('preprocessing_seconds',None)
        require(metadata['preprocessing_count'] == 1,'PREPROCESSING_COUNT')
        record({'event':'ENGINE_CONSTRUCTED','metadata_without_timing':metadata})
        for source in SOURCES:
            require(prior is None or prior() is None,'PREVIOUS_RESULT_RETAINED')
            budget.before_solve(source)
            record({'event':'SOLVE_ATTEMPT','source':source,'attempt':budget.cursor})
            result = engine.solve(source,profile=False)
            # No external clock reads and no copy of native timing fields.
            prior = ref(result)
            checked = validate_result(result,graph,source)
            result = None
            gc.collect()  # Outside any measurement; not a memory reclamation proof.
            release = observed_release(prior)
            require(prior is None or release['weakref_dead'],'RESULT_NOT_RELEASED')
            record({'event':'QUERY_VERIFIED','query':checked,'result_release':release})
        require(budget.cursor == 2,'QUERY_COUNT')
        er,gr = ref(engine),ref(graph)
        engine = None
        graph = None
        gc.collect()
        engine_release,graph_release = observed_release(er),observed_release(gr)
        require(er is None or engine_release['weakref_dead'],'ENGINE_NOT_RELEASED')
        require(gr is None or graph_release['weakref_dead'],'GRAPH_NOT_RELEASED')
        record({'event':'REFERENCES_RELEASED','engine':engine_release,'graph':graph_release,'native_memory_reclamation_proven':False})
        return budget.cursor
    except BaseException:
        budget.failed = True
        raise
    finally:
        result = engine = graph = None


def child(p,variant,directory):
    journal = Path(directory)/(variant+'.events.jsonl')
    record = lambda value:event(journal,{'variant':variant,'pid':os.getpid(),**value})
    attempted = 0
    def counted(value):
        nonlocal attempted
        if value['event'] == 'SOLVE_ATTEMPT': attempted += 1
        record(value)
    try:
        identity = preflight(p,variant)
        record({'event':'PREFLIGHT_PASSED','binary':identity,'interpreter':sys.version,'executable':sys.executable})
        ops = SmokeImports(p,variant,identity)
        module,deps = import_verified(identity,{b['path'] for b in p['binaries'].values()},ops)
        record({'event':'IMPORT_VERIFIED','binary':identity,'dependencies':deps,'loaded_module_path':module.__file__})
        count = fixed_queries(module,counted)
        publish(Path(directory)/(variant+'.receipt.json'),{'variant':variant,'status':'PASS','pid':os.getpid(),'binary':identity,'dependencies':deps,'query_attempts':count,'query_successes':count,'native_timing_values_retained':False})
        return 0
    except BaseException as exc:
        # No locals in traceback: no query/preprocessing timing values are exposed.
        error = {'type':type(exc).__name__,'message':str(exc),'traceback':''.join(traceback.format_exception(exc))}
        record({'event':'SMOKE_FAILED','query_attempts':attempted,'error':error})
        publish(Path(directory)/(variant+'.receipt.json'),{'variant':variant,'status':'FAIL','pid':os.getpid(),'query_attempts':attempted,'error':error,'native_timing_values_retained':False})
        sys.stderr.write(error['traceback'])
        return 3
