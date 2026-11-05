# Task 9 native performance workflow

Task 9 changes native allocation and validation bookkeeping only. It does not
repeat Task 8's immutable fixture-selection optimization, change the production
default, or replace recursive BMSSP with another solver.

## Immutable baseline and data

Start from commit `698c14951399aca25a2409c8d1e26532c9d26587`. Create a `git archive`
source snapshot outside the checkout, preserve its SHA-256 and build a separate
Release extension from it. Do not rebuild this baseline from modified sources.
The Task 9 evidence retains the source archive and baseline extension/static
library binaries, their SHA-256 hashes, CMake caches and compile commands.

Reuse the existing three GraphML fixtures, manifests and exact Task 8 source lists
(`after-compat/<region>/results.json`). Their canonical snapshot identities and
file checksums are in [road_dataset_inventory.json](road_dataset_inventory.json).
No new OSM data is needed. Attribution and clipping/turn/duration limitations in
[real_road_workflow.md](real_road_workflow.md) still apply.

Use the same Python 3.11 environment, CMake Release flags, Apple Clang 21 compiler,
arm64 architecture and SDK for both builds. Build outside the source tree:

```sh
cmake -S "$BASELINE_SOURCE" -B "$BASELINE_BUILD" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DBMSSP_PYTHON=ON -DPython_EXECUTABLE="$PYTHON" \
  -Dpybind11_DIR="$("$PYTHON" -m pybind11 --cmakedir)" \
  -DCMAKE_CXX_COMPILER=/Library/Developer/CommandLineTools/usr/bin/clang++
cmake --build "$BASELINE_BUILD" -j 4
cmake --preset release -B "$CANDIDATE_BUILD" \
  -DBMSSP_PYTHON=ON -DBMSSP_ALLOCATION_PROBE=ON \
  -DPython_EXECUTABLE="$PYTHON" \
  -Dpybind11_DIR="$("$PYTHON" -m pybind11 --cmakedir)" \
  -DCMAKE_CXX_COMPILER=/Library/Developer/CommandLineTools/usr/bin/clang++
cmake --build "$CANDIDATE_BUILD" -j 4
```

All baseline/candidate engine flags must match. Allocation interception is linked
only into optional probe and memory-test executables, never the production
library or binding. Debug/sanitizer/structural-probe timings are not query latency
measurements.

## Counterbalanced A/B

From the repository root, set absolute paths:

```sh
export GRAPH_CACHE_DIR=/private/tmp/bmssp-task9-cache
export MPLCONFIGDIR=/private/tmp/bmssp-task9-mpl
export ROAD_FIXTURE_ROOT=/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-road-data
export NATIVE_MAX_NODES=40000 NATIVE_MAX_EDGES=100000
export NATIVE_SNAPSHOT_MAX_GEOMETRY_POINTS=600000
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/tools/offline_guard:$PWD/backend"
"$PYTHON" tools/native_ab_benchmark.py \
  --queries "$TASK8_EVIDENCE/after-compat" \
  --variant "baseline=$BASELINE_BUILD/python" \
  --variant "optimized=$CANDIDATE_BUILD/python" \
  --trials 4 --matrix-repeats 5 --output "$NEW_AB_DIRECTORY"
```

The final experiment launches fresh baseline/candidate processes for each trial;
load/preparation order reverses on odd trials. Both processes prepare exactly the
same verified snapshots and run the same eight untimed warmups before each job.
Variant job order is AB, BA, BA, AB; graph order reverses on odd trials. Every job
replays all 100 recorded source IDs, without profiling. Hashes of every full
binary64 distance vector and selected original paths must agree, as must all
deterministic BMSSP work counters. Five matrix samples at each of 1/4/8 distinct
sources per job must also agree bit-for-bit. No source, slow sample or failure is
removed. Source lists include small/disconnected components, not just large SCCs.

Each job persists all latencies, diagnostics, fingerprints, warmups, current and
peak process RSS, before/after load averages, vm_stat and pmset thermal output.
Build metadata records binary hashes, compiler, preprocessing times, snapshots,
GraphML checksums and source-list file hashes. Kernel source hashes and stage
source copies accompany the execution evidence. The CLI refuses an existing
output directory. Exceptions preserve completed jobs and a failing manifest.

Query wall time includes binding result creation and workspace/label-arena
teardown. The existing internal query timer stops before all teardown; its
residual is not a pure binding benchmark. Matrix timing includes matrix extraction
on both sides. Startup/preprocessing is recorded separately, not subtracted from
only one variant. Native extension loading requires distinct processes; no
in-process module replacement is used.

Summaries use nearest-rank p50/p95/p99. Report per-trial percentiles and paired
median speed changes, in addition to pooled 400 samples/variant/graph. These are
four repeats of the same fixed 100-query distribution, not 400 independent road
queries. Host frequency and scheduling are not pinned; report observed variance
and source-specific regressions rather than attributing every difference to code.

## Allocation and structural diagnosis

```sh
export PYTHONPATH="$PWD/tools/offline_guard:$PWD/backend:$CANDIDATE_BUILD/python"
"$PYTHON" tools/export_native_probe_graphs.py \
  --queries "$TASK8_EVIDENCE/after-compat" --output "$NEW_PROBE_INPUTS"
"$CANDIDATE_BUILD/allocation_probe" \
  "$NEW_PROBE_INPUTS/seremban-medium.txt" \
  "$NEW_PROBE_INPUTS/seremban-medium-sources.txt"
```

The export preserves original node IDs, deterministic edge IDs and binary64
weights via 17-digit round-trip serialization; it never quantizes weights. Both
probes must use the same exported files/hashes and 10 recorded sources. Link the
same current probe driver against the immutable baseline static library in a
separate CMake project for a matched comparison. CMake supplies the SDK settings;
a bare CLT compiler invocation without its SDK failed during setup and is retained.

The isolated replacement operators count successful ordinary **and aligned** C++
new/new[] calls, requested bytes, delete calls and size histograms during a query.
They include query workspace and returned-result destruction, but exclude the
reference Dijkstra check, graph/reduction construction, C malloc, allocator
metadata/padding, OS allocations and failed requests. Bins have power-of-two upper
bounds; the final bin saturates. These are cumulative allocation bytes, not live
heap bytes. Unix getrusage peak RSS covers the whole probe process (bytes on
macOS, platform units in the raw record). Allocation counts and RSS are not
latency measurements. Balanced counted new/delete calls are not a leak detector.

For separate baseline structural instrumentation:

```sh
"$PYTHON" tools/native_structural_probe.py \
  --source "$BASELINE_SOURCE" \
  --library "$BASELINE_BUILD/libbmssp_foundation.a" \
  --compiler /Library/Developer/CommandLineTools/usr/bin/clang++ \
  --output "$NEW_STRUCTURAL_BUILD"
"$NEW_STRUCTURAL_BUILD/build/structural_probe" \
  "$NEW_PROBE_INPUTS/seremban-medium.txt" \
  "$NEW_PROBE_INPUTS/seremban-medium-sources.txt"
```

The generator checks native source/header Git blob hashes against 698c1495 before
creating instrumented objects, preserving the pristine archive and library. It
counts comparison calls, identical snapshots, scalar/hop ties, vertex/edge chain
steps and maximum chain walk. Pointer-identical comparisons are counted
separately from scalar ties. It also measures frontier-validity calls and their
allocation subset using scoped probes. Its scope clocks/counter overhead makes
those timings instrumented diagnostics only. Production compare() is unchanged.

## Ownership and invariant arguments

- Label nodes live in separately owned arrays. Growth moves unique_ptr handles,
  never published nodes; the vector's iterator invalidation therefore cannot
  invalidate node/parent references. Blocks grow 32, 64, ... to 4096-node chunks.
  The mutex still protects allocation, cursor publication and handle growth.
  Array creation or handle-vector allocation failure leaves the previous cursor
  and published nodes intact. Nothrow node assignment completes initialization
  before publication. Arena ownership and iterative destruction remain unchanged.
  See the standard [array ownership](https://eel.is/c++draft/unique.ptr.create)
  and [vector growth guarantees](https://eel.is/c++draft/vector.modifiers).
- Each frontier owns an unsynchronized pool with explicit thread-safe
  new_delete_resource upstream. Its list entries, list blocks, fence map,
  key-location map and batch index nodes share that local pool. No pool is shared
  across concurrent queries or recursion frames. Resource declaration/destruction
  order keeps it alive until every using container is destroyed. Existing list
  handles, key order, balanced fences, partial ordering, selection and Delete
  remain unchanged. Pool chunks may retain more capacity until frontier
  destruction. [Standard pool semantics](https://eel.is/c++draft/mem.res.pool.overview)
  explain that tradeoff.
- Validation marks are private workspace scratch indexed by immutable dense
  vertex indices. A validity check completes before recursion or any observer
  executes; no caller reads its marks afterward. Thus only this scratch can be
  reused across recursion. Live completed sets and pivot forests remain separate.
  uint32 epochs avoid per-call clearing; explicit wrap clearing is tested using
  uint8 epochs. The extra array costs four bytes per transformed vertex per query
  and can impose fixed overhead on small reachable components.
- Equality-valid relaxations, parameters, recursive bounds, progress/coverage
  checks, symbolic ordering, pivot/base algorithms, path projection and all public
  engine selection behavior are preserved. No asymptotic improvement is claimed.

## Strict gates

Run Debug/Release CTest, ASan/UBSan, supported TSan, the existing Python/native/API/
logistics and frontend suites, and `tools/road_acceptance.py` on all three graphs.
This rechecks 960,816 real-road distances and 643,571 original-edge paths. The
full road gate may run alongside correctness builds; its incidental timings must
not be used as the controlled A/B result. No trace/oracle test is weakened.

New memory tests cover root/growth/query allocation failures, stable saved
parents, shared-arena concurrent growth and deterministic ties, repeated large
arena destruction, frontier reinitialization after allocation failure and epoch
wrap. ASan/UBSan is not a race detector. TSan findings apply to executed tests,
not a proof of race freedom. macOS leak detection is unsupported/disabled; no
leak-check claim is made. RSS/cache retention and counted allocation balance are
reported separately.

A separate current comparison against native Dijkstra uses the same candidate
extension and recorded queries, eight equal warmups and alternating per-query
engine order:

```sh
"$PYTHON" tools/native_ab_benchmark.py --reference \
  --extension "$CANDIDATE_BUILD/python" \
  --queries "$TASK8_EVIDENCE/after-compat" --output "$NEW_REFERENCE_DIRECTORY"
```

Every complete distance vector must match exactly. This measures the remaining
Dijkstra gap; it is separate from the four-trial optimization A/B evidence.
