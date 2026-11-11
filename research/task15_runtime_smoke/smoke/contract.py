"""Independent fixed expectations; pure checks, with no graph algorithms or clocks."""
import math
import struct
from production_adapter import require
from production_adapter.fingerprints import COUNTERS, FRONTIER, PROFILES

VERTICES = (0,1,2,3,4,5)
EDGES = ((10,0,1,2.0),(11,1,2,3.0),(12,0,3,10.0),(13,2,3,1.0),
         (14,3,4,2.0),(15,1,4,20.0),(16,4,1,5.0))
SOURCES = (0,3)
EXPECTATIONS = {
    0: {'distances':(0.0,2.0,5.0,6.0,8.0,math.inf), 'target':4,
        'vertices':[0,1,2,3,4], 'edges':[10,11,13,14]},
    3: {'distances':(math.inf,7.0,10.0,0.0,2.0,math.inf), 'target':2,
        'vertices':[3,4,1,2], 'edges':[14,16,11]}}
TIMINGS = {'query_seconds','preprocessing_seconds'}


def bits(value):
    require(type(value) is float and not math.isnan(value) and value >= 0, 'DISTANCE_TYPE_OR_RANGE')
    return struct.pack('<d',value).hex()


def safe_diagnostics(d):
    # Do not bind, copy, retain or report either native timing value.
    for name in TIMINGS:
        d.pop(name,None)
    require(type(d) is dict and set(d) == COUNTERS | {'frontier','profile','implementation'}, 'DIAGNOSTIC_FIELDS')
    require(all(type(d[k]) is int and d[k] >= 0 for k in COUNTERS), 'DIAGNOSTIC_COUNTER')
    require(d['implementation'] == 'BMSSP2025Engine::solve', 'IMPLEMENTATION')
    require(type(d['frontier']) is dict and set(d['frontier']) == FRONTIER, 'FRONTIER_FIELDS')
    require(all(type(v) is int and v >= 0 for v in d['frontier'].values()), 'FRONTIER_COUNTER')
    require(type(d['profile']) is dict and set(d['profile']) == PROFILES, 'PROFILE_FIELDS')
    for row in d['profile'].values():
        # Profiling durations are not retained either, even though disabled.
        row.pop('inclusive_seconds',None)
        row.pop('exclusive_seconds',None)
        require(set(row) == {'calls'} and type(row['calls']) is int and row['calls'] == 0, 'PROFILE_ENABLED')
    require(d['label_nodes_materialized'] == d['label_updates']+1 <= d['label_nodes_created'], 'MATERIALIZATION')
    return d


def validate_result(result,graph,source):
    require(type(source) is int and source in SOURCES, 'UNAUTHORIZED_SOURCE')
    require(result.source == source and type(result.source) is int and result.belongs_to(graph) is True, 'RESULT_SOURCE_OR_GRAPH')
    require(result.algorithm == 'native_bmssp_2025','RESULT_ALGORITHM')
    expected = EXPECTATIONS[source]
    actual = result.distances
    require(type(actual) is list and len(actual) == len(VERTICES), 'DISTANCE_LENGTH')
    actual_bits = [bits(v) for v in actual]
    expected_bits = [bits(v) for v in expected['distances']]
    require(actual_bits == expected_bits,'DISTANCE_MISMATCH')
    path = result.path(expected['target'])
    require(type(path) is dict and set(path) == {'reachable','distance','vertices','edges'}, 'PATH_FIELDS')
    require(path['reachable'] is True and path['vertices'] == expected['vertices'] and path['edges'] == expected['edges'], 'DIRECTED_PATH_MISMATCH')
    require(all(type(v) is int for v in path['vertices']+path['edges']), 'PATH_ID_TYPE')
    require(bits(path['distance']) == expected_bits[expected['target']], 'PATH_DISTANCE')
    edge_map = {e[0]:e for e in EDGES}
    total = 0.0
    for u,v,eid in zip(path['vertices'],path['vertices'][1:],path['edges']):
        edge = edge_map[eid]
        require(edge[1:3] == (u,v), 'EDGE_ORIENTATION')
        total += edge[3]
    require(bits(total) == bits(path['distance']), 'PATH_WEIGHT')
    unreachable = result.path(5)
    require(unreachable == {'reachable':False,'distance':math.inf,'vertices':[],'edges':[]}, 'UNREACHABLE_PATH')
    d = safe_diagnostics(result.diagnostics)
    # Primitive copies only; no DistanceResult or full timing diagnostic escapes.
    return {'source':source,'status':'CORRECT','distances_le_hex':actual_bits,
            'expected_distances_le_hex':expected_bits,'distances_display':[v if math.isfinite(v) else '+Infinity' for v in actual],
            'target':expected['target'],'directed_path':{'vertices':list(path['vertices']),'edges':list(path['edges']),'distance_le_hex':bits(path['distance'])},
            'expected_directed_path':{'vertices':expected['vertices'],'edges':expected['edges']},
            'unreachable_target':5,'unreachable_correct':True,'diagnostics_without_timing':d}


class Budget:
    """One graph, one engine, exactly the two prescribed sources; no retry after failure."""
    def __init__(self): self.cursor = 0; self.failed = False
    def before_solve(self,source):
        require(not self.failed and self.cursor < 2, 'SOLVE_BUDGET_EXHAUSTED')
        require(type(source) is int and source == SOURCES[self.cursor], 'UNAUTHORIZED_SOURCE_ORDER')
        self.cursor += 1
