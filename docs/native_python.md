# Native Python routing integration (Task 6)

The explicit modes are `native_bmssp_2025`, `native_reference_dijkstra`, and
`legacy_networkx`. `/distance-matrix` still defaults to legacy compatibility.
No benchmark-based selection or native failure fallback exists. The old extension,
VRP path, frontend and deployment workflows are preserved.

## Build and import

C++20, CMake >=3.20 (>=3.21 for presets), Python >=3.9 with development headers, and
pybind11 >=2.11 are required. The existing requirements pin pybind11 2.11.1.
The following uses an external virtualenv/build directory on macOS arm64 or Linux;
choose a Python with compatible wheels for the existing application dependencies:

```sh
python3.11 -m venv ../bmssp-python-venv
. ../bmssp-python-venv/bin/activate
python -m pip install pybind11==2.11.1
python native/python/build.py --build-dir ../bmssp-python-build --config Release
export PYTHONPATH="$(cd ../bmssp-python-build/python && pwd):$(pwd)/backend"
python native/python/import_smoke.py
```

The helper requires a virtualenv, discovers pybind11 through that interpreter,
rejects source-tree builds, compiles all native targets and runs the import smoke.
Use `--compiler /path/to/clang++` when necessary. On this macOS host the tested
compiler is `/Library/Developer/CommandLineTools/usr/bin/clang++` (Apple Clang 21).
Linux uses the same CMake method but **has not been executed in this task**.
There is no hardcoded interpreter path, global install, or network fetch in CMake.
Native-only builds retain `BMSSP_PYTHON=OFF` and no Python dependency.

Equivalent configuration flags are `-DBMSSP_PYTHON=ON`,
`-DPython_EXECUTABLE=<venv interpreter>`, and
`-Dpybind11_DIR=<python -m pybind11 --cmakedir>`. The output is under the external
build's `python/` directory. Native Debug/Release/sanitizer presets remain available.
For the full Python backend, install the unchanged `backend/requirements.txt` in
an isolated environment; validation additionally constrained the unpinned pandas
transitive dependency to `<3` and retained a complete environment freeze.

## Ownership and binding contract

`bmssp_native.NativeGraph(vertices, edges)` accepts integer vertex IDs and
`(uint64_edge_id, int64_from, int64_to, binary64_weight)` records. Integer scalars
must fit their exact 64-bit type; booleans/floating IDs and string/bool weights
are rejected. Native validation rejects negative/nonfinite weights, duplicate IDs
and unknown endpoints. Valid zero weights and parallel edge identities survive.
The module name is distinct from the legacy extension.

`BMSSP2025Engine(graph)` prepares degree reduction once. `solve(source)` returns a
`DistanceResult` containing algorithm identity, source, distance/reachability
vectors, `distance(target)`, `distances_to(targets)`, `path(target)` and diagnostics.
`NativeReferenceDijkstra(graph).solve(source)` is a separate explicit solver.
Graph copies share immutable C++ storage; engines and results own graph references.
No Python keep-alive chain or borrowed graph buffer is required. A result remains
usable after Python deletes the graph and engine. Distance/path containers are
copies; diagnostic dictionaries are query-local and do not expose graph/workspace
storage. `belongs_to(graph)` checks exact native storage identity.

Python conversion, object access and diagnostics wrapping hold the GIL. Pure C++
graph construction, BMSSP preprocessing/queries, Dijkstra, target extraction and
path reconstruction release it. Solver calls expose no Python callbacks. Each
query has its own labels/workspace; immutable engines support concurrent queries.
Standard native invalid-argument/out-of-range/overflow/runtime exceptions become
Python ValueError/IndexError/OverflowError/RuntimeError. Binding type/range
violations use TypeError. Native failures never invoke another algorithm.
See the [pybind11 GIL documentation](https://pybind11.readthedocs.io/en/stable/advanced/misc.html#global-interpreter-lock-gil)
and [CMake integration](https://pybind11.readthedocs.io/en/stable/cmake/index.html).

## Graph snapshots and freshness

`SnapshotCache.get(graph)` validates a directed NetworkX DiGraph/MultiDiGraph,
preserves every vertex and every original edge, and returns a `GraphSnapshot` plus
per-lookup timings. IDs normalize only from integral scalars or ASCII decimal
strings; collisions and signed-64-bit overflow are rejected. Floats and boolean
node IDs are unsupported. OSM multi-edge keys may be integer or string. Global
native edge IDs are assigned deterministically after sorting normalized endpoints
and typed keys, retaining a read-only mapping to original `(u,v,key)` identities.
Edge keys alone are not treated as globally unique. Simple edges map to key None.

Only numeric, finite, nonnegative `length` weights in meters are accepted. No
reverse arcs, edges, weights or vertices are synthesized by the adapter. Zero
weights remain zero. `original_path(result,target)` uses the native original-edge
IDs and checks that the result belongs to this snapshot before mapping identities.

Every cache lookup scans, validates, canonicalizes and hashes current routing
content, even on a warm hit. `adapter_conversion_time` includes this Python
capture/canonicalization work on both cold and warm lookups;
`snapshot_validation_time` reports the same initial capture interval. These
overlapping timings must not be added together. Keys include weak source identity, content digest,
weight configuration and structural limits. Changes to nodes, arcs, keys or weights
create a new immutable native graph; previous source versions are retired from
the bounded LRU. The snapshot lazily retains one prepared instance per selected
native engine under a lock. Old snapshots held by callers remain intentionally
valid representations of their captured graph. Task 7 also captures road coordinates, geometry and travel times; changes to
these values invalidate snapshots used by the logistics transaction.

Graph owners must serialize mutation during capture. NetworkX supplies no atomic
snapshot contract for arbitrary concurrent writers. Capture iteration errors and
changes observed across native construction are rejected; this is not a promise
to detect every mutate-and-revert race. Concurrent queries on an already captured
snapshot are supported. Warm lookup still has O(n+m) validation plus sorting and
hashing/allocation costs, measured separately from native queries.

## Road data and strict loading

OSMnx's simplified edges already contain sums of original segment lengths. The
loader now validates these lengths and never calls `add_edge_lengths` after
simplification. A curved 725.25-meter test road retains its full cost rather than
being shortened to its roughly 111-meter endpoint chord.

`load_native_graph(place)` accepts only an already loaded/local cached OSM graph
marked `osmnx_preserved_v1`, origin `osm`, units `meters`, with valid lengths.
It never downloads data, estimates a missing length, or creates a test graph.
Historical caches lack this marker and may contain the old overwritten lengths;
there is no safe automatic repair from their current numbers. They remain usable
through legacy mode, and require an explicit reload through the corrected loader
before native routing. The marker records loader provenance, not an independent
audit of OSM survey accuracy, access restrictions or road completeness. Cache
pickle files must be trusted local application data.

No validated local real-road dataset was available in this checkout. All Task 6
measurements and acceptance tests use declared deterministic offline fixtures.
Native routing is therefore opt-in; unrestricted production default promotion is
not authorized by this evidence.

## Matrix and API contract

```python
from native_graph import snapshot_cache
from routing_adapter import compute_native_matrix
snapshot, capture = snapshot_cache.get(directed_graph)
matrix, metadata = compute_native_matrix(snapshot, [source, target, target],
                                         engine="native_bmssp_2025")
```

Exactly one full SSSP is performed per distinct submitted node, retaining submitted
row/column order and duplicates. Every destination is extracted from that source
result. Prepared degree reduction is reused across cells, sources and subsequent
matrix calls. Duplicate identical nodes return zero; missing directed paths remain
positive infinity internally and JSON null externally, with explicit reachability.
No Haversine, symmetric replacement, synthetic routing graph or finite sentinel
enters the native path. `exact_routing=true` means no road-cost approximation or
reachability substitution; it does not change the engine's binary64 arithmetic
limitations documented in [bmssp_2025.md](bmssp_2025.md).

The existing list-of-strings body remains unchanged. Select native mode explicitly:

```text
POST /distance-matrix?engine=native_bmssp_2025&place=Kuala%20Lumpur%2C%20Malaysia
["5000000000", "5000000001", "5000000001"]
```

Existing locations/matrix/status/computation_time/metadata fields remain. Metadata
adds selected_engine, algorithm_version, graph_snapshot, weight_units,
exact_routing, unreachable_pair_count, reachability, native_execution_diagnostics,
preprocessing_time, degree_reduction_time, query_time, snapshot/construction and
matrix-extraction timings. The source diagnostics include implementation names,
recursion, BaseCase/pivot/frontier activity and query durations. An unreachable
native response is `PARTIAL_OR_UNREACHABLE` with null cells and false reachability.
Legacy metadata identifies legacy_networkx and approximation provenance; its
compatibility behavior is not certified exact.

Unknown selection returns 422, malformed IDs/weights/locations 400, resource
budgets 413, missing binary/data or busy admission 503, and native execution errors
500 with selected-engine context. Failed requests never return a completed route
or switch engines. Graph loading, capture, preprocessing and query work all run in
a worker using Starlette's threadpool; native admission is process-bounded and
rejects overload instead of starting extra preprocessing. See
[FastAPI concurrency](https://fastapi.tiangolo.com/async/).

| Environment budget | Default | Meaning |
|---|---:|---|
| NATIVE_MAX_NODES | 10000 | Nodes per snapshot/request |
| NATIVE_MAX_EDGES | 40000 | Original edges per snapshot/request |
| NATIVE_MAX_LOCATIONS | 128 | Submitted matrix rows/columns |
| NATIVE_MAX_SOURCES | 32 | Distinct full SSSP queries per matrix |
| NATIVE_SNAPSHOT_CACHE_ENTRIES | 2 | Retained LRU snapshots per process |
| NATIVE_MAX_CONCURRENT_REQUESTS | 2 | Admitted native API workers per process |

All overrides require positive integer values. Set process-wide cache/admission
settings before API import/startup. Graph/location/source settings are read per
request. Nothing is silently truncated. Per-process limits multiply with server
worker count. These are structural/workload admission limits, not hard allocator
or wall-clock cancellation guarantees; low-level binding users manage their own
budgets. Existing native path-label allocation costs remain relevant.

At Task 6, VRP/frontend migration remained deferred. Task 7 adds explicit native
VRP, checked constraints and selected-road geometry; see
[exact_logistics.md](exact_logistics.md). Legacy mode remains non-certified and
real-road production acceptance remains separate.

## Verification

See [Task 6 executable evidence](native_python_validation.md) for commands, timings,
oracles, sanitizer launch details and bounded cold/warm measurements. Preserve
[Task 5 measurements](bmssp_validation.md): BMSSP was slower than native Dijkstra
on its small fixtures; this integration makes no automatic fastest-engine claim.
