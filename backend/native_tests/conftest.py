import networkx as nx
import pytest


@pytest.fixture
def roads():
    graph = nx.MultiDiGraph()
    graph.add_nodes_from([5_000_000_000, 5_000_000_001, 5_000_000_002, -7, 42])
    graph.add_edge(5_000_000_000, 5_000_000_001, key=0, length=8.0)
    graph.add_edge(5_000_000_000, 5_000_000_001, key=1, length=2.25)
    graph.add_edge(5_000_000_001, 5_000_000_002, key=0, length=0.0)
    graph.add_edge(5_000_000_000, 5_000_000_002, key="alternative", length=2.25)
    graph.add_edge(5_000_000_002, -7, key=0, length=1.0)
    return graph
