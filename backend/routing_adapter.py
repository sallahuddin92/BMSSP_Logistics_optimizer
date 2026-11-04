"""Explicit native matrix execution, independent of all legacy fallbacks."""
import math
from time import perf_counter
import numpy as np
from native_graph import RoutingLimits, RoutingBudgetExceeded, normalize_node_id

NATIVE_ENGINES = ("native_bmssp_2025", "native_reference_dijkstra")


def compute_native_matrix(graph_snapshot, locations, engine="native_bmssp_2025", limits=None):
    start = perf_counter()
    limits = limits or RoutingLimits.from_environment()
    if engine not in NATIVE_ENGINES:
        raise ValueError("Unsupported native engine")
    if not isinstance(locations, (list, tuple)) or not locations:
        raise ValueError("Native routing requires a nonempty location sequence")
    if len(locations) > limits.max_locations:
        raise RoutingBudgetExceeded("Native location budget exceeded")
    graph_size = graph_snapshot.native_graph.metadata
    if graph_size["vertex_count"] > limits.max_nodes or graph_size["edge_count"] > limits.max_edges:
        raise RoutingBudgetExceeded("Native graph node/edge budget exceeded")
    nodes = [normalize_node_id(loc) for loc in locations]
    sources = list(dict.fromkeys(nodes))
    if len(sources) > limits.max_sources:
        raise RoutingBudgetExceeded("Native distinct-source budget exceeded")
    for node in nodes:
        if node not in graph_snapshot.original_nodes:
            raise ValueError(f"Node {node} not in graph snapshot")
    prepared_start = perf_counter()
    prepared, created = graph_snapshot.engine(engine)
    prepare_time = perf_counter() - prepared_start
    matrix = np.full((len(nodes), len(nodes)), np.inf, dtype=np.float64)
    diagnostics = []
    query_time = 0.0
    binding_overhead = 0.0
    extraction_time = 0.0
    rows_by_source = {}
    for row_index, node in enumerate(nodes):
        rows_by_source.setdefault(node, []).append(row_index)
    for source in sources:
        query_start = perf_counter()
        result = prepared.solve(source)
        call_time = perf_counter() - query_start
        if result.algorithm != engine:
            raise RuntimeError("Native engine identity mismatch")
        diag = result.diagnostics
        native_time = diag["query_seconds"]
        query_time += native_time
        # Wall time includes result wrapping and transfer; timer noise is retained.
        binding_overhead += call_time - native_time
        diag["source"] = source
        diagnostics.append(diag)
        extraction_start = perf_counter()
        row = result.distances_to(nodes)
        if any(math.isnan(value) or value < 0 for value in row):
            raise RuntimeError("Native engine returned invalid distances")
        for row_index in rows_by_source[source]:
            matrix[row_index] = row
        extraction_time += perf_counter() - extraction_start
    reachable = np.isfinite(matrix)
    meta = {
        "selected_engine": engine,
        "algorithm_version": "arxiv:2504.17033v2" if engine == "native_bmssp_2025" else "native-dijkstra-v1",
        "graph_snapshot": graph_snapshot.snapshot_id,
        "graph_metadata": graph_snapshot.native_graph.metadata,
        "weight_units": "meters", "exact_routing": True,
        "arithmetic": "checked IEEE-754 binary64; no road-distance approximation",
        "unreachable_pair_count": int(np.count_nonzero(~reachable)),
        "reachability": reachable.tolist(),
        "fallback_counts": {"symmetric": 0, "haversine": 0},
        "approximation_provenance": [],
        "native_execution_diagnostics": {"sssp_invocations": len(sources), "sources": diagnostics,
                                         "engine_prepared_now": created,
                                         "degree_reduction_count": int(created and engine == "native_bmssp_2025")},
        "preprocessing_time": prepare_time if created else 0.0,
        "degree_reduction_time": diagnostics[0].get("preprocessing_seconds", 0.0)
                                 if created and engine == "native_bmssp_2025" else 0.0,
        "query_time": query_time, "query_wall_residual_time": binding_overhead,
        "matrix_extraction_time": extraction_time,
        "matrix_total_time": perf_counter() - start,
    }
    return matrix, meta
