#!/usr/bin/env python3
"""Uninstrumented real-road query loop for an external stack sampler.

Start this command, then `sample PID 3 1 -file native-sample.txt` on macOS.
Exclude this sampling run from latency benchmark distributions.
"""
import argparse
import json
import os
from pathlib import Path
import random
import resource
import time
import networkx as nx
from road_fixture import REGIONS, load_fixture, load_fixture_snapshot

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--region", choices=REGIONS, default="seremban-medium")
parser.add_argument("--seconds", type=float, default=15)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if not 1 <= args.seconds <= 120:
    parser.error("seconds must be between 1 and 120")
if args.output.exists():
    parser.error("output already exists")
place = "osm-fixture:" + args.region
graph = load_fixture(place)
snapshot = load_fixture_snapshot(place)
engine, _ = snapshot.engine("native_bmssp_2025")
rng = random.Random(20261105)
nodes = sorted(max(nx.strongly_connected_components(graph), key=len))
sources = [rng.choice(nodes) for _ in range(64)]
print("READY PID", os.getpid(), flush=True)
start = time.perf_counter()
queries = 0
while time.perf_counter() - start < args.seconds:
    result = engine.solve(sources[queries % len(sources)])
    assert result.algorithm == "native_bmssp_2025"
    queries += 1
args.output.write_text(
    json.dumps(
        dict(
            snapshot_id=snapshot.snapshot_id,
            sources=sources,
            queries=queries,
            wall_seconds=time.perf_counter() - start,
            peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        ),
        indent=2,
    )
)
