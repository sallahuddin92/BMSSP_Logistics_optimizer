#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Supplemental all-source temporal pairing; distinct from primary process-batch A/B."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import sys
import time
from native_ab_benchmark import REGIONS, distribution, host, sha


def receive(process):
    if not select.select([process.stdout], [], [], 600)[0]:
        raise TimeoutError("paired worker response")
    line = process.stdout.readline()
    if not line:
        raise RuntimeError("paired worker exited")
    return json.loads(line)


def worker(args):
    sys.path.insert(0, str(args.extension.resolve()))
    import bmssp_native as native
    from road_fixture import load_fixture_snapshot

    records, engines = {}, {}
    for region in REGIONS:
        record = json.loads((args.queries / region / "results.json").read_text())
        snapshot = load_fixture_snapshot("osm-fixture:" + region)
        assert snapshot.snapshot_id == record["snapshot_id"]
        engine, _ = snapshot.engine("native_bmssp_2025")
        records[region], engines[region] = record, engine
    print(
        json.dumps(
            {
                "ready": True,
                "pid": os.getpid(),
                "binary_sha256": sha(Path(native.__file__)),
            }
        ),
        flush=True,
    )
    for line in sys.stdin:
        request = json.loads(line)
        region = request["region"]
        record, engine = records[region], engines[region]
        if request["kind"] == "warm":
            for source in record["query_sources"][:8]:
                engine.solve(source)
            print(json.dumps({"warm": True}), flush=True)
            continue
        index = request["index"]
        assert 0 <= index < len(record["query_sources"])
        source = record["query_sources"][index]
        began = time.perf_counter()
        result = engine.solve(source)
        elapsed = time.perf_counter() - began
        d = result.diagnostics
        assert all(x["calls"] == 0 for x in d["profile"].values())
        distances = result.distances
        row = {
            "source": source,
            "index": index,
            "seconds": elapsed,
            "native_seconds": d["query_seconds"],
            "distance_sha256": hashlib.sha256(
                struct.pack("<" + "d" * len(distances), *distances)
            ).hexdigest(),
            "path_sha256": hashlib.sha256(
                json.dumps(
                    [result.path(t) for t in record["oracle_sources"][:4]],
                    sort_keys=True,
                ).encode()
            ).hexdigest(),
            "work": {
                k: v
                for k, v in d.items()
                if k not in ("query_seconds", "preprocessing_seconds", "profile")
            },
        }
        print(json.dumps(row), flush=True)


def controller(args):
    args.output.mkdir(parents=True, exist_ok=False)
    variants = dict(v.split("=", 1) for v in args.variant)
    assert len(variants) == 2
    manifest = {
        "protocol": "all 100 sources with alternating AB/BA order per source; separate fresh processes per trial",
        "argv": sys.argv,
        "host_initial": host(),
        "jobs": [],
        "failures": [],
    }
    processes = {}
    logs = []
    try:
        for trial in range(args.trials):
            ready = {}
            order = list(variants) if trial % 2 == 0 else list(reversed(variants))
            for variant in order:
                log = (args.output / f"{trial}-{variant}.log").open("x")
                logs.append(log)
                command = [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--worker",
                    "--extension",
                    variants[variant],
                    "--queries",
                    str(args.queries),
                ]
                p = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=log,
                    text=True,
                    bufsize=1,
                )
                processes[variant] = p
                ready[variant] = receive(p)
            manifest.setdefault("processes", {})[str(trial)] = ready
            for region in REGIONS if trial % 2 == 0 else tuple(reversed(REGIONS)):
                record = json.loads(
                    (args.queries / region / "results.json").read_text()
                )
                assert len(record["query_sources"]) == 100
                result = {
                    "trial": trial,
                    "region": region,
                    "snapshot_id": record["snapshot_id"],
                    "samples": {v: [] for v in variants},
                    "host_before": host(),
                }
                for p in processes.values():
                    p.stdin.write(json.dumps({"region": region, "kind": "warm"}) + "\n")
                    p.stdin.flush()
                    assert receive(p)["warm"]
                for index in range(100):
                    labels = (
                        list(variants)
                        if (index + trial) % 2 == 0
                        else list(reversed(variants))
                    )
                    responses = []
                    for variant in labels:
                        p = processes[variant]
                        p.stdin.write(
                            json.dumps(
                                {"region": region, "kind": "solve", "index": index}
                            )
                            + "\n"
                        )
                        p.stdin.flush()
                        row = receive(p)
                        assert row["source"] == record["query_sources"][index]
                        result["samples"][variant].append(row)
                        responses.append(row)
                    for key in (
                        "source",
                        "index",
                        "distance_sha256",
                        "path_sha256",
                        "work",
                    ):
                        assert responses[0][key] == responses[1][key], key
                result["host_after"] = host()
                result["summaries"] = {
                    v: distribution([x["seconds"] for x in values])
                    for v, values in result["samples"].items()
                }
                path = args.output / f"{trial}-{region}.json"
                path.write_text(json.dumps(result, indent=2))
                manifest["jobs"].append(path.name)
            for p in processes.values():
                p.stdin.close()
                p.wait(timeout=30)
                assert p.returncode == 0
            processes = {}
        manifest["status"] = "PASS"
    except Exception as exc:
        manifest["status"] = "FAIL"
        manifest["failures"].append(repr(exc))
        raise
    finally:
        for p in processes.values():
            if p.poll() is None:
                p.stdin.close()
                try:
                    p.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
        for log in logs:
            log.close()
        (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worker", action="store_true")
    p.add_argument("--extension", type=Path)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--variant", action="append")
    p.add_argument("--trials", type=int, default=2)
    args = p.parse_args()
    if args.trials < 1:
        p.error("--trials must be positive")
    if args.worker and args.extension is None:
        p.error("--worker requires --extension")
    if not args.worker and (
        args.output is None or not args.variant or len(args.variant) != 2
    ):
        p.error("Provide --output and exactly two --variant NAME=PATH values")
    if args.worker:
        worker(args)
    else:
        controller(args)
