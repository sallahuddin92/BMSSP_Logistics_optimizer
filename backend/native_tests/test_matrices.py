"""Four-way differential tests with an independent small-graph Floyd oracle."""
import math
import random
import numpy as np
import networkx as nx
import pytest
from native_graph import SnapshotCache
from routing_adapter import compute_native_matrix


def oracle(graph, nodes):
    # Independent Floyd-Warshall; no NetworkX shortest-path call or native labels.
    indices = {v: i for i, v in enumerate(nodes)}
    out = [[math.inf for _ in nodes] for _ in nodes]
    for i in range(len(nodes)):
        out[i][i] = 0
    for u, v, data in graph.edges(data=True):
        a, b = indices[u], indices[v]
        out[a][b] = min(out[a][b], data['length'])
    for k in range(len(nodes)):
        for i in range(len(nodes)):
            for j in range(len(nodes)):
                out[i][j] = min(out[i][j], out[i][k] + out[k][j])
    return out


@pytest.mark.parametrize('seed', [2025, 17033, 45141])
@pytest.mark.parametrize('density', [0, .15, .9])
def test_four_way_integer_quarter_agreement(seed, density, monkeypatch):
    rng = random.Random(seed)
    nodes = [5_000_000_000 + i for i in range(8)]
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(nodes)
    for u in nodes:
        for v in nodes:
            if rng.random() < density:
                graph.add_edge(u, v, length=rng.randrange(17)/4)
                if rng.random() < .2:
                    graph.add_edge(u, v, length=rng.randrange(17)/4)
    exact = np.array(oracle(graph, nodes))
    nx_results = dict(nx.all_pairs_dijkstra_path_length(graph, weight='length'))
    snapshot, _ = SnapshotCache().get(graph)
    locations = nodes + [nodes[2], nodes[0]]
    expected = np.array([[exact[nodes.index(u), nodes.index(v)] for v in locations] for u in locations])
    assert np.array_equal(expected, [[nx_results[u].get(v, math.inf) for v in locations] for u in locations])
    # Native modes must succeed with all NetworkX routing disabled.
    def forbidden(*args, **kwargs):
        raise AssertionError('NetworkX routing invoked in native mode')
    monkeypatch.setattr(nx, 'shortest_path_length', forbidden)
    monkeypatch.setattr(nx, 'single_source_dijkstra_path_length', forbidden)
    for engine in ['native_bmssp_2025', 'native_reference_dijkstra']:
        matrix, meta = compute_native_matrix(snapshot, locations, engine)
        assert np.array_equal(matrix, expected), f'seed={seed} density={density} edges={list(graph.edges(data=True))}'
        assert meta['native_execution_diagnostics']['sssp_invocations'] == len(nodes)
        assert meta['unreachable_pair_count'] == np.count_nonzero(~np.isfinite(expected))
        prepared, _ = snapshot.engine(engine)
        for u in nodes:
            result = prepared.solve(u)
            for v in nodes:
                path = snapshot.original_path(result, v)
                assert path['reachable'] == math.isfinite(exact[nodes.index(u), nodes.index(v)])
                if path['reachable']:
                    assert path['vertices'][0] == u and path['vertices'][-1] == v
                    assert len(set(path['vertices'])) == len(path['vertices'])
                    assert sum(graph[a][b][key]['length'] for a, b, key in path['original_edges']) == path['distance']


def test_one_way_zero_parallel_duplicate_and_float_paths(roads):
    locations = [5_000_000_000, 5_000_000_002, 42, -7, 5_000_000_002]
    snapshot, _ = SnapshotCache().get(roads)
    actual, meta = compute_native_matrix(snapshot, locations)
    assert actual[0, 1] == 2.25
    assert actual[1, 4] == 0
    assert math.isinf(actual[1, 0])
    assert math.isinf(actual[0, 2])
    assert meta['exact_routing'] and not meta['approximation_provenance']
    graph = nx.DiGraph()
    graph.add_weighted_edges_from([(0, 1, .1), (1, 2, .2), (0, 2, .3), (2, 3, .1)], weight='length')
    snap, _ = SnapshotCache().get(graph)
    a, _ = compute_native_matrix(snap, [0, 1, 2, 3])
    b, _ = compute_native_matrix(snap, [0, 1, 2, 3], 'native_reference_dijkstra')
    assert np.array_equal(a, b)
    prepared, _ = snap.engine('native_bmssp_2025')
    path = snap.original_path(prepared.solve(0), 3)
    assert sum(graph[u][v]['length'] for u, v, _ in path['original_edges']) == path['distance']
