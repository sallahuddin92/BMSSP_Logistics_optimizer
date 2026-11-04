from concurrent.futures import ThreadPoolExecutor
import gc
import importlib.machinery
import math
import pytest
import bmssp_native as native


def test_binary_execution_and_lifetime():
    assert any(native.__file__.endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES)
    graph = native.NativeGraph([-(2**63), 2**63-1, 7], [(2**64-1, -(2**63), 2**63-1, .25)])
    assert graph.metadata == dict(vertex_count=3, edge_count=1, directed=True, immutable=True)
    engine = native.BMSSP2025Engine(graph)
    assert engine.metadata["preprocessing_count"] == 1
    result = engine.solve(-(2**63))
    assert result.algorithm == "native_bmssp_2025"
    assert result.diagnostics["implementation"] == "BMSSP2025Engine::solve"
    assert result.diagnostics["recursive_calls"] > 0
    assert result.diagnostics["frontier"]["pulls"] > 0
    assert result.diagnostics["base_calls"] > 0
    assert result.belongs_to(graph)
    del engine, graph
    gc.collect()
    assert result.distance(2**63-1) == .25
    assert result.path(2**63-1)["edges"] == [2**64-1]
    assert result.path(7)["reachable"] is False
    assert math.isinf(result.distance(7))
    assert result.reachability.count(True) == 2
    assert result.source == -(2**63)


def test_independent_concurrent_queries_and_comparator():
    graph = native.NativeGraph(list(range(80)), [(i, i, i+1, .25) for i in range(79)])
    engine = native.BMSSP2025Engine(graph)
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(engine.solve, [0, 10, 20, 0, 79]))
    reference = native.NativeReferenceDijkstra(graph)
    for source, result in zip([0, 10, 20, 0, 79], results):
        assert result.distances == reference.solve(source).distances
        assert result.distance(source) == 0
    assert engine.metadata["preprocessing_count"] == 1


@pytest.mark.parametrize("vertices,edges", [
    ([0, 0], []), ([0], [(1, 0, 2, 1)]), ([0, 1], [(1, 0, 1, -1)]),
    ([0, 1], [(1, 0, 1, float('nan'))]), ([0, 1], [(1, 0, 1, float('inf'))]),
    ([0, 1], [(1, 0, 1, 0), (1, 1, 0, 0)]),
])
def test_native_graph_rejects_invalid(vertices, edges):
    with pytest.raises((ValueError, IndexError)):
        native.NativeGraph(vertices, edges)


def test_binding_integer_ranges_and_native_exceptions():
    with pytest.raises(TypeError):
        native.NativeGraph([2**63], [])
    with pytest.raises(TypeError):
        native.NativeGraph([0], [(-1, 0, 0, 0)])
    with pytest.raises(TypeError):
        native.NativeGraph([0], [(2**64, 0, 0, 0)])
    engine = native.BMSSP2025Engine(native.NativeGraph([0], []))
    with pytest.raises(IndexError):
        engine.solve(1)
    maximum = float.fromhex('0x1.fffffffffffffp+1023')
    with pytest.raises(OverflowError):
        native.BMSSP2025Engine(native.NativeGraph([0, 1, 2], [(0, 0, 1, maximum), (1, 1, 2, maximum)])).solve(0)


@pytest.mark.parametrize('value', [True, 1.5, '1'])
def test_direct_binding_rejects_noninteger_ids(value):
    with pytest.raises(TypeError):
        native.NativeGraph([value], [])
    engine = native.BMSSP2025Engine(native.NativeGraph([0, 1], [(1, 0, 1, 0)]))
    with pytest.raises(TypeError):
        engine.solve(value)
    result = engine.solve(0)
    with pytest.raises(TypeError):
        result.distances_to([value])


@pytest.mark.parametrize('weight', [True, '3'])
def test_direct_binding_rejects_weight_coercion(weight):
    with pytest.raises(TypeError):
        native.NativeGraph([0, 1], [(0, 0, 1, weight)])
