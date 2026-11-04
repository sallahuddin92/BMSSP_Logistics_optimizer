import networkx as nx
import pytest
from shapely.geometry import LineString

@pytest.fixture
def cycle():
    ids = [9007199254740993, 9007199254740995, 9007199254740997]
    g = nx.MultiDiGraph(crs='EPSG:4326')
    coords = [(101.0, 3.0), (101.01, 3.0), (101.01, 3.01)]
    for node, (x,y) in zip(ids, coords): g.add_node(node, x=x, y=y)
    g.add_edge(ids[0], ids[1], key=7, length=100.25, travel_time=3.0,
               geometry=LineString([coords[0], (101.005,3.002), coords[1]]))
    g.add_edge(ids[0], ids[1], key=8, length=500, travel_time=8.0)
    # Stored geometry is reversed: drawing must respect the selected directed arc.
    g.add_edge(ids[1], ids[2], key=7, length=200.5, travel_time=4.0,
               geometry=LineString([coords[2], coords[1]]))
    g.add_edge(ids[2], ids[0], key=7, length=300.75, travel_time=5.0,
               geometry=LineString([coords[2], coords[0]]))
    return g
