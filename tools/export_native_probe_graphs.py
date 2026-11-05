#!/usr/bin/env python3
"""Export verified road snapshots for allocation-only C++ probes, outside Git."""
import argparse
import hashlib
import json
from pathlib import Path
from road_fixture import REGIONS, load_fixture_snapshot

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--queries", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--sources", type=int, default=10)
a = p.parse_args()
if a.sources < 1:
    p.error("sources must be positive")
a.output.mkdir(parents=True, exist_ok=False)
manifest = {}
for name in REGIONS:
    query_file = a.queries / name / "results.json"
    record = json.loads(query_file.read_text())
    snapshot = load_fixture_snapshot("osm-fixture:" + name)
    assert snapshot.snapshot_id == record["snapshot_id"]
    path = a.output / (name + ".txt")
    with path.open("x") as stream:
        stream.write(f"{len(snapshot.original_nodes)} {len(snapshot.original_edges)}\n")
        for node in sorted(snapshot.original_nodes):
            stream.write(f"{node}\n")
        for edge, (u, v, key) in snapshot.original_edges.items():
            stream.write(
                f"{edge} {u} {v} {snapshot.road_data.edges[edge].length:.17g}\n"
            )
    sources = record["query_sources"][: a.sources]
    (a.output / (name + "-sources.txt")).write_text("\n".join(map(str, sources)) + "\n")
    manifest[name] = {
        "snapshot_id": snapshot.snapshot_id,
        "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "queries_sha256": hashlib.sha256(query_file.read_bytes()).hexdigest(),
        "sources": sources,
        "weight_serialization": "17 significant decimal digits: binary64 round-trip, no quantization",
    }
(a.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
