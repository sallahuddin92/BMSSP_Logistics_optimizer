#!/usr/bin/env python3
"""Offline real-road differential, logistics and reproducible profiling runner.
All samples (including failures) are retained. Exit nonzero on any failed gate.
"""
import argparse
import cProfile
import json
import math
import os
from pathlib import Path
import platform
import random
import resource
import sys
import time
import traceback
import networkx as nx
import numpy as np
from native_graph import SnapshotCache
from road_fixture import load_fixture, load_fixture_snapshot, REGIONS
from road_geometry import assemble_geometry
from routing_adapter import compute_native_matrix


def timed(call):
    start = time.perf_counter()
    result = call()
    return result, time.perf_counter() - start


def distribution(samples):
    rows = sorted(samples)
    n = len(rows)
    return dict(
        count=n,
        p50=rows[math.ceil(n * 0.50) - 1],
        p95=rows[math.ceil(n * 0.95) - 1] if n >= 20 else None,
        p99=rows[math.ceil(n * 0.99) - 1] if n >= 100 else None,
    )


def run_region(name, output, samples, seed):
    directory = output / name
    directory.mkdir()
    report = {"region": name, "seed": seed, "samples": {}, "checks": {}, "failures": []}

    def save():
        report["peak_process_rss_bytes"] = resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss
        (directory / "results.json").write_text(
            json.dumps(report, indent=2, allow_nan=False)
        )

    try:
        place = "osm-fixture:" + name
        graph, report["fixture_load_seconds"] = timed(lambda: load_fixture(place))
        report["provenance"] = graph.graph["road_fixture_provenance"]
        profiler = cProfile.Profile()
        profiler.enable()
        cache = SnapshotCache()
        (snapshot, capture), report["instrumented_cold_snapshot_seconds"] = timed(
            lambda: cache.get(graph)
        )
        profiler.disable()
        profiler.dump_stats(str(directory / "capture.prof"))
        report["snapshot_id"] = snapshot.snapshot_id
        report["capture"] = capture
        print(name, "loaded", len(graph), graph.number_of_edges(), flush=True)
        warm = []
        for _ in range(20):
            (_, metadata), elapsed = timed(lambda: cache.get(graph))
            warm.append(elapsed)
        report["samples"]["warm_snapshot_seconds"] = warm
        immutable = load_fixture_snapshot(place)
        immutable_times = []
        selection_times = []
        for _ in range(20):
            (_, metadata), elapsed = timed(lambda: cache.get(immutable))
            immutable_times.append(elapsed)
            _, elapsed = timed(lambda: load_fixture_snapshot(place))
            selection_times.append(elapsed)
        report["samples"]["immutable_snapshot_seconds"] = immutable_times
        report["samples"]["verified_file_selection_seconds"] = selection_times
        cold_capture = []
        for _ in range(5):
            _, elapsed = timed(lambda: SnapshotCache().get(graph))
            cold_capture.append(elapsed)
        report["samples"]["cold_snapshot_seconds"] = cold_capture
        engines = {
            selected: snapshot.engine(selected)[0]
            for selected in ("native_bmssp_2025", "native_reference_dijkstra")
        }
        report["engine_metadata"] = engines["native_bmssp_2025"].metadata
        nodes = sorted(graph)
        rng = random.Random(seed)
        largest = sorted(max(nx.strongly_connected_components(graph), key=len))
        # Spatial extremes force long paths, plus component representatives and random sources.
        extremes = [
            min(largest, key=lambda n: graph.nodes[n][k]) for k in ("x", "y")
        ] + [max(largest, key=lambda n: graph.nodes[n][k]) for k in ("x", "y")]
        representatives = [
            min(c)
            for c in sorted(nx.weakly_connected_components(graph), key=lambda c: min(c))
        ]
        sources = list(
            dict.fromkeys(
                extremes + representatives[:8] + rng.sample(nodes, min(12, len(nodes)))
            )
        )
        report["oracle_sources"] = sources
        checked = 0
        paths = 0
        unreachable = 0
        geometry_statuses = {}
        longest = 0.0
        for source in sources:
            report["current_oracle_source"] = source
            print(name, "oracle source", source, flush=True)
            actual = engines["native_bmssp_2025"].solve(source)
            reference = engines["native_reference_dijkstra"].solve(source)
            nx_dist = nx.single_source_dijkstra_path_length(
                graph, source, weight="length"
            )
            assert actual.diagnostics["implementation"] == "BMSSP2025Engine::solve"
            for target in nodes:
                a, b, c = (
                    actual.distance(target),
                    reference.distance(target),
                    nx_dist.get(target, math.inf),
                )
                assert a == b == c, dict(
                    source=source, target=target, bmssp=a, dijkstra=b, networkx=c
                )
                checked += 1
                if not math.isfinite(a):
                    unreachable += 1
            # All original predecessor paths validated, not just a chosen destination.
            for target in nodes:
                path = snapshot.original_path(actual, target)
                if not path["reachable"]:
                    assert not path["vertices"] and not path["edges"]
                    continue
                assert path["vertices"][0] == source and path["vertices"][-1] == target
                assert len(path["vertices"]) == len(path["edges"]) + 1
                total = 0.0
                for a, b, e in zip(
                    path["vertices"], path["vertices"][1:], path["edges"]
                ):
                    u, v, key = snapshot.original_edges[e]
                    assert (a, b) == (u, v) and graph.has_edge(u, v, key)
                    total += float(graph[u][v][key]["length"])
                assert total == path["distance"]
                points, status = assemble_geometry(
                    snapshot, path["edges"], path["vertices"]
                )
                assert points, dict(source=source, target=target, geometry=status)
                geometry_statuses[status] = geometry_statuses.get(status, 0) + 1
                longest = max(longest, total)
                paths += 1
        report["checks"].update(
            distance_comparisons=checked,
            original_paths=paths,
            unreachable_comparisons=unreachable,
            geometry_statuses=geometry_statuses,
            longest_path_m=longest,
            one_way_edges=sum(
                bool(d.get("oneway")) for _, _, d in graph.edges(data=True)
            ),
            parallel_pairs=report["provenance"]["parallel_pairs"],
            large_node_ids=max(nodes) > 2**32,
        )
        # Explicit directed reverse difference and edge-specific parallel checks.
        differences = []
        for u, v, d in graph.edges(data=True):
            if d.get("oneway") and not graph.has_edge(v, u):
                a = engines["native_bmssp_2025"].solve(u).distance(v)
                b = engines["native_bmssp_2025"].solve(v).distance(u)
                if a != b:
                    differences.append(
                        dict(
                            u=u, v=v, forward=a, reverse=b if math.isfinite(b) else None
                        )
                    )
                    break
        assert differences, "Expected a directed asymmetric road pair"
        report["checks"]["directed_asymmetry"] = differences
        chosen = list(dict.fromkeys(extremes))[:4]
        for node in largest:
            if len(chosen) >= 4:
                break
            if node not in chosen:
                chosen.append(node)
        locations = chosen + [chosen[0]]
        matrix, meta = compute_native_matrix(snapshot, locations)
        expected = np.array(
            [
                [
                    nx.single_source_dijkstra_path_length(
                        graph, u, weight="length"
                    ).get(v, math.inf)
                    for v in locations
                ]
                for u in locations
            ]
        )
        assert np.array_equal(matrix, expected) and meta[
            "native_execution_diagnostics"
        ]["sssp_invocations"] == len(chosen)
        report["checks"]["repeated_source_matrix"] = meta
        query_sources = [rng.choice(nodes) for _ in range(samples)]
        report["query_sources"] = query_sources
        for selected, engine in engines.items():
            times = []
            diagnostics = []
            report["samples"][selected] = times
            report[selected + "_diagnostics"] = diagnostics
            for source in query_sources:
                started = time.perf_counter()
                try:
                    result = engine.solve(source)
                except Exception:
                    report["failed_query_sample"] = dict(
                        engine=selected,
                        source=source,
                        elapsed_seconds=time.perf_counter() - started,
                    )
                    raise
                elapsed = time.perf_counter() - started
                times.append(elapsed)
                diagnostics.append(result.diagnostics)
            report["samples"][selected] = times
            report[selected + "_diagnostics"] = diagnostics
        profiles = []
        for source in extremes:
            result, elapsed = timed(
                lambda: engines["native_bmssp_2025"].solve(source, profile=True)
            )
            profiles.append(
                dict(
                    source=source, wall_seconds=elapsed, diagnostics=result.diagnostics
                )
            )
        report["instrumented_profiles"] = profiles
        save()
        print(name, "native profiling complete", flush=True)
        # Separate cold construction, result wrapping, extraction and path reconstruction.
        cold = []
        import bmssp_native

        for _ in range(10):
            _, elapsed = timed(
                lambda: bmssp_native.BMSSP2025Engine(snapshot.native_graph)
            )
            cold.append(elapsed)
        report["samples"]["cold_degree_reduction_seconds"] = cold
        result = engines["native_bmssp_2025"].solve(chosen[0])
        path_times = []
        extract = []
        for _ in range(100):
            _, elapsed = timed(lambda: result.path(chosen[-1]))
            path_times.append(elapsed)
            _, elapsed = timed(lambda: result.distances_to(nodes))
            extract.append(elapsed)
        report["samples"]["path_binding_seconds"] = path_times
        report["samples"]["all_distances_binding_seconds"] = extract
        matrices = {}
        for count in (1, 4, 8):
            locs = largest[:: max(1, len(largest) // count)][:count]
            rows = []
            for _ in range(10):
                (_, metadata), elapsed = timed(
                    lambda: compute_native_matrix(snapshot, locs)
                )
                rows.append(dict(wall_seconds=elapsed, metadata=metadata))
            matrices[str(count)] = rows
        report["matrices"] = matrices
        # Real production API, explicit place; no monkeypatch or generated road edges.
        from fastapi.testclient import TestClient
        import api

        client = TestClient(api.app)
        base = dict(
            locations=[str(n) for n in chosen], engine="native_bmssp_2025", place=place
        )
        requests = [
            ("one_vehicle", {**base, "vehicle_count": 1}),
            (
                "multiple_capacity",
                {
                    **base,
                    "vehicle_count": 2,
                    "demands": [0, 1, 1, 1],
                    "capacities": [2, 2],
                },
            ),
            (
                "infeasible_capacity",
                {
                    **base,
                    "vehicle_count": 1,
                    "demands": [0, 1, 1, 1],
                    "capacities": [1],
                },
            ),
            ("missing_durations", {**base, "time_windows": [[0, 10000]] * 4}),
        ]
        # A stop in a different actual weak component must be unreachable in both directions.
        if len(representatives) > 1:
            other = next(
                n for n in representatives if not nx.has_path(graph, chosen[0], n)
            )
            requests.append(
                ("disconnected", {**base, "locations": [str(chosen[0]), str(other)]})
            )
        report["api"] = []
        for label, body in requests:
            response, elapsed = timed(lambda: client.post("/vrp", json=body))
            data = response.json()
            row = dict(
                case=label,
                request=body,
                http_status=response.status_code,
                wall_seconds=elapsed,
                response=data,
            )
            report["api"].append(row)
            if label == "missing_durations":
                assert response.status_code == 400
                continue
            assert response.status_code == 200, row
            if label.startswith("infeasible") or label == "disconnected":
                assert data["status"] == "NO_SOLUTION" and not data["routes"]
                continue
            assert (
                data["status"] == "FEASIBLE"
                and data["route_feasibility"]
                and data["exact_routing"]
            )
            assert data["graph_snapshot"] == snapshot.snapshot_id
            assert data["metadata"]["native_execution_diagnostics"][
                "sssp_invocations"
            ] == len(chosen)
            served = []
            for index, (route, legs) in enumerate(
                zip(data["routes"], data["route_legs"])
            ):
                assert route[0] == route[-1] == 0
                served.extend(route[1:-1])
                if "capacities" in body:
                    assert data["vehicle_loads"][index] <= body["capacities"][index]
                for leg in legs:
                    a, b = int(leg["source"]), int(leg["target"])
                    assert leg["path_status"] == "VERIFIED" and leg["geometry"]
                    assert leg["distance"] == engines["native_bmssp_2025"].solve(
                        a
                    ).distance(b)
            assert sorted(served) == list(range(1, len(chosen)))
            _, serialization = timed(lambda: json.dumps(data))
            row["serialization_seconds"] = serialization
        # Export exact UI stop coordinates so the browser can click real road nodes.
        report["browser_locations"] = [
            dict(id=str(n), lat=graph.nodes[n]["y"], lon=graph.nodes[n]["x"])
            for n in chosen[:3]
        ]
        report["summaries"] = {k: distribution(v) for k, v in report["samples"].items()}
        report["status"] = "PASS"
    except Exception as exc:
        report["status"] = "FAIL"
        report["failures"].append(
            dict(error=str(exc), traceback=traceback.format_exc())
        )
        raise
    finally:
        save()
    print(name, report["status"], report["summaries"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--regions", nargs="+", choices=REGIONS, default=list(REGIONS))
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261105)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("samples must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "environment.json").write_text(
        json.dumps(
            dict(
                python=sys.version,
                platform=platform.platform(),
                machine=platform.machine(),
                seed=args.seed,
                argv=sys.argv,
            ),
            indent=2,
        )
    )
    for name in args.regions:
        run_region(name, args.output, args.samples, args.seed)
