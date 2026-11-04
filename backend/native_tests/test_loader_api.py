import asyncio
import threading
import time
import networkx as nx
import pytest
from fastapi.testclient import TestClient
import bmssp_native
import api
import graph_loader
from native_graph import NativeUnavailable, snapshot_cache


def test_curved_road_lengths_survive_loading(monkeypatch, tmp_path):
    from shapely.geometry import LineString
    graph = nx.MultiDiGraph()
    graph.add_node(0, x=0, y=0)
    graph.add_node(1, x=.001, y=0)
    graph.add_edge(0, 1, key=0, length=725.25, geometry=LineString([(0, 0), (.0005, .003), (.001, 0)]))
    monkeypatch.setattr(graph_loader.ox, 'graph_from_place', lambda *a, **k: graph)
    def forbidden(*args, **kwargs):
        raise AssertionError('Simplified lengths were overwritten')
    monkeypatch.setattr(graph_loader.ox.distance, 'add_edge_lengths', forbidden)
    monkeypatch.setattr(graph_loader, 'CACHE_DIR', str(tmp_path))
    monkeypatch.setattr(graph_loader, '_current_graph', None)
    monkeypatch.setattr(graph_loader, '_current_place', None)
    loaded = graph_loader.load_graph('curved-fixture', force_reload=True)
    assert loaded is graph
    assert graph[0][1][0]['length'] == 725.25
    assert graph[0][1][0]['length'] > graph_loader.haversine_distance(0, 0, 0, .001)
    assert graph_loader.load_native_graph('curved-fixture') is graph
    monkeypatch.setattr(graph_loader, '_current_graph', None)
    cached = graph_loader.load_native_graph('curved-fixture')
    assert cached[0][1][0]['length'] == 725.25
    from routing_adapter import compute_native_matrix
    snapshot, _ = snapshot_cache.get(cached)
    assert compute_native_matrix(snapshot, [0, 1])[0][0, 1] == 725.25


def test_strict_loader_rejects_missing_historical_and_synthetic(monkeypatch):
    monkeypatch.setattr(graph_loader, '_current_graph', None)
    monkeypatch.setattr(graph_loader, '_current_place', None)
    monkeypatch.setattr(graph_loader, 'load_graph_from_cache', lambda place: None)
    monkeypatch.setattr(graph_loader.ox, 'graph_from_place', lambda *a, **k: pytest.fail('Native downloaded data'))
    monkeypatch.setattr(graph_loader, 'create_test_graph', lambda: pytest.fail('Native substituted graph'))
    with pytest.raises(NativeUnavailable, match='No local'):
        graph_loader.load_native_graph()
    graph = nx.DiGraph()
    graph.add_edge(0, 1, length=111)
    monkeypatch.setattr(graph_loader, '_current_graph', graph)
    monkeypatch.setattr(graph_loader, '_current_place', 'old')
    with pytest.raises(NativeUnavailable, match='provenance'):
        graph_loader.load_native_graph('old')
    graph.graph['routing_data_origin'] = 'synthetic_fallback'
    with pytest.raises(ValueError, match='Synthetic'):
        snapshot_cache.get(graph)


def test_actual_python_to_api_execution_and_directed_unreachable(roads, monkeypatch):
    snapshot_cache.clear()
    monkeypatch.setattr(graph_loader, 'load_native_graph', lambda place: roads)
    def forbidden(*args, **kwargs):
        raise AssertionError('Undisclosed engine substitution')
    monkeypatch.setattr(api, 'compute_matrix_with_fallback', forbidden)
    monkeypatch.setattr(nx, 'shortest_path_length', forbidden)
    monkeypatch.setattr(nx, 'single_source_dijkstra_path_length', forbidden)
    monkeypatch.setattr(bmssp_native, 'NativeReferenceDijkstra', forbidden)
    locations = ['5000000000', '5000000002', '-7', '42', '5000000002']
    with TestClient(api.app) as client:
        response = client.post('/distance-matrix?engine=native_bmssp_2025', json=locations)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data['locations'] == locations
        assert data['matrix'][0][1] == 2.25
        assert data['matrix'][1][0] is None
        assert data['matrix'][1][4] == 0
        assert data['status'] == 'PARTIAL_OR_UNREACHABLE'
        meta = data['metadata']
        assert meta['selected_engine'] == 'native_bmssp_2025'
        assert meta['algorithm_version'] == 'arxiv:2504.17033v2'
        assert meta['exact_routing'] and meta['weight_units'] == 'meters'
        assert meta['unreachable_pair_count'] > 0
        assert meta['reachability'][1][0] is False
        diagnostics = meta['native_execution_diagnostics']
        assert diagnostics['sssp_invocations'] == 4
        assert sum(d['recursive_calls'] for d in diagnostics['sources']) > 0
        assert sum(d['frontier']['pulls'] for d in diagnostics['sources']) > 0
        assert sum(d['base_calls'] for d in diagnostics['sources']) > 0
        assert all(d['implementation'] == 'BMSSP2025Engine::solve' for d in diagnostics['sources'])
        repeated = client.post('/distance-matrix?engine=native_bmssp_2025', json=locations).json()
        assert repeated['matrix'] == data['matrix']
        assert repeated['metadata']['cache_hit']
        assert repeated['metadata']['preprocessing_time'] == 0
        assert repeated['metadata']['native_execution_diagnostics']['degree_reduction_count'] == 0


def test_explicit_dijkstra_and_legacy_default(roads, monkeypatch):
    snapshot_cache.clear()
    monkeypatch.setattr(graph_loader, 'load_native_graph', lambda place: roads)
    import numpy as np
    legacy_calls = []
    def legacy(locations, place):
        legacy_calls.append((locations, place))
        return np.zeros((len(locations), len(locations))), {'fallback_counts': {'symmetric': 0, 'haversine': 0}}
    monkeypatch.setattr(api, 'compute_matrix_with_fallback', legacy)
    with TestClient(api.app) as client:
        result = client.post('/distance-matrix?engine=native_reference_dijkstra', json=['5000000000', '-7'])
        assert result.status_code == 200
        assert result.json()['metadata']['selected_engine'] == 'native_reference_dijkstra'
        assert all(d['implementation'] == 'reference_dijkstra' for d in result.json()['metadata']['native_execution_diagnostics']['sources'])
        result = client.post('/distance-matrix', json=['node_1'])
        assert result.status_code == 200
        assert result.json()['metadata']['selected_engine'] == 'legacy_networkx'
        assert not result.json()['metadata']['exact_routing']
        assert legacy_calls == [(['node_1'], None)]


def test_api_validation_failure_import_execution_and_admission(roads, monkeypatch):
    snapshot_cache.clear()
    monkeypatch.setattr(graph_loader, 'load_native_graph', lambda place: roads)
    monkeypatch.setattr(api, 'compute_matrix_with_fallback', lambda *a: pytest.fail('Fallback executed'))
    with TestClient(api.app) as client:
        assert client.post('/distance-matrix?engine=fake', json=['42']).status_code == 422
        assert client.post('/distance-matrix?engine=native_bmssp_2025', json=['999']).status_code == 400
        assert client.post('/distance-matrix?engine=native_bmssp_2025', json=[]).status_code == 400
        monkeypatch.setenv('NATIVE_MAX_LOCATIONS', '1')
        assert client.post('/distance-matrix?engine=native_bmssp_2025', json=['42', '42']).status_code == 413
        monkeypatch.delenv('NATIVE_MAX_LOCATIONS')
        monkeypatch.setenv('NATIVE_MAX_SOURCES', '1')
        assert client.post('/distance-matrix?engine=native_bmssp_2025', json=['42', '-7']).status_code == 413
        monkeypatch.delenv('NATIVE_MAX_SOURCES')
        with monkeypatch.context() as context:
            import native_graph
            original = native_graph.importlib.import_module
            def missing(name):
                if name == 'bmssp_native':
                    raise ImportError('deliberate missing binary')
                return original(name)
            context.setattr(native_graph.importlib, 'import_module', missing)
            snapshot_cache.clear()
            response = client.post('/distance-matrix?engine=native_bmssp_2025', json=['42'])
            assert response.status_code == 503 and 'unavailable' in response.text
        with monkeypatch.context() as context:
            def fail(*args, **kwargs):
                raise RuntimeError('deliberate native execution failure')
            context.setattr(api, 'compute_native_matrix', fail)
            response = client.post('/distance-matrix?engine=native_bmssp_2025', json=['42'])
            assert response.status_code == 500 and 'native execution failure' in response.text
        with monkeypatch.context() as context:
            slot = threading.BoundedSemaphore(1)
            slot.acquire()
            context.setattr(api, '_native_slots', slot)
            assert client.post('/distance-matrix?engine=native_bmssp_2025', json=['42']).status_code == 503


def test_preprocessing_runs_off_event_loop(roads, monkeypatch):
    main_thread = threading.get_ident()
    worker_threads = []
    def load(place):
        worker_threads.append(threading.get_ident())
        time.sleep(.05)
        return roads
    monkeypatch.setattr(graph_loader, 'load_native_graph', load)
    async def run():
        progressed = False
        task = asyncio.create_task(api.get_distance_matrix(['42'], 'native_bmssp_2025', None))
        await asyncio.sleep(.01)
        progressed = not task.done()
        response = await task
        assert progressed
        assert response['metadata']['selected_engine'] == 'native_bmssp_2025'
    asyncio.run(run())
    assert worker_threads and worker_threads[0] != main_thread
