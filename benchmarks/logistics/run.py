"""Bounded offline VRP benchmark; fixture injection exists only in this harness."""
import json
import logging
import math
import platform
import random
import resource
import statistics
from time import perf_counter
from unittest.mock import patch
import networkx as nx
from fastapi.testclient import TestClient
from shapely.geometry import LineString
import api
from native_graph import snapshot_cache


def fixture():
    graph=nx.MultiDiGraph(crs='EPSG:4326')
    ids=[9007199254740993+2*i for i in range(8)]
    for i,node in enumerate(ids):graph.add_node(node,x=101+i*.001,y=3+(i%2)*.001)
    rng=random.Random(2025)
    for i,a in enumerate(ids):
        for j,b in enumerate(ids):
            if j==(i+1)%len(ids) or (i!=j and rng.random()<.15):
                graph.add_edge(a,b,length=rng.randrange(1,81)/4,travel_time=float(rng.randrange(1,8)),
                    geometry=LineString([(graph.nodes[a]['x'],graph.nodes[a]['y']),(graph.nodes[b]['x'],graph.nodes[b]['y'])]))
    return graph


def run(samples=30):
    logging.getLogger('api').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    graph=fixture();rows=[]
    for engine in ['native_bmssp_2025','native_reference_dijkstra']:
        for state in ['cold','warm']:
            with patch('graph_loader.load_native_graph',return_value=graph),TestClient(api.app) as client:
                body={'engine':engine,'locations':[str(x) for x in graph],'vehicle_count':2,
                      'demands':[0]+[1]*7,'capacities':[4,4],'max_search_seconds':1}
                snapshot_cache.clear()
                client.post('/vrp',json=body).raise_for_status()
                measurements={name:[] for name in ['matrix','solver','paths','geometry','serialization_probe','api']}
                for _ in range(samples):
                    if state=='cold':snapshot_cache.clear()
                    clock=perf_counter();response=client.post('/vrp',json=body);latency=perf_counter()-clock
                    response.raise_for_status();data=response.json()
                    assert data['status']=='FEASIBLE' and data['route_feasibility'] and data['selected_engine']==engine
                    assert sorted(x for r in data['routes'] for x in r[1:-1])==list(range(1,8))
                    assert data['metadata']['native_execution_diagnostics']['sssp_invocations']==8
                    totals=[]
                    for legs in data['route_legs']:
                        for leg in legs:
                            value=0.0
                            for edge in leg['original_edges']:
                                value+=graph[int(edge['u'])][int(edge['v'])][int(edge['key'])]['length']
                            assert value==leg['distance'];totals.append(value)
                    assert math.fsum(totals)==data['total_distance']
                    times=data['computation_times']
                    for name,value in zip(measurements,[times['matrix_computation'],times['vrp_solving'],times['path_reconstruction'],times['geometry_assembly'],times['serialization'],latency]):
                        measurements[name].append(value)
                def stats(values):
                    values=sorted(values)
                    return {'p50_seconds':statistics.median(values),'p95_seconds':values[(95*len(values)+99)//100-1]}
                rows.append({'engine':engine,'state':state,'samples':samples,'timings':{k:stats(v) for k,v in measurements.items()},
                             'last_native_diagnostics':data['metadata']['native_execution_diagnostics'],
                             'last_snapshot':data['graph_snapshot'],'last_total_distance':data['total_distance']})
    return {'seed':2025,'nodes':len(graph),'edges':graph.number_of_edges(),'density':graph.number_of_edges()/len(graph)**2,
            'sources':8,'vehicles':2,'samples_per_group':samples,'platform':platform.platform(),
            'peak_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'method':'In-process FastAPI TestClient; cold clears snapshot cache; warm retains snapshot/engine. Serializer timing is a JSON encoding probe before final JSONResponse encoding. p95 nearest rank.',
            'rows':rows}


if __name__=='__main__':print(json.dumps(run(),indent=2))
