# Task 8: real Malaysian road acceptance

This workflow uses the existing native adapter, engines, API and logistics solver.
It does not change the default engine. Prepared OSM data is explicit local input;
the application never invokes the preparation command or downloads a replacement.

## Preparation and resource contract

Use a separate Python 3.11 environment with the pinned backend requirements,
`tools/requirements-road-data.txt`, and a Release native extension built using the
instructions in `docs/native_python.md`. The optional importer adds osmium 4.2.0;
it does not require a system osmium command or a nationwide node-location index.

From the repository root (set `PYTHON`, `NATIVE_BUILD`, `ROAD_FIXTURE_ROOT` to your
own absolute paths):

```sh
export GRAPH_CACHE_DIR=/private/tmp/bmssp-road-cache
export MPLCONFIGDIR=/private/tmp/bmssp-road-mpl
export ROAD_FIXTURE_ROOT=/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-road-data
export PYTHONPATH="$PWD/backend:$NATIVE_BUILD/python"
# Explicit benchmark operator limits; production defaults remain 10k/40k/200k.
export NATIVE_MAX_NODES=40000
export NATIVE_MAX_EDGES=100000
export NATIVE_SNAPSHOT_MAX_GEOMETRY_POINTS=600000
"$PYTHON" tools/prepare_road_data.py --output "$ROAD_FIXTURE_ROOT"
```

The importer checks disk space and source Content-Length before downloading. Its
source cap is 300 MiB, total dataset cap 1 GiB, and free-space reserve 5 GiB. It
checks both Geofabrik's MD5 sidecar and SHA-256. Interrupted downloads are retained
and must be inspected explicitly; they are never silently replaced. A verified
cached PBF is reused even if the moving `latest` URL changes. Keep this source and
its `source.json` to reproduce these exact bytes; a future latest download is a
new dataset. All prepared files live outside Git.

Three fixed rectangles, `(south, west, north, east)`, are declared in the importer:

| Workload | Rectangle |
|---|---|
| Seremban urban | 2.718, 101.925, 2.742, 101.953 |
| Seremban medium | 2.66, 101.86, 2.80, 102.01 |
| Seremban–Port Dickson | 2.47, 101.76, 2.80, 102.02 |

Three streaming PBF passes retain only rectangle node IDs, selected driving ways,
and coordinates for their references. Limits are one million selected node IDs
and 150,000 ways per workload. Complete ways with at least one OSM node inside the
rectangle are selected. A way crossing a rectangle with no interior node can be
absent. Ways extending beyond the rectangle remain complete. These are
**boundary-clipped workloads, not complete regional road coverage**. No area is
shrunk to meet a budget. The medium/corridor workloads exceed the default native
admission limits; the explicit benchmark limits above are required.

Filtering uses the recorded OSMnx 1.6.0 `drive` filter. XML retains OSM node/way IDs
and way tags. OSMnx constructs a directed MultiDiGraph, adds lengths before
simplification, and sums those lengths during simplification. `retain_all=True`
and `remove_rings=False` preserve components and isolated rings. Simplified
lengths are never replaced by endpoint chords. One-way tags and roundabouts are
handled by OSMnx; conditional access and relation-based turn restrictions are
unsupported. Travel times, traffic and speeds are not invented. Distance weights
remain OSMnx's rounded geodesic segment lengths in meters, not surveyed lengths.

Each manifest records source bytes/hash/headers/date, extraction UTC, OSMnx
version/filter, rectangle, graph SHA-256, canonical native snapshot ID, counts,
components and build timings. GraphML serialization can have timestamp metadata;
the canonical snapshot identity covers routing IDs, keys, weights, coordinates,
geometry and valid edge durations. Rebuilds validate routing content, rather than
assuming serialization bytes are identical.

## Selection and immutable reuse

Set `ROAD_FIXTURE_ROOT` in the server environment and explicitly submit
`place="osm-fixture:seremban-small"`, `osm-fixture:seremban-medium`, or
`osm-fixture:seremban-port-dickson`. The frontend provides the same native dataset
selector. Changing datasets clears all old stops and routes. Legacy routing
remains available with its existing current-graph behavior; prepared native VRP
fixtures require a native engine.

`road_fixture.py` verifies the manifest schema/source, allowed filename, file
size cap, graph SHA-256, original counts and canonical snapshot ID. It reads the
same verified bytes it parses. It never deserializes pickle or accepts an
historical cache merely because it has a marker. A maximum of three declared
fixture records is retained. These are operator-owned files: checksums detect
corruption/change; they are not a signature proving OSM origin against a
malicious local operator.

Native selection returns the privately retained `GraphSnapshot`, whose native
storage and captured road metadata are immutable. A legacy mutable NetworkX
object is separate. `SnapshotCache.get(GraphSnapshot)` checks current admission
and geometry limits and reuses that captured version. It never infers
immutability from a NetworkX object, `nx.freeze`, attributes, mtime or a caller
version string. All mutable graph lookups continue full canonical capture and
mutation checks. Old handed-out snapshots remain valid after file replacement;
the next selection checks file bytes and constructs the new version.

## Offline validation and profiling

```sh
export PYTHONPATH="$PWD/tools/offline_guard:$PWD/backend:$NATIVE_BUILD/python"
"$PYTHON" tools/road_acceptance.py --output /absolute/new-evidence-directory
"$PYTHON" -m pytest backend/tests backend/native_tests backend/logistics_tests backend/road_tests -p no:cacheprovider
node --test frontend/tests/*.test.cjs
```

The scoped offline guard rejects outbound INET sockets. It is not used for
preparation. The acceptance runner never downloads. Every selected oracle source
is compared at **all destinations** with native BMSSP, native Dijkstra and
NetworkX Dijkstra on the identical adapter input. Distances and directed
reachability must agree exactly as binary64 values: **no epsilon or rounding
normalization**. Original-edge path sums use left-to-right binary64 accumulation
and must equal the result exactly. This is empirical numerical validation, not a
proof that the paper's exact-real comparison-addition model holds for arbitrary
binary64 inputs. Geometry's existing 1e-7 degree endpoint tolerance applies only
to drawing continuity, never to routing distances.

The runner checks original directed edge keys and endpoints, path reconstruction,
geometry continuity, long spatial-extreme paths, reverse asymmetry, disconnected
components, parallel edges, OSM IDs beyond 32 bits, repeated sources and matrices.
Real API requests cover one/multiple vehicles, mandatory visits, capacities,
return to depot and directed infeasibility. No real duration data is present;
time-window requests must reject absent duration data. Synthetic duration unit
tests remain separate from road acceptance.

Raw JSON retains every query latency, source, diagnostic and API request/response.
Failure JSON and a traceback are written before nonzero exit; failed samples are
not removed. Seed defaults to 20261105. Empirical nearest-rank percentiles are
p50 always, p95 for >=20 samples and p99 for >=100 samples. One hundred samples
provide a coarse p99, not a stable production tail estimate. Cold capture (5),
cold degree reduction (10), warm capture/immutable reuse/file checking (20),
query/path/bulk extraction (100 each), and 1/4/8-source matrices (10 each) are
reported separately. Cold is fresh in-process construction, not OS page-cache
cold. Fixture load includes file verification, GraphML parsing and initial capture.
Process peak RSS is cumulative (macOS bytes), not per-component heap accounting.
Label creation counts measure arena node allocations; total malloc bytes are not
claimed. `.prof` files preserve Python capture call profiles.

`BMSSP2025Engine.solve(source, profile=True)` opts into per-thread exclusive and
inclusive timing/call counters for label allocation/comparison, FindPivots,
BaseCase, public frontier operations and recursive BMSSP. Exclusive categories
partition instrumented scope time; inclusive recursive times overlap. Scope clock
overhead is material, especially for comparisons. Instrumented timings diagnose
work distribution and **must not replace uninstrumented latency measurements**.
Default queries do not read these profiling clocks. Existing query diagnostics
also expose reduction expansion, labels, equality relaxations, recursive work and
frontier work. Matrix metadata separates native time, Python wall residual and
extraction; VRP metadata separates solving, path and geometry; the runner measures
JSON serialization. The residual is not a pure binding microbenchmark.

## Browser proof

Use Playwright 1.56.1, Leaflet 1.9.4 and local Chrome. Start the real API harness:

```sh
export PYTHONPATH="$PWD/tools/offline_guard:$PWD/backend:$PWD/tools:$NATIVE_BUILD/python"
"$PYTHON" -m uvicorn road_server:app --host 127.0.0.1 --port 8878
# In another shell with NODE_PATH pointing to the installed npm packages:
ROAD_RESULTS=/absolute/evidence/seremban-small/results.json \
BROWSER_EVIDENCE=/absolute/existing/browser-directory \
node frontend/tests/road_browser.cjs
```

The harness mounts the existing frontend and production API; it adds no fixture
mode or graph substitution endpoints. Real map clicks discover original nodes,
then submit a two-vehicle capacity-constrained solve. Browser checks snapshot,
source hash, native identity, loads and exact equality of displayed polylines to
API segments. JSON and screenshot evidence are retained. Leaflet is served from
the local pinned package; remote tiles/fonts are intentionally blocked. The
screenshot proves selected real-road geometry, not availability of a live basemap.

## Attribution and limitations

Source: [Geofabrik Malaysia/Singapore/Brunei](https://download.geofabrik.de/asia/malaysia-singapore-brunei.html).
Data © OpenStreetMap contributors, available under the
[Open Database License](https://www.openstreetmap.org/copyright).
Retain attribution and observe ODbL obligations when sharing source or derived
graph databases. No research implementation code was copied or vendored in this
task; dependency licenses continue to apply. The native research contract remains
in `docs/bmssp_2025.md`. No turn-restriction, traffic, theoretical speedup,
complete regional coverage or production scalability claim follows from these
workloads. Linux performance/real-browser acceptance must be measured separately.

For a paired integration comparison after implementing immutable reuse:

```sh
"$PYTHON" tools/road_snapshot_benchmark.py --output /absolute/new-paired-results.json
```

This alternates 30 before/after samples per graph. Both sides verify the same
file bytes on every lookup. The before side captures the mutable NetworkX graph;
the after side uses the private immutable snapshot. It asserts identical routing
snapshot IDs and includes file verification and admission checks in both times.
It measures the integration optimization, not a BMSSP algorithm speedup.

A separate uninstrumented native stack sample can be reproduced with
`tools/road_native_sample.py --region seremban-medium --seconds 15 --output NEW.json`
and `/usr/bin/sample PID 3 1 -file NEW-sample.txt` after the tool prints READY.
Keep sampling runs separate from latency distributions.
`tools/road_query_benchmark.py --queries REGION/results.json --output NEW.json`
replays the recorded source list against the extension selected by PYTHONPATH,
including an older build in a separate process. Sequential process comparisons
are not paired evidence of a native algorithm speedup.
