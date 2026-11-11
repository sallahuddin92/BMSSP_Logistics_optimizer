"""Historical Task14 byte conventions; structural checks are not a shortest-path oracle."""
import hashlib
import json
import math
import struct
from . import require

COUNTERS = set('recursive_calls base_calls max_recursion_depth pivot_calls pivot_edge_scans pivots_selected pivot_early_returns relaxed_edges equality_relaxations label_updates completed_vertex_events completed_vertices original_reachable_vertices label_nodes_created label_nodes_materialized transformed_vertices transformed_edges k t root_level'.split())
FRONTIER = set('initializations discards inserts pulls batches splits selection_work pulled_keys peak_keys'.split())
PROFILES = set('label_creation label_comparison find_pivots base_case frontier recursive_bmssp'.split())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def historical_paths(paths):
    # Deliberately retain default separators, ensure_ascii and allow_nan, as archived.
    return sha(json.dumps(paths, sort_keys=True).encode())


def binary64(value):
    require(type(value) is float and not math.isnan(value) and value >= 0, 'DISTANCE_BINARY64')
    return struct.pack('<d', value)


def diagnostics(value):
    require(type(value) is dict and set(value) == COUNTERS | {'frontier', 'profile', 'implementation', 'query_seconds', 'preprocessing_seconds'}, 'DIAGNOSTICS_FIELDS')
    for key in COUNTERS:
        require(type(value[key]) is int and value[key] >= 0, 'DIAGNOSTIC_COUNTER')
    require(type(value['frontier']) is dict and set(value['frontier']) == FRONTIER, 'FRONTIER_FIELDS')
    for v in value['frontier'].values():
        require(type(v) is int and v >= 0, 'FRONTIER_COUNTER')
    for name in ('query_seconds', 'preprocessing_seconds'):
        require(type(value[name]) is float and math.isfinite(value[name]) and value[name] >= 0, 'NATIVE_TIMING')
    require(value['implementation'] == 'BMSSP2025Engine::solve', 'IMPLEMENTATION')
    require(type(value['profile']) is dict and set(value['profile']) == PROFILES, 'PROFILE_FIELDS')
    for row in value['profile'].values():
        require(type(row) is dict and set(row) == {'inclusive_seconds', 'exclusive_seconds', 'calls'}, 'PROFILE_FIELDS')
        require(type(row['calls']) is int and row['calls'] == 0, 'PROFILES_ENABLED')
        require(all(type(row[k]) is float and row[k] == 0 for k in ('inclusive_seconds', 'exclusive_seconds')), 'PROFILES_ENABLED')
    require(value['label_nodes_materialized'] == value['label_updates']+1 <= value['label_nodes_created'], 'MATERIALIZATION')
    # Detach from binding-owned dictionaries; validation guarantees primitive-only JSON.
    return json.loads(canonical(value))


def evidence(result, native_graph, graph, source, targets, protocol_kind):
    require(result.belongs_to(native_graph) is True and type(result.source) is int and result.source == source, 'RESULT_GRAPH_SOURCE')
    require(result.algorithm == 'native_bmssp_2025', 'RESULT_ALGORITHM')
    d = diagnostics(result.diagnostics)
    distances = result.distances  # Exactly one binding-owned vector copy, outside timing.
    require(len(distances) == len(graph.vertices), 'DISTANCE_LENGTH')
    encoded = b''.join(binary64(x) for x in distances)
    by_vertex = dict(zip(graph.vertices, distances))
    require(by_vertex[source] == 0, 'SOURCE_DISTANCE')
    edges = {e[0]: e for e in graph.edges}
    require(len(targets) == 4 and all(t in by_vertex for t in targets), 'PATH_TARGETS')
    paths = []
    summaries = []
    for target in targets:
        path = result.path(target)
        require(type(path) is dict and set(path) == {'reachable', 'distance', 'vertices', 'edges'}, 'PATH_FIELDS')
        require(type(path['reachable']) is bool and type(path['vertices']) is list and type(path['edges']) is list, 'PATH_TYPES')
        require(all(type(v) is int for v in path['vertices']+path['edges']), 'PATH_IDS')
        require(binary64(path['distance']) == binary64(by_vertex[target]), 'PATH_DISTANCE')
        if not path['reachable']:
            require(path['distance'] == math.inf and not path['vertices'] and not path['edges'], 'UNREACHABLE_PATH')
        else:
            vs, es = path['vertices'], path['edges']
            require(math.isfinite(path['distance']) and len(vs) == len(es)+1 and vs[0] == source and vs[-1] == target, 'PATH_ENDPOINTS')
            require(len(set(vs)) == len(vs) and all(v in by_vertex for v in vs), 'PATH_CYCLE_OR_VERTEX')
            total = 0.0
            for u, v, eid in zip(vs, vs[1:], es):
                require(eid in edges and edges[eid][1:3] == (u, v), 'PATH_EDGE_ORIENTATION')
                w = edges[eid][3]
                require(math.isfinite(by_vertex[u]+w) and by_vertex[u]+w == by_vertex[v], 'PATH_PREDECESSOR_DISTANCE')
                total += w
            require(math.isfinite(total) and total == path['distance'], 'PATH_SUM')
        paths.append(path)
        summaries.append({'target': target, 'reachable': path['reachable'], 'distance_le_hex': binary64(path['distance']).hex(),
                          'vertices': list(path['vertices']), 'edges': list(path['edges']), 'path_sha256': historical_paths(path)})
    work = {k: v for k, v in d.items() if k not in {'query_seconds', 'preprocessing_seconds', 'profile'}}
    require(protocol_kind in {'P1', 'P2'}, 'PROTOCOL_KIND')
    historical = {k: v for k, v in work.items() if protocol_kind != 'P1' or k != 'label_nodes_materialized'}
    return {'diagnostics': d, 'legacy_query_seconds': d['query_seconds'], 'distance_sha256': sha(encoded),
            'paths_sha256': historical_paths(paths), 'paths': summaries, 'work': work, 'work_sha256': sha(canonical(work)),
            'historical_work': historical, 'materialization_count': d['label_nodes_materialized']}


def validate_evidence(proof, query, inp):
    require(type(proof) is dict and set(proof) == {'diagnostics','legacy_query_seconds','distance_sha256','paths_sha256','paths','work','work_sha256','historical_work','materialization_count'}, 'EVIDENCE_SCHEMA')
    d = diagnostics(proof['diagnostics'])
    for name in ('distance_sha256','paths_sha256','work_sha256'):
        value = proof[name]
        require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'FINGERPRINT_FORMAT')
    require(proof['legacy_query_seconds'] == d['query_seconds'], 'LEGACY_DIAGNOSTIC_CHANGED')
    work = {k:v for k,v in d.items() if k not in {'query_seconds','preprocessing_seconds','profile'}}
    historical = {k:v for k,v in work.items() if query['protocol'] != 'P1' or k != 'label_nodes_materialized'}
    require(canonical(proof['work']) == canonical(work) and proof['work_sha256'] == sha(canonical(work)), 'WORK_FINGERPRINT')
    require(canonical(proof['historical_work']) == canonical(historical) and proof['materialization_count'] == d['label_nodes_materialized'], 'WORK_CONVENTION')
    require(type(proof['paths']) is list and len(proof['paths']) == 4, 'PATH_COUNT')
    raw = []
    for summary, target in zip(proof['paths'], inp['path_targets']):
        require(type(summary) is dict and set(summary) == {'target','reachable','distance_le_hex','vertices','edges','path_sha256'}, 'PATH_SUMMARY_SCHEMA')
        require(type(summary['target']) is int and summary['target'] == int(target), 'PATH_TARGET_IDENTITY')
        bits = summary['distance_le_hex']
        require(type(bits) is str and len(bits) == 16 and all(c in '0123456789abcdef' for c in bits), 'PATH_DISTANCE_ENCODING')
        distance = struct.unpack('<d', bytes.fromhex(bits))[0]
        binary64(distance)
        path = {'reachable':summary['reachable'],'distance':distance,'vertices':summary['vertices'],'edges':summary['edges']}
        require(type(path['reachable']) is bool and type(path['vertices']) is list and type(path['edges']) is list, 'PATH_TYPES')
        require(all(type(x) is int for x in path['vertices']+path['edges']), 'PATH_IDS')
        if path['reachable']:
            require(math.isfinite(distance) and len(path['vertices']) == len(path['edges'])+1 and
                    path['vertices'][0] == int(query['source_id']) and path['vertices'][-1] == int(target), 'PATH_ENDPOINTS')
        else:
            require(distance == math.inf and not path['vertices'] and not path['edges'], 'UNREACHABLE_PATH')
        require(summary['path_sha256'] == historical_paths(path), 'PATH_FINGERPRINT')
        raw.append(path)
    require(proof['paths_sha256'] == historical_paths(raw), 'PATHS_FINGERPRINT')
    return proof
