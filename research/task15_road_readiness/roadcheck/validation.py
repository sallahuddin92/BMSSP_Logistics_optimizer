"""Exact comparison and directed shortest-path validation, without native timings."""
import math
import struct
from production_adapter import require
from smoke.contract import safe_diagnostics
from .oracle import bits,vector_identity
from .io import sha


class InvalidResult(ValueError):
    def __init__(self,evidence):
        super().__init__('ROAD_CORRECTNESS_FAILED')
        self.evidence=evidence


def check_path(path,source,target,graph,native,oracle):
    require(type(path) is dict and set(path)=={'reachable','distance','vertices','edges'},'PATH_SCHEMA')
    require(type(path['reachable']) is bool and type(path['vertices']) is list and type(path['edges']) is list,'PATH_TYPES')
    require(all(type(v) is int for v in path['vertices']+path['edges']),'PATH_IDS')
    by_vertex=dict(zip(graph.vertices,native));expected=dict(zip(graph.vertices,oracle))
    require(bits(path['distance'])==bits(expected[target])==bits(by_vertex[target]),'PATH_SHORTEST_COST')
    vs,es=path['vertices'],path['edges']
    if not path['reachable']:
        require(path['distance']==math.inf and not vs and not es,'UNREACHABLE_PATH')
        return
    require(math.isfinite(path['distance']) and len(vs)==len(es)+1 and vs[0]==source and vs[-1]==target,'PATH_ENDPOINTS')
    require(len(set(vs))==len(vs) and all(v in by_vertex for v in vs),'PATH_CYCLE_OR_VERTEX')
    edges={e[0]:e for e in graph.edges};total=0.0
    for u,v,eid in zip(vs,vs[1:],es):
        require(eid in edges and edges[eid][1:3]==(u,v),'DIRECTED_EDGE_ORIENTATION')
        weight=edges[eid][3]
        require(by_vertex[u]+weight==by_vertex[v],'PREDECESSOR_DISTANCE')
        total+=weight
    require(bits(total)==bits(path['distance']),'PATH_SUM')


def validate(result,native_graph,graph,chosen,oracle_record):
    source=chosen['source_id']
    report={'selection':chosen,'oracle_sha256':oracle_record['distance_sha256'],'native_sha256':None,
            'distance_mismatches':[],'paths':[],'diagnostics_without_timing':None,'errors':[]}
    # Collect evidence even on a distance mismatch; never change exact expectations.
    try:
        require(type(result.source) is int and result.source==source and result.belongs_to(native_graph) is True,'RESULT_SOURCE_OR_STORAGE')
        require(result.algorithm=='native_bmssp_2025','RESULT_ALGORITHM')
        raw=result.diagnostics
        for key in ('query_seconds','preprocessing_seconds'):raw.pop(key,None)
        for row in raw.get('profile',{}).values():
            if type(row) is dict:
                row.pop('inclusive_seconds',None);row.pop('exclusive_seconds',None)
        report['diagnostics_without_timing']=raw
        safe_diagnostics(raw)
        native=result.distances
        require(type(native) is list and len(native)==len(graph.vertices),'DISTANCE_LENGTH')
        native_bits,report['native_sha256']=vector_identity(native)
        expected_bits=oracle_record['distances_le_hex']
        require(oracle_record['vertices']==list(graph.vertices) and len(expected_bits)==len(native),'ORACLE_VERTEX_ORDER')
        require(sha(bytes.fromhex(''.join(expected_bits)))==oracle_record['distance_sha256'],'ORACLE_VECTOR_HASH')
        expected=[struct.unpack('<d',bytes.fromhex(v))[0] for v in expected_bits]
        for vertex,actual,wanted in zip(graph.vertices,native_bits,expected_bits):
            if actual!=wanted:
                report['distance_mismatches'].append({'vertex':vertex,'expected_le_hex':wanted,'actual_le_hex':actual})
        require(native[graph.vertices.index(source)]==0.0,'SOURCE_DISTANCE')
        report['native_reachable']=sum(math.isfinite(v) for v in native)
        report['oracle_reachable']=sum(math.isfinite(v) for v in expected)
        for target in chosen['path_targets']:
            try:
                path=result.path(target)
                saved={'target':target,'reachable':path['reachable'],'distance_le_hex':bits(path['distance']),
                       'vertices':list(path['vertices']),'edges':list(path['edges']),'valid':False}
                report['paths'].append(saved)
                check_path(path,source,target,graph,native,expected)
                saved['valid']=True
            except Exception as exc:
                report['errors'].append({'target':target,'type':type(exc).__name__,'message':str(exc)})
        require(report['native_reachable']==report['oracle_reachable'],'REACHABILITY_MISMATCH')
    except Exception as exc:
        report['errors'].append({'type':type(exc).__name__,'message':str(exc)})
    report['first_differing_vertex']=report['distance_mismatches'][0] if report['distance_mismatches'] else None
    report['valid']=not report['errors'] and not report['distance_mismatches'] and len(report['paths'])==4 and all(p['valid'] for p in report['paths'])
    if not report['valid']:raise InvalidResult(report)
    return report
