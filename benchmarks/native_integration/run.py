"""Bounded offline integration measurements; no production graph substitution.

Run with the compiled extension and backend on PYTHONPATH. Prints JSON only.
"""
import argparse
import json
import logging
import platform
import random
import resource
import statistics
import time
from unittest.mock import patch
import networkx as nx
from fastapi.testclient import TestClient
import bmssp_native
import api
from native_graph import SnapshotCache, snapshot_cache
from routing_adapter import compute_native_matrix


def fixture(family):
    n = 48 if family == 'sparse' else 64
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(5_000_000_000 + i for i in range(n))
    ids = list(graph)
    if family == 'chain':
        for a, b in zip(ids, ids[1:]):
            graph.add_edge(a, b, length=1.25)
    elif family == 'hub':
        for i, b in enumerate(ids[1:]):
            graph.add_edge(ids[0], b, length=(i % 17)/4)
    else:
        rng = random.Random(2025)
        for a in ids:
            for b in ids:
                if rng.random() < .08:
                    graph.add_edge(a, b, length=rng.randrange(33)/4)
    return graph


def summarize(values):
    ordered = sorted(values)
    return {'samples': len(values), 'p50_seconds': statistics.median(values),
            'p95_seconds': ordered[max(0, (95*len(ordered)+99)//100-1)]}


def run(samples):
    rows = []
    for family in ['chain', 'hub', 'sparse']:
        graph = fixture(family)
        ids = list(graph)
        locations = [ids[0], ids[len(ids)//4], ids[len(ids)//2], ids[-1], ids[0]]
        strings = [str(node) for node in locations]
        for selected in ['native_bmssp_2025', 'native_reference_dijkstra']:
            # Explicit benchmark-only fixture injection, never used by production loaders.
            with patch('graph_loader.load_native_graph', return_value=graph), TestClient(api.app) as client:
                for state in ['cold', 'warm']:
                    cache = SnapshotCache()
                    if state == 'warm':
                        snapshot, _ = cache.get(graph)
                        compute_native_matrix(snapshot, locations, selected)
                        client.post('/distance-matrix', params={'engine': selected}, json=strings).raise_for_status()
                    measurements = {name: [] for name in ['adapter_conversion', 'snapshot_lookup_wall',
                        'native_graph_construction', 'degree_reduction', 'native_query',
                        'query_wall_residual', 'binding_roundtrip', 'matrix_extraction', 'matrix_wall', 'api_latency']}
                    last_meta = None
                    for _ in range(samples):
                        if state == 'cold':
                            cache.clear()
                            snapshot_cache.clear()
                        start = time.perf_counter()
                        snapshot, snapshot_meta = cache.get(graph)
                        lookup = time.perf_counter()-start
                        start = time.perf_counter()
                        matrix, meta = compute_native_matrix(snapshot, locations, selected)
                        matrix_wall = time.perf_counter()-start
                        baseline = [[nx.shortest_path_length(graph, a, b, weight='length')
                                     if nx.has_path(graph, a, b) else float('inf') for b in locations] for a in locations]
                        assert matrix.tolist() == baseline
                        start = time.perf_counter()
                        for _ in range(100):
                            assert bmssp_native._binding_roundtrip_ids(locations) == locations
                        binding = (time.perf_counter()-start)/100
                        start = time.perf_counter()
                        response = client.post('/distance-matrix', params={'engine': selected}, json=strings)
                        api_latency = time.perf_counter()-start
                        response.raise_for_status()
                        expected_json = [[None if value == float('inf') else value for value in row] for row in baseline]
                        assert response.json()['matrix'] == expected_json
                        assert response.json()['metadata']['selected_engine'] == selected
                        values = [snapshot_meta['adapter_conversion_time'], lookup,
                            snapshot_meta['native_graph_construction_time'],
                            meta['degree_reduction_time'],
                            meta['query_time'], meta['query_wall_residual_time'], binding,
                            meta['matrix_extraction_time'], matrix_wall, api_latency]
                        for key, value in zip(measurements, values):
                            measurements[key].append(value)
                        last_meta = meta
                    rows.append({'family': family, 'engine': selected, 'state': state,
                        'nodes': len(graph), 'edges': graph.number_of_edges(),
                        'density_including_loops': graph.number_of_edges()/len(graph)**2,
                        'requested_locations': len(locations), 'distinct_sources': len(set(locations)),
                        'query_distribution': strings, 'timings': {k: summarize(v) for k, v in measurements.items()},
                        'last_query_diagnostics': last_meta['native_execution_diagnostics']})
    return {'seed': 2025, 'samples_per_engine_family_state': samples,
        'machine': platform.platform(), 'processor': platform.processor(),
        'compiler': bmssp_native.compiler, 'module': bmssp_native.__file__,
        'max_rss_platform_units': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'method': 'In-process TestClient API; cold resets both caches; warm retains snapshots/engines. p95 nearest rank. Binding roundtrip includes argument/result transfer and trivial native vector move, not solver cleanup.',
        'rows': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=30)
    args = parser.parse_args()
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('api').setLevel(logging.WARNING)
    if args.samples < 20:
        parser.error('At least 20 samples are required for reported p95')
    print(json.dumps(run(args.samples), indent=2))
