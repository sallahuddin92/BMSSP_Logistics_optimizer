#!/usr/bin/env python3
"""Paired before/after prepared-fixture selection on identical immutable data.

Before: verify file + retrieve mutable graph + full adapter validation.
After: verify file + retrieve private immutable snapshot + admission validation.
Alternates order; retains every sample. Does not benchmark SSSP or OS-cold I/O.
"""
import argparse
import json
from pathlib import Path
import resource
import time
import traceback
from native_graph import SnapshotCache
from road_fixture import REGIONS, load_fixture, load_fixture_snapshot
from road_acceptance import distribution

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--samples", type=int, default=30)
args = parser.parse_args()
if args.samples < 1:
    parser.error("samples must be positive")
if args.output.exists():
    parser.error("output already exists; refusing overwrite")
report = {"regions": {}, "failures": []}
try:
    for region in REGIONS:
        place = "osm-fixture:" + region
        cache = SnapshotCache()
        graph = load_fixture(place)
        immutable = load_fixture_snapshot(place)
        snapshot, _ = cache.get(graph)
        assert snapshot.snapshot_id == immutable.snapshot_id
        samples = {"before": [], "after": []}
        report["regions"][region] = dict(
            snapshot_id=snapshot.snapshot_id, samples=samples
        )
        for index in range(args.samples):
            for mode in ("before", "after") if index % 2 == 0 else ("after", "before"):
                start = time.perf_counter()
                source = (
                    load_fixture(place)
                    if mode == "before"
                    else load_fixture_snapshot(place)
                )
                result, metadata = cache.get(source)
                elapsed = time.perf_counter() - start
                assert result.snapshot_id == snapshot.snapshot_id
                samples[mode].append(elapsed)
        report["regions"][region] = dict(
            snapshot_id=snapshot.snapshot_id,
            samples=samples,
            summaries={key: distribution(values) for key, values in samples.items()},
        )
        print(region, report["regions"][region]["summaries"], flush=True)
    report["status"] = "PASS"
except Exception:
    report["status"] = "FAIL"
    report["failures"].append(traceback.format_exc())
    raise
finally:
    report["peak_process_rss_bytes"] = resource.getrusage(
        resource.RUSAGE_SELF
    ).ru_maxrss
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
