"""Local offline browser/benchmark harness ONLY; never imported by production api.

Run: python -m uvicorn logistics_tests.fixture_app:app --host 127.0.0.1 --port 8877
"""
from pathlib import Path
import networkx as nx
from shapely.geometry import LineString
from fastapi.staticfiles import StaticFiles
from fastapi import Body
import api
import graph_loader

IDS=[9007199254740993,9007199254740995,9007199254740997]
mode='cycle'

def graph_fixture(selected='cycle'):
    g=nx.MultiDiGraph(crs='EPSG:4326')
    coords=[(101,3),(101.01,3),(101.01,3.01)]
    for node,(x,y) in zip(IDS,coords):g.add_node(node,x=x,y=y)
    for i in range(3 if selected!='oneway' else 2):
        a,b=IDS[i],IDS[(i+1)%3]
        points=[coords[i],coords[(i+1)%3]]
        if i==0:points.insert(1,(101.005,3.002))
        g.add_edge(a,b,key=7,length=[100.25,200.5,300.75][i],travel_time=[3,4,5][i],geometry=LineString(points))
    if selected=='missing_geometry':g.nodes[IDS[1]].pop('x')
    return g

current=graph_fixture()
def native_graph(place=None):
    if mode=='failure':raise RuntimeError('PRIVATE_TEST_SERVER_ERROR')
    return current

graph_loader.load_native_graph=native_graph
graph_loader.load_graph=lambda *args,**kwargs:current
app=api.app
@app.post('/fixture-mode')
def fixture_mode(value:dict=Body(...)):
    global mode,current
    mode=value['mode'];current=graph_fixture(mode)
    return {'mode':mode}
app.mount('/ui',StaticFiles(directory=Path(__file__).resolve().parents[2]/'frontend',html=True),name='fixture-ui')
