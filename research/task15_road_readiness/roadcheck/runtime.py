"""Fixed real-road children, isolated from dormant production dispatch."""
import gc
import json
import os
from pathlib import Path
import sys
import traceback
from production_adapter import require
from production_adapter.loading import import_verified
from smoke.runtime import preflight,SmokeImports,ref,observed_release
from .inputs import REGIONS,Budget,load
from .io import sha,publish,event
from .validation import validate,InvalidResult


def child(p,variant,directory):
    root=Path(directory);attempts=0;chosen=None;identity=None
    graph=native_graph=engine=result=None
    previous=None
    record=lambda value:event(root/(variant+'.events.jsonl'),{'variant':variant,'pid':os.getpid(),**value})
    try:
        identity=preflight(p,variant)
        module,deps=import_verified(identity,{b['path'] for b in p['binaries'].values()},SmokeImports(p,variant,identity))
        record({'event':'IMPORT_VERIFIED','binary_preimport_identity':identity,'loaded_module_path':module.__file__,'dependencies':deps})
        campaign=json.loads((root/'campaign.json').read_bytes())
        budget=Budget(p)
        for region in REGIONS:
            require(previous is None or previous() is None,'PRIOR_RESULT_RETAINED')
            graph,chosen=load(p,region)
            oracle_data=(root/(region+'.oracle.json')).read_bytes()
            require(sha(oracle_data)==campaign['oracle_files'][region],'ORACLE_FILE_HASH')
            oracle_record=json.loads(oracle_data)
            require(oracle_record['selection']==chosen,'ORACLE_SELECTION')
            native_graph=module.NativeGraph(graph.vertices,graph.edges)
            require(tuple(native_graph.vertex_ids)==graph.vertices,'NATIVE_VERTEX_ORDER')
            engine=module.BMSSP2025Engine(native_graph)
            metadata=engine.metadata;metadata.pop('preprocessing_seconds',None)
            require(metadata['preprocessing_count']==1,'PREPROCESSING_COUNT')
            record({'event':'GRAPH_PREPARED','selection':chosen,'metadata_without_timing':metadata})
            budget.claim(region,chosen['source_id']);attempts+=1
            record({'event':'SOLVE_ATTEMPT','selection':chosen,'attempt':attempts})
            result=engine.solve(chosen['source_id'],profile=False)
            previous=ref(result)
            proof=validate(result,native_graph,graph,chosen,oracle_record)
            result=None;oracle_record=None;oracle_data=None
            gc.collect()
            release=observed_release(previous)
            require(previous is None or release['weakref_dead'],'RESULT_RETAINED')
            er,gr=ref(engine),ref(native_graph)
            engine=native_graph=graph=None;gc.collect()
            engine_release,graph_release=observed_release(er),observed_release(gr)
            require(er is None or engine_release['weakref_dead'],'ENGINE_RETAINED')
            require(gr is None or graph_release['weakref_dead'],'GRAPH_RETAINED')
            record({'event':'QUERY_VERIFIED','evidence':proof,'result_release':release,'engine_release':engine_release,'graph_release':graph_release})
            proof=None
        require(attempts==3,'QUERY_COUNT')
        publish(root/(variant+'.receipt.json'),{'variant':variant,'pid':os.getpid(),'status':'PASS','query_attempts':attempts,'binary_preimport_identity':identity,'dependencies':deps})
        return 0
    except BaseException as exc:
        error={'type':type(exc).__name__,'message':str(exc),'traceback':''.join(traceback.format_exception(exc))}
        failure={'variant':variant,'pid':os.getpid(),'status':'FAIL','query_attempts':attempts,'selection':chosen,'binary_preimport_identity':identity,'error':error,
                 'invalid_result_evidence':exc.evidence if isinstance(exc,InvalidResult) else None}
        record({'event':'FAILURE',**failure})
        publish(root/(variant+'.receipt.json'),failure)
        sys.stderr.write(error['traceback'])
        return 3
    finally:result=engine=native_graph=graph=None
