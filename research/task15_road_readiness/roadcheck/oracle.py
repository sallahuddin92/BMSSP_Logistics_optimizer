"""Independent heapq Dijkstra on directed multigraphs. No native calls or clocks."""
import heapq
import math
import struct
from production_adapter import require
from .io import sha


def bits(value):
    require(type(value) is float and not math.isnan(value) and value >= 0,'DISTANCE_BINARY64')
    return struct.pack('<d',value).hex()


def vector_identity(distances):
    encoded=[bits(v) for v in distances]
    return encoded,sha(bytes.fromhex(''.join(encoded)))


def dijkstra(graph,source):
    require(source in graph.vertices,'ORACLE_SOURCE')
    adjacency={v:[] for v in graph.vertices}
    for eid,u,v,weight in graph.edges:
        require(u in adjacency and v in adjacency and math.isfinite(weight) and weight>=0,'ORACLE_EDGE')
        adjacency[u].append((v,weight))  # Preserve every parallel edge and its orientation.
    distances={v:math.inf for v in graph.vertices}
    distances[source]=0.0
    queue=[(0.0,source)]
    while queue:
        distance,u=heapq.heappop(queue)
        if distance != distances[u]:continue
        for v,weight in adjacency[u]:
            candidate=distance+weight
            require(math.isfinite(candidate),'ORACLE_DISTANCE_OVERFLOW')
            if candidate < distances[v]:
                distances[v]=candidate
                heapq.heappush(queue,(candidate,v))
    return [distances[v] for v in graph.vertices]
