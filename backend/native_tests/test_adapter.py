from concurrent.futures import ThreadPoolExecutor
import math
import numpy as np
import networkx as nx
import pytest
from native_graph import (SnapshotCache, RoutingLimits, RoutingBudgetExceeded, normalize_node_id,
                          NativeUnavailable, native_module)
from routing_adapter import compute_native_matrix


def test_snapshot_identity_mapping_mutation_and_ownership(roads):
    cache = SnapshotCache(2)
    first, metadata = cache.get(roads)
    assert not metadata['cache_hit']
    second, metadata = cache.get(roads)
    assert metadata['cache_hit'] and second is first
    locations = [5_000_000_000, 5_000_000_001, 42, 5_000_000_001]
    matrix, meta = compute_native_matrix(first, locations)
    assert meta['native_execution_diagnostics']['sssp_invocations'] == 3
    assert meta['native_execution_diagnostics']['degree_reduction_count'] == 1
    matrix2, meta2 = compute_native_matrix(second, locations)
    assert np.array_equal(matrix, matrix2)
    assert meta2['preprocessing_time'] == 0
    assert meta2['native_execution_diagnostics']['degree_reduction_count'] == 0
    prepared, _ = first.engine('native_bmssp_2025')
    result = prepared.solve(5_000_000_000)
    path = first.original_path(result, -7)
    assert path['original_edges'][-1] == (5_000_000_002, -7, 0)
    assert len(set(first.original_edges)) == roads.number_of_edges()
    with pytest.raises(TypeError):
        first.original_edges[0] = ()
    roads[5_000_000_000][5_000_000_001][1]['length'] = 1
    changed, metadata = cache.get(roads)
    assert changed is not first and not metadata['cache_hit']
    assert changed.snapshot_id != first.snapshot_id
    assert compute_native_matrix(changed, locations)[0][0, 1] == 1
    assert compute_native_matrix(first, locations)[0][0, 1] == 2.25
    with pytest.raises(ValueError, match='different native graph'):
        changed.original_path(result, -7)
    roads.add_node(100)
    third, _ = cache.get(roads)
    assert 100 in third.original_nodes
    del roads
    assert first.original_path(result, -7)['distance'] == 3.25


def test_order_independent_edge_ids_and_node_normalization(roads):
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(reversed(list(roads)))
    graph.add_edges_from((u, v, k, dict(data)) for u, v, k, data in reversed(list(roads.edges(keys=True, data=True))))
    cache = SnapshotCache()
    a, _ = cache.get(roads)
    b, _ = cache.get(graph)
    assert a.snapshot_id == b.snapshot_id
    assert dict(a.original_edges) == dict(b.original_edges)
    graph = nx.DiGraph()
    graph.add_edge('5000000000', np.int64(5000000001), length=np.float64(0))
    snap, _ = cache.get(graph)
    assert compute_native_matrix(snap, ['5000000000', '5000000001'])[0][0, 1] == 0
    assert snap.original_nodes[5000000000] == '5000000000'


@pytest.mark.parametrize('value', [True, 1.0, '1.0', 'node_1', None, 2**63, -(2**63)-1, ' 1'])
def test_invalid_ids(value):
    with pytest.raises(ValueError):
        normalize_node_id(value)


@pytest.mark.parametrize('weight', [-1, math.inf, math.nan, None, True, '3'])
def test_invalid_edge_weights(weight):
    graph = nx.DiGraph()
    graph.add_edge(0, 1, length=weight)
    with pytest.raises(ValueError):
        SnapshotCache().get(graph)


def test_unsupported_graphs_collisions_keys_and_budgets(roads):
    with pytest.raises(ValueError, match='directed'):
        SnapshotCache().get(nx.Graph())
    graph = nx.DiGraph()
    graph.add_nodes_from([1, '01'])
    with pytest.raises(ValueError, match='collide'):
        SnapshotCache().get(graph)
    graph = nx.MultiDiGraph()
    graph.add_edge(0, 1, key=(1, 2), length=1)
    with pytest.raises(ValueError, match='keys'):
        SnapshotCache().get(graph)
    with pytest.raises(RoutingBudgetExceeded):
        SnapshotCache().get(roads, limits=RoutingLimits(max_nodes=1))
    snapshot, _ = SnapshotCache().get(roads)
    for locations, limits in [([1, 2], RoutingLimits(max_locations=1)),
                              ([5_000_000_000, 42], RoutingLimits(max_sources=1))]:
        with pytest.raises(RoutingBudgetExceeded):
            compute_native_matrix(snapshot, locations, limits=limits)
    with pytest.raises(ValueError, match='not in graph'):
        compute_native_matrix(snapshot, [999])
    with pytest.raises(ValueError):
        compute_native_matrix(snapshot, [])
    with pytest.raises(ValueError):
        compute_native_matrix(snapshot, [42], engine='fake')
    with pytest.raises(ValueError):
        SnapshotCache().get(roads, weight='time')


def test_cache_eviction_and_concurrent_engine_reuse(roads):
    cache = SnapshotCache(1)
    snapshot, _ = cache.get(roads)
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: compute_native_matrix(snapshot, [5_000_000_000, -7]), range(4)))
    assert sum(meta['native_execution_diagnostics']['degree_reduction_count'] for _, meta in results) == 1
    assert all(matrix[0, 1] == 3.25 and math.isinf(matrix[1, 0]) for matrix, _ in results)
    cache.get(nx.DiGraph())
    assert cache.get(roads)[0] is not snapshot


def test_failed_module_import(monkeypatch):
    import native_graph
    original = native_graph.importlib.import_module
    def missing(name):
        if name == 'bmssp_native':
            raise ImportError('deliberate missing extension')
        return original(name)
    monkeypatch.setattr(native_graph.importlib, 'import_module', missing)
    with pytest.raises(NativeUnavailable, match='unavailable'):
        native_module()
