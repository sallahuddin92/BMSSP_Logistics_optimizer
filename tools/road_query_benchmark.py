#!/usr/bin/env python3
"""Replay recorded sources against a selected extension build (no profiling).

Use separate processes/PYTHONPATH for before and after builds. Same source list,
graph bytes and snapshot identity are required. Retain all samples and failures.
"""
import argparse
import json
from pathlib import Path
import time
import traceback
import bmssp_native
from native_graph import SnapshotCache
from road_fixture import load_fixture
from road_acceptance import distribution

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--queries", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    parser.error("output already exists")
record = json.loads(args.queries.read_text())
report = dict(
    region=record["region"],
    sources=record["query_sources"],
    compiler=bmssp_native.compiler,
    samples=[],
    failures=[],
)
try:
    graph = load_fixture("osm-fixture:" + record["region"])
    snapshot, _ = SnapshotCache().get(graph)
    assert snapshot.snapshot_id == record["snapshot_id"]
    report["snapshot_id"] = snapshot.snapshot_id
    engine, _ = snapshot.engine("native_bmssp_2025")
    engine.solve(record["query_sources"][0])
    for source in record["query_sources"]:
        started = time.perf_counter()
        try:
            result = engine.solve(source)
        except Exception:
            report["failed_sample"] = dict(
                source=source, seconds=time.perf_counter() - started
            )
            raise
        report["samples"].append(time.perf_counter() - started)
    report["summary"] = distribution(report["samples"])
    report["status"] = "PASS"
except Exception:
    report["status"] = "FAIL"
    report["failures"].append(traceback.format_exc())
    raise
finally:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
