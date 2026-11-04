"""Immutable selected-road metadata and canonical [latitude, longitude] geometry."""
from dataclasses import dataclass
import math
import numbers
from types import MappingProxyType
from pyproj import CRS


def coordinate(x, y):
    if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, numbers.Real) or not isinstance(y, numbers.Real):
        return None
    x, y = float(x), float(y)
    return (y, x) if math.isfinite(x) and math.isfinite(y) and -180 <= x <= 180 and -90 <= y <= 90 else None


@dataclass(frozen=True)
class RoadEdge:
    length: float
    points: object
    explicit_geometry: bool
    travel_time: object


@dataclass(frozen=True)
class RoadData:
    nodes: object
    edges: object
    geographic: bool


class GeometryBudgetExceeded(RuntimeError):
    pass


def capture_roads(graph, nodes, mapping, max_points=200000):
    point_count = 0
    try:
        geographic = CRS.from_user_input(graph.graph.get('crs', 'EPSG:4326')).equals(CRS.from_epsg(4326), ignore_axis_order=True)
    except Exception:
        geographic = False
    coords = {i: coordinate(graph.nodes[original].get('x'), graph.nodes[original].get('y')) if geographic else None for i, original in nodes.items()}
    edges = {}
    for native_id, (u, v, key) in mapping.items():
        data = graph[u][v][key] if graph.is_multigraph() else graph[u][v]
        geometry = data.get('geometry')
        points = None
        if geographic and geometry is not None:
            try:
                if geometry.geom_type == 'LineString':
                    values = []
                    for pair in geometry.coords:
                        point_count += 1
                        if point_count > max_points:
                            raise GeometryBudgetExceeded('Snapshot geometry capture budget exceeded')
                        values.append(coordinate(*pair) if len(pair) == 2 else None)
                    if len(values) >= 2 and all(p is not None for p in values):
                        points = tuple(values)
            except (AttributeError, TypeError, ValueError):
                pass
        duration = data.get('travel_time')
        if isinstance(duration, bool) or not isinstance(duration, numbers.Real) or not math.isfinite(duration) or duration < 0:
            duration = None
        edges[native_id] = RoadEdge(float(data['length']), points, geometry is not None,
                                    float(duration) if duration is not None else None)
    road = RoadData(MappingProxyType(coords), MappingProxyType(edges), geographic)
    content = (geographic, tuple(sorted(coords.items())), tuple(sorted(edges.items())))
    return road, content


def close(a, b):
    return a is not None and b is not None and max(abs(a[i]-b[i]) for i in (0,1)) <= 1e-7


def assemble_geometry(snapshot, native_edges, vertices):
    road = snapshot.road_data
    if not native_edges:
        point = road.nodes.get(vertices[0])
        return ([list(point)] if point is not None else []), 'STATIONARY' if point is not None else 'UNAVAILABLE'
    result = []
    endpoint_only = False
    for edge_id, a, b in zip(native_edges, vertices, vertices[1:]):
        edge = road.edges[edge_id]
        start, end = road.nodes[a], road.nodes[b]
        if start is None or end is None:
            return [], 'UNAVAILABLE'
        points = edge.points
        if points is None:
            if edge.explicit_geometry:
                return [], 'UNAVAILABLE'
            points = (start, end)
            endpoint_only = True
        elif not (close(points[0], start) and close(points[-1], end)) and close(points[0], end) and close(points[-1], start):
            points = tuple(reversed(points))
        if not close(points[0], start) or not close(points[-1], end):
            return [], 'UNAVAILABLE'
        if result and not close(result[-1], points[0]):
            return [], 'UNAVAILABLE'
        result.extend(points[1:] if result else points)
    return [list(p) for p in result], 'ENDPOINTS_ONLY' if endpoint_only else 'AVAILABLE'
