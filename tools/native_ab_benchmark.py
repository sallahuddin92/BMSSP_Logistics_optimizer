#!/usr/bin/env python3
"""Counterbalanced, separate-process native A/B replay. Never downloads road data.

The same Task 8 query JSONs and verified GraphML snapshots feed every process.
Profiling stays disabled in timed queries. Warmups, failures, every latency,
distance/path fingerprints, work counters, preprocessing and host samples persist.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import select
import statistics
import struct
import subprocess
import sys
import time
import traceback

REGIONS = ("seremban-small", "seremban-medium", "seremban-port-dickson")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distribution(values):
    ordered = sorted(values)
    n = len(ordered)
    return {
        "count": n,
        "p50": ordered[math.ceil(n * 0.5) - 1],
        "p95": ordered[math.ceil(n * 0.95) - 1] if n >= 20 else None,
        "p99": ordered[math.ceil(n * 0.99) - 1] if n >= 100 else None,
    }


def host():
    return {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "load_average": os.getloadavg(),
        "cpu_processes": subprocess.check_output(
            ["ps", "-Ao", "pid,pcpu,pmem,comm", "-r"], text=True
        ).splitlines()[:16],
        "vm_stat": subprocess.check_output(["vm_stat"], text=True),
        "thermal": subprocess.run(
            ["pmset", "-g", "therm"], capture_output=True, text=True
        ).stdout,
    }


def worker(args):
    sys.path.insert(0, str(args.extension.resolve()))
    import resource
    import bmssp_native as native
    from road_fixture import load_fixture_snapshot
    from routing_adapter import compute_native_matrix

    snapshots = {}
    records = {}
    engines = {}
    preparation = {}
    for region in REGIONS:
        record = json.loads((args.queries / region / "results.json").read_text())
        snapshot = load_fixture_snapshot("osm-fixture:" + region)
        assert snapshot.snapshot_id == record["snapshot_id"]
        began = time.perf_counter()
        engine, _ = snapshot.engine("native_bmssp_2025")
        preparation[region] = {
            "wall_seconds": time.perf_counter() - began,
            "metadata": engine.metadata,
            "snapshot_id": snapshot.snapshot_id,
            "graph_file_sha256": record["provenance"]["graph_sha256"],
            "query_file_sha256": sha(args.queries / region / "results.json"),
        }
        snapshots[region] = snapshot
        records[region] = record
        engines[region] = engine
    print(
        json.dumps(
            {
                "ready": True,
                "pid": os.getpid(),
                "extension": native.__file__,
                "binary_sha256": sha(Path(native.__file__)),
                "compiler": native.compiler,
                "preparation": preparation,
            }
        ),
        flush=True,
    )
    for line in sys.stdin:
        request = json.loads(line)
        region = request["region"]
        record = records[region]
        response = {
            "region": region,
            "trial": request["trial"],
            "samples": [],
            "matrices": {},
            "failures": [],
        }
        try:
            engine = engines[region]
            snapshot = snapshots[region]
            warm = []
            for source in record["query_sources"][:8]:
                began = time.perf_counter()
                engine.solve(source)
                warm.append(time.perf_counter() - began)
            response["warmup_seconds"] = warm
            targets = record["oracle_sources"][:4]
            for index, source in enumerate(record["query_sources"]):
                began = time.perf_counter()
                try:
                    result = engine.solve(source)
                except Exception:
                    response["failed_sample"] = {
                        "index": index,
                        "source": source,
                        "seconds": time.perf_counter() - began,
                    }
                    raise
                elapsed = time.perf_counter() - began
                assert result.algorithm == "native_bmssp_2025"
                d = result.diagnostics
                assert all(value["calls"] == 0 for value in d["profile"].values())
                if "label_nodes_materialized" in d:
                    assert d["label_nodes_materialized"] == d["label_updates"] + 1
                    assert d["label_nodes_materialized"] <= d["label_nodes_created"]
                distances = result.distances
                digest = hashlib.sha256(
                    struct.pack("<" + "d" * len(distances), *distances)
                ).hexdigest()
                paths = [result.path(target) for target in targets]
                path_digest = hashlib.sha256(
                    json.dumps(paths, sort_keys=True).encode()
                ).hexdigest()
                work = {
                    k: v
                    for k, v in d.items()
                    if k
                    not in (
                        "query_seconds",
                        "preprocessing_seconds",
                        "profile",
                        "label_nodes_materialized",
                    )
                }
                response["samples"].append(
                    {
                        "source": source,
                        "seconds": elapsed,
                        "native_seconds": d["query_seconds"],
                        "label_nodes_materialized": d.get(
                            "label_nodes_materialized", d["label_nodes_created"]
                        ),
                        "distance_sha256": digest,
                        "path_sha256": path_digest,
                        "work": work,
                    }
                )
            for count in (1, 4, 8):
                locations = list(dict.fromkeys(record["query_sources"]))[:count]
                rows = []
                response["matrices"][str(count)] = rows
                for _ in range(args.matrix_repeats):
                    began = time.perf_counter()
                    matrix, meta = compute_native_matrix(snapshot, locations)
                    elapsed = time.perf_counter() - began
                    rows.append(
                        {
                            "seconds": elapsed,
                            "sha256": hashlib.sha256(matrix.tobytes()).hexdigest(),
                            "query_seconds": meta["query_time"],
                            "extraction_seconds": meta["matrix_extraction_time"],
                        }
                    )
            response["peak_rss_bytes"] = resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
            response["resident_rss_bytes"] = (
                int(
                    subprocess.check_output(
                        ["ps", "-o", "rss=", "-p", str(os.getpid())], text=True
                    ).strip()
                )
                * 1024
            )
            response["summary"] = distribution(
                [row["seconds"] for row in response["samples"]]
            )
            response["status"] = "PASS"
        except Exception:
            response["status"] = "FAIL"
            response["failures"].append(traceback.format_exc())
        print(json.dumps(response, allow_nan=False), flush=True)


def reference_comparison(args):
    """Fresh in-process interleaved BMSSP/Dijkstra comparison, separate from A/B."""
    args.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(args.extension.resolve()))
    import bmssp_native as native
    from road_fixture import load_fixture_snapshot

    metadata = {
        "binary_sha256": sha(Path(native.__file__)),
        "host": host(),
        "regions": {},
        "failures": [],
    }
    try:
        for region in REGIONS:
            record = json.loads((args.queries / region / "results.json").read_text())
            snapshot = load_fixture_snapshot("osm-fixture:" + region)
            assert snapshot.snapshot_id == record["snapshot_id"]
            prepared, _ = snapshot.engine("native_bmssp_2025")
            engines = {
                "bmssp": prepared,
                "dijkstra": native.NativeReferenceDijkstra(snapshot.native_graph),
            }
            rows = {key: [] for key in engines}
            metadata["regions"][region] = {
                "snapshot_id": snapshot.snapshot_id,
                "samples": rows,
            }
            for source in record["query_sources"][:8]:
                for engine in engines.values():
                    engine.solve(source)
            for index, source in enumerate(record["query_sources"]):
                results = {}
                for key in list(engines) if index % 2 == 0 else list(reversed(engines)):
                    start = time.perf_counter()
                    result = engines[key].solve(source)
                    elapsed = time.perf_counter() - start
                    rows[key].append(
                        {
                            "source": source,
                            "seconds": elapsed,
                            "diagnostics": result.diagnostics,
                        }
                    )
                    results[key] = result
                assert results["bmssp"].distances == results["dijkstra"].distances
            metadata["regions"][region]["summaries"] = {
                key: distribution([row["seconds"] for row in values])
                for key, values in rows.items()
            }
            print(region, metadata["regions"][region]["summaries"], flush=True)
        metadata["status"] = "PASS"
    except Exception:
        metadata["status"] = "FAIL"
        metadata["failures"].append(traceback.format_exc())
        raise
    finally:
        (args.output / "results.json").write_text(json.dumps(metadata, indent=2))


def receive(process, timeout=600):
    if not select.select([process.stdout], [], [], timeout)[0]:
        raise TimeoutError("Worker response deadline exceeded")
    line = process.stdout.readline()
    if not line:
        raise RuntimeError(f"Worker exited {process.poll()} before a response")
    return json.loads(line)


def controller(args):
    args.output.mkdir(parents=True, exist_ok=False)
    variants = dict(value.split("=", 1) for value in args.variant)
    if len(variants) != len(args.variant) or not 1 <= len(variants) <= 3:
        raise ValueError("Provide one to three unique variants")
    processes = {}
    logs = []
    report = {
        "variants": {},
        "jobs": [],
        "failures": [],
        "argv": sys.argv,
        "host_initial": host(),
        "fresh_processes_per_trial": True,
        "trial_builds": {},
    }
    try:
        for label, extension in variants.items():
            log = (args.output / (label + "-stderr.log")).open("x")
            logs.append(log)
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--worker",
                "--extension",
                extension,
                "--queries",
                str(args.queries.resolve()),
                "--matrix-repeats",
                str(args.matrix_repeats),
            ]
            proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=log,
                text=True,
                bufsize=1,
            )
            processes[label] = proc
            report["variants"][label] = receive(proc)
            assert report["variants"][label]["ready"]
        (args.output / "builds.json").write_text(
            json.dumps(report["variants"], indent=2)
        )
        labels = list(variants)
        for trial in range(args.trials):
            if trial:
                for proc in processes.values():
                    proc.stdin.close()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                processes = {}
                for label in (
                    list(variants) if trial % 2 == 0 else list(reversed(variants))
                ):
                    extension = variants[label]
                    log = (
                        args.output / (str(trial) + "-" + label + "-stderr.log")
                    ).open("x")
                    logs.append(log)
                    command = [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--worker",
                        "--extension",
                        extension,
                        "--queries",
                        str(args.queries.resolve()),
                        "--matrix-repeats",
                        str(args.matrix_repeats),
                    ]
                    proc = subprocess.Popen(
                        command,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=log,
                        text=True,
                        bufsize=1,
                    )
                    processes[label] = proc
                    ready = receive(proc)
                    assert (
                        ready["binary_sha256"]
                        == report["variants"][label]["binary_sha256"]
                    )
                    report["trial_builds"].setdefault(str(trial), {})[label] = ready
            else:
                report["trial_builds"]["0"] = report["variants"]
            regions = REGIONS if trial % 2 == 0 else tuple(reversed(REGIONS))
            for region in regions:
                order = labels if trial % 4 in (0, 3) else list(reversed(labels))
                responses = {}
                for label in order:
                    state = host()
                    proc = processes[label]
                    proc.stdin.write(
                        json.dumps({"region": region, "trial": trial}) + "\n"
                    )
                    proc.stdin.flush()
                    response = receive(proc)
                    response["host_before"] = state
                    response["host_after"] = host()
                    response["variant"] = label
                    name = f"{trial}-{region}-{label}.json"
                    (args.output / name).write_text(json.dumps(response, indent=2))
                    report["jobs"].append(name)
                    responses[label] = response
                    if response["status"] != "PASS":
                        raise RuntimeError(f"Failed job: {name}")
                    print(trial, region, label, response["summary"], flush=True)
                for other in labels[1:]:
                    a, b = responses[labels[0]], responses[other]
                    assert len(a["samples"]) == len(b["samples"])
                    for x, y in zip(a["samples"], b["samples"]):
                        assert (
                            x["source"],
                            x["distance_sha256"],
                            x["path_sha256"],
                        ) == (y["source"], y["distance_sha256"], y["path_sha256"])
                        assert (
                            x["work"] == y["work"]
                        ), "Optimization changed deterministic BMSSP work"
                    for count in a["matrices"]:
                        assert [r["sha256"] for r in a["matrices"][count]] == [
                            r["sha256"] for r in b["matrices"][count]
                        ]
        report["status"] = "PASS"
    except Exception:
        report["status"] = "FAIL"
        report["failures"].append(traceback.format_exc())
        raise
    finally:
        for proc in processes.values():
            if proc.poll() is None:
                proc.stdin.close()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        for log in logs:
            log.close()
        (args.output / "manifest.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worker", action="store_true")
    p.add_argument("--reference", action="store_true")
    p.add_argument("--extension", type=Path)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--variant", action="append")
    p.add_argument("--trials", type=int, default=4)
    p.add_argument("--matrix-repeats", type=int, default=5)
    args = p.parse_args()
    if args.trials < 1 or args.matrix_repeats < 0:
        p.error("Invalid repetitions")
    if args.worker:
        worker(args)
    elif args.reference:
        if args.extension is None or args.output is None:
            p.error("--reference requires --extension and --output")
        reference_comparison(args)
    else:
        if not args.variant or args.output is None:
            p.error("--variant and --output are required")
        controller(args)
