import math
import copy
import networkx as nx
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import api
import graph_loader
from native_graph import snapshot_cache, NativeUnavailable


def request(cycle, monkeypatch, **changes):
    monkeypatch.setattr(graph_loader,'load_native_graph',lambda place:cycle)
    body={'locations':[str(x) for x in cycle], 'engine':'native_bmssp_2025', **changes}
    return TestClient(api.app).post('/vrp',json=body)


def test_native_execution_original_paths_geometry_and_reuse(cycle,monkeypatch):
    import bmssp_native
    snapshot_cache.clear()
    monkeypatch.setattr(api,'compute_matrix_with_fallback',lambda *a,**k:pytest.fail('Legacy fallback'))
    monkeypatch.setattr(nx,'shortest_path',lambda *a,**k:pytest.fail('Independent NetworkX route'))
    monkeypatch.setattr(bmssp_native,'NativeReferenceDijkstra',lambda *a:pytest.fail('Dijkstra substitution'))
    result=request(cycle,monkeypatch,vehicle_count=2,demands=[0,1,1],capacities=[1,1])
    assert result.status_code==200,result.text
    data=result.json()
    assert data['status']=='FEASIBLE' and data['route_feasibility'] and data['exact_routing']
    assert data['selected_engine']=='native_bmssp_2025' and data['graph_snapshot']
    diag=data['metadata']['native_execution_diagnostics']
    assert diag['sssp_invocations']==3
    assert sum(x['recursive_calls'] for x in diag['sources'])>0
    assert sum(x['frontier']['pulls'] for x in diag['sources'])>0
    assert diag['degree_reduction_count']==1
    total=[]
    for r,legs,geometry,segments in zip(data['routes'],data['route_legs'],data['route_geometries'],data['route_geometry_segments']):
        assert len(legs)==len(r)-1
        assert geometry==segments[0]
        for leg in legs:
            assert leg['path_status']=='VERIFIED'
            edges=leg['original_edges']; lengths=[]
            for a,b,e in zip(leg['vertices'],leg['vertices'][1:],edges):
                assert e['u']==a and e['v']==b
                lengths.append(cycle[int(a)][int(b)][int(e['key'])]['length'])
            assert sum(lengths)==leg['distance']
            total.append(leg['distance'])
    assert math.fsum(total)==data['total_distance']
    assert [3.002,101.005] in [point for geometry in data['route_geometries'] for point in geometry]
    assert all(isinstance(x,str) for route in data['route_locations'] for x in route)
    second=request(cycle,monkeypatch).json()
    assert second['metadata']['cache_hit'] and second['metadata']['native_execution_diagnostics']['degree_reduction_count']==0


def test_unreachable_returns_no_success_even_http_200(monkeypatch):
    graph=nx.DiGraph();graph.add_edge(0,1,length=1)
    data=request(graph,monkeypatch).json()
    assert data['status']=='NO_SOLUTION' and not data['route_feasibility']
    assert data['routes']==[] and data['route_geometries']==[] and data['total_distance'] is None
    assert data['metadata']['unreachable_pair_count']==1


def test_duration_provenance_and_time_validation(cycle,monkeypatch):
    response=request(cycle,monkeypatch,time_windows=[[0,100],[10,40],[0,70]],service_durations=[0,2,3])
    assert response.status_code==200,response.text
    data=response.json();assert data['status']=='FEASIBLE' and data['duration_units']=='seconds'
    assert data['metadata']['duration_provenance'].startswith('sum_of_travel_time')
    assert data['schedules'][0][-1]['arrival_seconds']<=100
    for _,_,attrs in cycle.edges(data=True):attrs.pop('travel_time',None)
    response=request(cycle,monkeypatch,time_windows=[[0,100]]*3)
    assert response.status_code==400 and 'duration_matrix' in response.text
    supplied=[[0,3,7],[9,0,4],[5,8,0]]
    data=request(cycle,monkeypatch,time_windows=[[0,100]]*3,duration_matrix=supplied).json()
    assert data['status']=='FEASIBLE' and data['metadata']['duration_provenance'].startswith('caller_supplied')
    data=request(cycle,monkeypatch,time_windows=[[0,1]]*3,duration_matrix=supplied).json()
    assert data['status']=='NO_SOLUTION'


def test_missing_geometry_splits_without_bridging_and_snapshot_invalidation(cycle,monkeypatch):
    initial=request(cycle,monkeypatch).json()
    mid=list(cycle)[1]
    cycle.nodes[mid].pop('x')
    data=request(cycle,monkeypatch).json()
    assert data['graph_snapshot']!=initial['graph_snapshot']
    assert data['status']=='FEASIBLE' and data['total_distance']==initial['total_distance']
    assert any(l['geometry_status']=='UNAVAILABLE' for legs in data['route_legs'] for l in legs)
    assert data['route_geometries']==[[]]
    assert len(data['route_geometry_segments'][0])<=2


def test_duplicate_invalid_budget_and_execution_errors(cycle,monkeypatch):
    assert request(cycle,monkeypatch,locations=[str(list(cycle)[0])]*2).status_code==400
    assert request(cycle,monkeypatch,demands=[0,0,0]).status_code==400
    assert request(cycle,monkeypatch,vehicle_count=11).status_code==413
    assert request(cycle,monkeypatch,max_search_seconds=1000).status_code==413
    assert request(cycle,monkeypatch,demands=[0,True,0],capacities=[1]).status_code==422
    with patch('graph_loader.load_native_graph',side_effect=NativeUnavailable('Native local data unavailable')):
        assert TestClient(api.app).post('/vrp',json={'locations':['0'],'engine':'native_bmssp_2025'}).status_code==503
    with patch('logistics_routing.compute_native_matrix',side_effect=RuntimeError('private server failure')):
        result=request(cycle,monkeypatch)
        assert result.status_code==500 and 'private server failure' not in result.text
    monkeypatch.setenv('VRP_MAX_GEOMETRY_POINTS','1')
    assert request(cycle,monkeypatch).status_code==413


def test_explicit_native_dijkstra_and_depot_index(cycle,monkeypatch):
    response=request(cycle,monkeypatch,engine='native_reference_dijkstra',depot=1)
    assert response.status_code==200,response.text
    data=response.json();assert data['selected_engine']=='native_reference_dijkstra'
    assert data['routes'][0][0]==data['routes'][0][-1]==1
    assert all(d['implementation']=='reference_dijkstra' for d in data['metadata']['native_execution_diagnostics']['sources'])


def test_native_search_strings_and_no_legacy_graph_loading(cycle,monkeypatch):
    monkeypatch.setattr(graph_loader,'load_native_graph',lambda place:cycle)
    monkeypatch.setattr(graph_loader,'find_nearest_nodes',lambda *a:pytest.fail('Legacy search used'))
    client=TestClient(api.app)
    response=client.post('/search-nodes?engine=native_bmssp_2025',json={'lat':3,'lon':101,'radius':1000})
    assert response.status_code==200 and response.json()['nodes'][0]['node_id']=='9007199254740993'
    assert client.post('/search-nodes?engine=native_bmssp_2025',json={'lat':3,'lon':101,'radius':50000}).status_code==422
    monkeypatch.setenv('NATIVE_SNAPSHOT_MAX_GEOMETRY_POINTS','1')
    assert request(cycle,monkeypatch).status_code==413


def test_projected_geometry_is_explicitly_unavailable(cycle,monkeypatch):
    cycle.graph['crs']='EPSG:3857'
    data=request(cycle,monkeypatch).json()
    assert data['status']=='FEASIBLE' and data['route_geometries']==[[]]
    assert all(leg['geometry_status']=='UNAVAILABLE' for legs in data['route_legs'] for leg in legs)


def test_original_string_ids_round_trip(monkeypatch):
    graph=nx.DiGraph()
    graph.add_node('01',x=101,y=3);graph.add_node('02',x=101.01,y=3)
    graph.add_edge('01','02',length=1);graph.add_edge('02','01',length=1)
    data=request(graph,monkeypatch).json()
    assert data['status']=='FEASIBLE'
    assert data['location_coordinates']['01']=={'lat':3.0,'lon':101.0}
    assert data['route_legs'][0][0]['source']=='01'
    assert data['route_legs'][0][0]['vertices']==['01','02']


def test_legacy_approximation_does_not_overwrite_solver_failure(monkeypatch):
    import numpy as np
    from vrp_solver import solve_vrp
    # The original API test module imports api with a solver mock installed.
    # Restore the actual solver for this independent production-behavior check.
    monkeypatch.setattr(api, 'solve_vrp', solve_vrp)
    monkeypatch.setattr(api,'compute_matrix_with_fallback',lambda *a,**k:(np.array([[0,1],[math.inf,0]]),{'fallback_counts':{'haversine':1,'symmetric':0}}))
    monkeypatch.setattr(api,'get_node_coordinates',lambda *a:None)
    data=TestClient(api.app).post('/vrp',json={'locations':['node_1','node_2']}).json()
    assert data['status']=='NO_SOLUTION' and not data['route_feasibility'] and not data['exact_routing']


def test_solver_and_geometry_work_run_off_event_loop(cycle,monkeypatch):
    import asyncio,threading,time
    import logistics_routing
    original=logistics_routing.solve_vrp
    threads=[]
    def delayed(*args,**kwargs):
        threads.append(threading.get_ident());time.sleep(.05)
        return original(*args,**kwargs)
    monkeypatch.setattr(graph_loader,'load_native_graph',lambda place:cycle)
    monkeypatch.setattr(logistics_routing,'solve_vrp',delayed)
    main=threading.get_ident()
    async def run():
        req=api.VRPRequest(locations=[str(x) for x in cycle],engine='native_bmssp_2025')
        task=asyncio.create_task(api.solve_vehicle_routing(req))
        await asyncio.sleep(.01)
        assert not task.done() and (await api.health_check())['status']=='healthy'
        assert (await task).status_code==200
    asyncio.run(run())
    assert threads and threads[0]!=main


def test_request_preserves_snapshot_if_source_changes_after_matrix(cycle,monkeypatch):
    import logistics_routing
    from shapely.geometry import LineString
    original=logistics_routing.compute_native_matrix
    def mutate_after_capture(*args,**kwargs):
        matrix,metadata=original(*args,**kwargs)
        for u,v,data in cycle.edges(data=True):
            data['length']+=1000
            data['geometry']=LineString([(0,0),(1,1)])
        return matrix,metadata
    with monkeypatch.context() as context:
        context.setattr(logistics_routing,'compute_native_matrix',mutate_after_capture)
        preserved=request(cycle,context).json()
    assert preserved['status']=='FEASIBLE' and preserved['total_distance']==601.5
    assert [3.002,101.005] in preserved['route_geometries'][0]
    changed=request(cycle,monkeypatch).json()
    assert changed['graph_snapshot']!=preserved['graph_snapshot']
    assert changed['total_distance']>preserved['total_distance']


def test_loader_failure_never_substitutes_demo_graph(monkeypatch):
    monkeypatch.setattr(graph_loader,'_current_graph',None)
    monkeypatch.setattr(graph_loader,'_current_place',None)
    monkeypatch.setattr(graph_loader,'load_graph_from_cache',lambda place:None)
    monkeypatch.setattr(graph_loader.ox,'graph_from_place',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('offline data failure')))
    monkeypatch.setattr(graph_loader,'create_test_graph',lambda:pytest.fail('Synthetic graph substituted'))
    with pytest.raises(RuntimeError,match='no synthetic replacement'):
        graph_loader.load_graph('controlled-fixture-failure')


def test_zero_roads_equal_parallel_ties_and_zero_time_capacity(monkeypatch):
    graph=nx.MultiDiGraph()
    graph.add_node(0,x=101,y=3);graph.add_node(1,x=101,y=3)
    graph.add_edge(0,1,key=7,length=0,travel_time=0)
    graph.add_edge(0,1,key=8,length=0,travel_time=0)
    graph.add_edge(1,0,key=7,length=0,travel_time=0)
    data=request(graph,monkeypatch,demands=[0,0],capacities=[0],time_windows=[[0,0],[0,0]]).json()
    assert data['status']=='FEASIBLE' and data['total_distance']==0 and data['vehicle_loads']==[0]
    assert data['route_legs'][0][0]['original_edges'][0]['key']=='7'
    assert all(step['arrival_seconds']==0 for step in data['schedules'][0])
