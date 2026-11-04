"""Validated immutable routing snapshots. No NetworkX path computation occurs here."""
from collections import OrderedDict
from dataclasses import dataclass, field
import hashlib
import importlib
import math
import numbers
import os
import re
import threading
from time import perf_counter
from types import MappingProxyType
import weakref

import networkx as nx
from road_geometry import capture_roads, GeometryBudgetExceeded


class NativeUnavailable(RuntimeError):
    pass


class RoutingBudgetExceeded(ValueError):
    pass


def positive_budget(name, default):
    raw = os.environ.get(name, str(default))
    if not re.fullmatch(r"[1-9][0-9]*", raw):
        raise ValueError(f"{name} must be a positive integer")
    return int(raw)


@dataclass(frozen=True)
class RoutingLimits:
    max_nodes: int = 10_000
    max_edges: int = 40_000
    max_locations: int = 128
    max_sources: int = 32

    @classmethod
    def from_environment(cls):
        return cls(*(positive_budget(name, default) for name, default in (
            ("NATIVE_MAX_NODES", 10_000), ("NATIVE_MAX_EDGES", 40_000),
            ("NATIVE_MAX_LOCATIONS", 128), ("NATIVE_MAX_SOURCES", 32))))


def native_module():
    try:
        return importlib.import_module("bmssp_native")
    except (ImportError, OSError) as exc:
        raise NativeUnavailable("bmssp_native is unavailable; build the native extension for this Python") from exc


def normalize_node_id(value):
    if isinstance(value, bool):
        raise ValueError("Boolean node IDs are unsupported")
    if isinstance(value, numbers.Integral):
        result = int(value)
    elif isinstance(value, str) and re.fullmatch(r"[+-]?[0-9]+", value, flags=re.ASCII):
        result = int(value)
    else:
        raise ValueError(f"Expected an integer or decimal string node ID: {value!r}")
    if not -(2**63) <= result < 2**63:
        raise ValueError("Node ID is outside signed 64-bit range")
    return result


def _key_token(key):
    if isinstance(key, numbers.Integral) and not isinstance(key, bool):
        return ("integer", int(key))
    if isinstance(key, str):
        return ("string", key)
    raise ValueError("MultiDiGraph edge keys must be integers or strings")


def _capture(graph, weight, limits):
    if not isinstance(graph, (nx.DiGraph, nx.MultiDiGraph)) or not graph.is_directed():
        raise ValueError("Native routing requires a directed NetworkX graph")
    if len(graph) > limits.max_nodes or graph.number_of_edges() > limits.max_edges:
        raise RoutingBudgetExceeded("Native graph node/edge budget exceeded")
    if graph.graph.get("routing_data_origin") == "synthetic_fallback":
        raise ValueError("Synthetic fallback graphs are forbidden for native routing")
    if graph.graph.get("routing_weight_units", "meters") != "meters":
        raise ValueError("Native road weights must be meters")
    nodes = {}
    for original in graph.nodes:
        node = normalize_node_id(original)
        if node in nodes:
            raise ValueError("Node IDs collide after normalization")
        nodes[node] = original
    rows = []
    items = graph.edges(keys=True, data=True) if graph.is_multigraph() else (
        (u, v, None, data) for u, v, data in graph.edges(data=True))
    for u, v, key, data in items:
        value = data.get(weight)
        if isinstance(value, bool) or not isinstance(value, numbers.Real):
            raise ValueError(f"Edge {(u, v, key)!r} requires a numeric {weight!r} weight")
        length = float(value)
        if not math.isfinite(length) or length < 0:
            raise ValueError(f"Edge {(u, v, key)!r} has invalid road weight")
        a, b = normalize_node_id(u), normalize_node_id(v)
        rows.append((a, b, _key_token(key) if graph.is_multigraph() else ("simple", ""),
                     length, (u, v, key)))
    rows.sort(key=lambda row: row[:3])
    ids = sorted(nodes)
    # Canonical input includes original node identity type/spelling and edge keys.
    content = (weight, tuple((i, type(nodes[i]).__name__, str(nodes[i])) for i in ids),
               tuple((a, b, key, length.hex()) for a, b, key, length, _ in rows))
    digest = hashlib.sha256(repr(content).encode("utf-8")).hexdigest()
    edges = [(i, a, b, w) for i, (a, b, _, w, _) in enumerate(rows)]
    mapping = {i: row[4] for i, row in enumerate(rows)}
    try:
        road, road_content = capture_roads(graph, nodes, mapping, positive_budget("NATIVE_SNAPSHOT_MAX_GEOMETRY_POINTS", 200000))
    except GeometryBudgetExceeded as exc:
        raise RoutingBudgetExceeded(str(exc)) from exc
    digest = hashlib.sha256((digest + repr(road_content)).encode("utf-8")).hexdigest()
    return digest, ids, edges, nodes, mapping, road


@dataclass(frozen=True)
class GraphSnapshot:
    native_graph: object
    snapshot_id: str
    original_nodes: object
    original_edges: object
    timings: object
    weight: str
    road_data: object = None
    provenance_json: str = "{}"
    geometry_points: int = field(init=False, default=0)
    _engines: dict = field(default_factory=dict, repr=False, compare=False)
    _lock: object = field(default_factory=threading.RLock, repr=False, compare=False)

    def __post_init__(self):
        if self.road_data is not None:
            object.__setattr__(self, "geometry_points", sum(len(e.points) for e in self.road_data.edges.values() if e.points is not None))

    def engine(self, selected):
        if selected not in ("native_bmssp_2025", "native_reference_dijkstra"):
            raise ValueError("Unsupported native engine")
        with self._lock:
            created = selected not in self._engines
            if created:
                module = native_module()
                cls = module.BMSSP2025Engine if selected == "native_bmssp_2025" else module.NativeReferenceDijkstra
                self._engines[selected] = cls(self.native_graph)
            return self._engines[selected], created

    def original_path(self, result, target):
        if not result.belongs_to(self.native_graph):
            raise ValueError("Result belongs to a different native graph snapshot")
        path = result.path(normalize_node_id(target))
        return {**path, "original_edges": [self.original_edges[i] for i in path["edges"]],
                "original_vertices": [self.original_nodes[i] for i in path["vertices"]]}


class SnapshotCache:
    """Bounded LRU keyed by weak source identity, validated content and configuration.

    Mutable inputs are scanned/validated on every lookup; identity alone is never
    a cache hit. Explicit GraphSnapshot inputs reuse immutable captured content.
    Snapshots already handed to callers remain immutable.
    Source graph mutations must be serialized by their owner during capture.
    """
    def __init__(self, max_entries=2):
        if max_entries < 1:
            raise ValueError("Snapshot cache capacity must be positive")
        self.max_entries = max_entries
        self._entries = OrderedDict()
        self._lock = threading.RLock()

    def get(self, graph, weight="length", limits=None):
        limits = limits or RoutingLimits.from_environment()
        if weight != "length":
            raise ValueError("Native road routing currently supports only length in meters")
        start = perf_counter()
        # Explicit immutable input contract, never inferred from NetworkX identity,
        # graph attributes, nx.freeze(), file timestamps, or a caller version token.
        if isinstance(graph, GraphSnapshot):
            size = graph.native_graph.metadata
            if (size["vertex_count"] > limits.max_nodes or size["edge_count"] > limits.max_edges
                    or graph.geometry_points > positive_budget("NATIVE_SNAPSHOT_MAX_GEOMETRY_POINTS", 200000)):
                raise RoutingBudgetExceeded("Immutable snapshot exceeds routing/geometry budget")
            if graph.weight != weight:
                raise ValueError("Snapshot weight mismatch")
            return graph, {"cache_hit": True, "immutable_snapshot_reused": True,
                           "snapshot_validation_time": perf_counter()-start,
                           "adapter_conversion_time": 0.0, "native_graph_construction_time": 0.0}
        with self._lock:
            try:
                digest, ids, edges, nodes, mapping, road = _capture(graph, weight, limits)
            except RuntimeError as exc:
                raise ValueError("Graph changed during snapshot capture") from exc
            validated = perf_counter() - start
            key = (id(graph), digest, weight, limits)
            old = self._entries.get(key)
            if old is not None and old[0]() is graph:
                self._entries.move_to_end(key)
                return old[1], {"cache_hit": True, "snapshot_validation_time": validated,
                                "adapter_conversion_time": validated, "native_graph_construction_time": 0.0}
            module = native_module()
            native_start = perf_counter()
            native_graph = module.NativeGraph(ids, edges)
            construction = perf_counter() - native_start
            # Reject a source changed while native construction released the GIL.
            if _capture(graph, weight, limits)[0] != digest:
                raise ValueError("Graph changed during native snapshot construction")
            snapshot = GraphSnapshot(native_graph, digest, MappingProxyType(nodes),
                                     MappingProxyType(mapping), MappingProxyType({
                                         "adapter_conversion_time": validated,
                                         "native_graph_construction_time": construction}), weight, road)
            # Retire previous versions of the same source instead of retaining stale entries.
            for previous in list(self._entries):
                if previous[0] == id(graph):
                    del self._entries[previous]
            self._entries[key] = (weakref.ref(graph), snapshot)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
            return snapshot, {"cache_hit": False, "snapshot_validation_time": validated,
                              **snapshot.timings}

    def clear(self):
        with self._lock:
            self._entries.clear()


snapshot_cache = SnapshotCache(positive_budget("NATIVE_SNAPSHOT_CACHE_ENTRIES", 2))
