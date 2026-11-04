# Task 6 executable verification

Task date: 2026-11-04 (Asia/Kuala_Lumpur). Expected baseline verified clean at
`b2c6e95108f668dc76fbdbbdd72998498e1c50b4`, branch `codex/genuine-bmssp-engine`,
origin `https://github.com/sallahuddin92/BMSSP_Logistics_optimizer.git`.
Task 5 core sources and their original tests are unchanged. Integration contracts,
API examples, graph provenance restrictions and budgets are in
[native_python.md](native_python.md).

## Environment and retained evidence

macOS 26.5.1 (25F80), Apple M4 arm64, 10 logical CPUs, 16 GiB RAM.
Apple Clang 21.0.0 (clang-2100.1.1.101), CMake 4.3.3, Python 3.11.15,
pybind11 2.11.1. All C++ targets compile as C++20 with existing warnings-as-errors.
An isolated virtualenv was recreated because earlier Task 3/5 temporary
environments no longer existed. All direct requirements are unchanged; the
unpinned pandas transitive dependency was constrained to <3 (resolved 2.3.3).
No global installation, existing environment upgrade or road-data download occurred.
Linux build instructions are provided but Linux execution is unverified.

External build/venv/run workspace: `/private/tmp/bmssp-task6.ZTijar`.
Persistent evidence copy: `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task6-evidence`.
The latter contains the command manifest (argv, cwd, exit code, wall seconds),
logs including intermediate failures, JUnit XML, environment freeze/overrides,
compile commands, source/binary hashes, actual API response, and complete benchmark
JSON with all component p50/p95 values. Binaries/generated build files stay outside
Git. Temporary build paths may eventually disappear; the persistent evidence
preserves commands and measurements, and the documented build helper reproduces
fresh binaries. No external implementation source was reused.

## Commands and test gates

Commands below run from the checkout unless a working directory is stated.
The retained command JSON files record the expanded exact paths/arguments.

```sh
export BMSSP_BUILD=/private/tmp/bmssp-task6.ZTijar
export BMSSP_PYTHON="$BMSSP_BUILD/venv/bin/python"
# Environment initialization (executed):
/opt/homebrew/bin/python3.11 -m venv "$BMSSP_BUILD/venv"
/Users/sallahuddin/.local/bin/uv pip install --python "$BMSSP_PYTHON" -r backend/requirements.txt 'pandas<3'
# Repeated with debug, release and sanitizers:
cmake --preset release -B "$BMSSP_BUILD/release" -DBMSSP_PYTHON=ON -DPython_EXECUTABLE="$BMSSP_PYTHON" -Dpybind11_DIR="$("$BMSSP_PYTHON" -m pybind11 --cmakedir)" -DCMAKE_CXX_COMPILER=/Library/Developer/CommandLineTools/usr/bin/clang++
cmake --build "$BMSSP_BUILD/release" --parallel 4
ctest --test-dir "$BMSSP_BUILD/release" -V
# Native sanitizer CTest uses:
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --test-dir "$BMSSP_BUILD/sanitizers" -V
# Executed portable helper, including build/import smoke:
"$BMSSP_PYTHON" native/python/build.py --build-dir "$BMSSP_BUILD/release" --config Release --compiler /Library/Developer/CommandLineTools/usr/bin/clang++
```

For Python tests, cwd is `backend`, with these environment overrides:

```sh
export PYTHONDONTWRITEBYTECODE=1
export GRAPH_CACHE_DIR=/private/tmp/bmssp-task6.ZTijar/cache
export MPLCONFIGDIR=/private/tmp/bmssp-task6.ZTijar/mpl
export PYTHONPATH=/private/tmp/bmssp-task6.ZTijar/guard:/private/tmp/bmssp-task6.ZTijar/release/python:/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer/backend
/private/tmp/bmssp-task6.ZTijar/venv/bin/python -m pytest native_tests -vv --tb=long -p no:cacheprovider --junitxml=/private/tmp/bmssp-task6.ZTijar/delivery-integration.xml
```

The existing 34 tests run with the extension directory deliberately omitted from
PYTHONPATH, using `-m pytest tests -vv --tb=long -p no:cacheprovider` and an external
JUnit output. Thus legacy operation does not depend on a native binary being
installed. The external `guard/sitecustomize.py` rejects outbound IPv4/IPv6 socket
connections; Unix-domain TestClient communication remains available.

For the sanitized Python extension, replace release/python with sanitizers/python
in PYTHONPATH, then execute from backend:

```sh
/private/tmp/bmssp-task6.ZTijar/venv/bin/python ../native/python/run_sanitized_macos.py --compiler /Library/Developer/CommandLineTools/usr/bin/clang++ -- -m pytest native_tests -vv --tb=long -p no:cacheprovider --junitxml=/private/tmp/bmssp-task6.ZTijar/delivery-sanitizer-integration.xml
```

The versioned helper starts the actual framework interpreter with the matching
Clang ASan runtime preloaded and retains the virtualenv prefix. Two initial attempts
through Homebrew's bin launcher failed before module use (`Interceptors are not
working` / runtime loaded too late). The framework method resolves this; all
binding/adapter/API cases pass with ASan/UBSan instrumentation in the native module.
Leak detection is disabled because the Apple runtime does not support it. No
leak-check claim is made. The native-only sanitizer suite does not require Python
runtime preloading; the Python suite is a separate explicit gate.

| Gate | Outcome | Command wall seconds |
|---|---|---:|
| Debug CTest | 13/13, exit 0 | 25.591841 |
| Release CTest | 13/13, exit 0 | 10.417321 |
| Native ASan/UBSan CTest | 12/12, exit 0 | 46.714767 |
| Final Python integration | 49 passed, exit 0 | 2.734923 |
| Python ASan/UBSan integration | 49 passed, exit 0 | 4.959159 |
| Existing backend, no native binary on path | 34 passed, exit 0 | 133.208918 |

Debug/Release CTest contain the 79 unchanged native named cases, two CLI checks and
one binding import smoke. All native core cases passed. After final binding input
hardening, each configuration rebuilt successfully; Debug import smoke and both
Release/sanitized Python integration suites passed. Native-core tests need no
algorithm-change rerun because no native core source changed. Complete native
builds initially took Debug 5.880693 s, Release 5.592172 s, sanitizer 6.874540 s;
final binding-only builds took 1.925783 / 2.595980 / 2.427008 s respectively.
Some independent builds/tests overlapped, so suite timings are not controlled
performance comparisons.

During input hardening, pybind11 2.11 rejected constructing a tuple directly from a
borrowed handle. The explicit borrowed-object conversion fixed the compile error;
all three final warning-clean builds succeeded. Failure logs are retained. No
correctness assertion, existing test expectation, or timeout was weakened. Python
runs report 16 existing dependency/API deprecation warnings, zero skipped tests,
zero xfails and zero remaining failures.

## Actual execution and four-way agreement

The API proof uses the real extension binary and a declared offline directed
MultiDiGraph fixture. NetworkX path methods, the legacy fallback and the native
Dijkstra constructor are disabled by tests. Requests must still succeed and
identify BMSSP2025Engine::solve, with recursive/frontier/BaseCase work. The retained
`execution-proof.json` includes the binary path/hash and actual HTTP response.
Four distinct source queries produced 26 recursive calls, 22 frontier pulls,
16 BaseCase calls, 10 pivot calls, 12 pivot edge scans, and 77 relaxations.
One prepared degree reduction served all sources. Repeated requests use the same
snapshot and report zero new degree reductions/preprocessing.

| Corpus | Graphs | Sources / submitted destinations | Comparators | Outcome |
|---|---:|---|---|---|
| Quarter-unit random MultiDiGraphs | 9 | 8 distinct / 10 including duplicates | BMSSP, native Dijkstra, NetworkX Dijkstra, independent Floyd-Warshall | Exact distance/reachability agreement |
| One-way/parallel/zero/isolate fixture | 1 | 4 distinct / 5 including duplicates | Native modes, known distances and path checks | Reverse/disconnected entries remain unreachable |
| Curved road | 1 | 2 / 2 | Preserved original length and native matrix | 725.25 meters retained; reverse unreachable |
| Decimal binary64 fixture | 1 | 4 / 4 | BMSSP/native Dijkstra and reconstructed cost | Exact machine-distance agreement |

Random seeds are 2025, 17033 and 45141, n=8, densities 0/.15/.9 including possible
self-loops, quarter-unit weights, parallel edges and large OSM-style IDs. Random
matrices compare all submitted entries exactly, with no tolerance. Every reachable
path in that corpus is reconstructed through original edge mappings and checked
for directed endpoints, no predecessor cycle, and exact sum. Failures report the
seed, density and graph edges. The independent oracle uses its own Floyd-Warshall
loops; it does not call NetworkX shortest-path functions or native labels.

Other cases cover int64 endpoints and uint64 maximum edge ID, malformed/overflow
IDs, numeric-weight rejection, missing endpoints, missing imports, explicit native
execution failure, graph mutation invalidation, immutable old snapshots, deterministic
parallel-key mappings, LRU eviction, snapshot/engine lifetime, concurrent independent
queries, concurrent single preprocessing, request budgets/admission and event-loop
progress during worker preprocessing. The binding is verified as a compiled
extension using its platform extension suffix.

## Bounded performance observations

Executed from the checkout, with the same offline/cache/MPL environment and the
Release extension on PYTHONPATH:

```sh
/usr/bin/time -l /private/tmp/bmssp-task6.ZTijar/venv/bin/python benchmarks/native_integration/run.py --samples 30
```

Seed 2025, identical original graph/query sets for both native engines. Graphs are
64-node/63-edge chain and hub, and 48-node/170-edge sparse directed multigraph;
loop-inclusive densities 63/4096, 63/4096 and 170/2304. Locations are the large-ID
vertices at offsets 0, n/4, n/2, n-1, 0: four SSSP sources, five matrix columns,
and a duplicate row/column. Thirty samples per family/engine/state, 12 groups.
Cold resets both snapshot caches and includes new native graph/engine preparation.
Warm retains snapshots and prepared engines after one warmup. No import/startup
cost is included in API sample latency. Each measured matrix and API response is
checked against NetworkX on the same graph. No large OSM dataset is involved.

API time uses in-process FastAPI TestClient including worker dispatch, capture,
query/extraction, JSON conversion and response; it is not deployed network latency.
P95 uses nearest rank (29th of 30). These small samples characterize the fixture
run, not production tail latency or a universal speed comparison. Component query
time sums the four complete SSSP diagnostics, not a per-cell average.

API latency in milliseconds (p50 / p95):

| Fixture | Engine | Cold | Warm |
|---|---|---:|---:|
| chain | native_bmssp_2025 | 1.282875 / 1.955792 | 1.073938 / 1.098167 |
| chain | native_reference_dijkstra | 0.833188 / 0.913583 | 0.654458 / 0.682084 |
| hub | native_bmssp_2025 | 1.206730 / 1.433583 | 1.041666 / 1.216291 |
| hub | native_reference_dijkstra | 0.839146 / 0.946417 | 0.659542 / 0.867500 |
| sparse | native_bmssp_2025 | 2.921834 / 3.155625 | 2.525709 / 2.960792 |
| sparse | native_reference_dijkstra | 1.170751 / 1.278583 | 0.827708 / 0.867500 |

Cold BMSSP component medians in milliseconds (independently timed intervals;
medians are not additive):

| Fixture | Adapter capture/conversion | Native graph | Degree reduction | Four BMSSP queries | Binding roundtrip | Matrix extraction |
|---|---:|---:|---:|---:|---:|---:|
| chain | 0.176958 | 0.008270 | 0.011375 | 0.270230 | 0.000206 | 0.005333 |
| hub | 0.173959 | 0.008500 | 0.009687 | 0.225020 | 0.000210 | 0.005125 |
| sparse | 0.348396 | 0.012979 | 0.028417 | 1.455187 | 0.000213 | 0.005854 |

Warm matrix component query medians (BMSSP / native Dijkstra, milliseconds):
- chain: 0.273520 / 0.008271.
- hub: 0.229854 / 0.009479.
- sparse: 1.437166 / 0.004750.

Warm native graph construction and degree reduction are zero; Python freshness
capture/conversion still runs and is measured. The full JSON retains p50/p95 for
all ten components. Binding roundtrip is the mean of 100 trivial vector-transfer
calls per sample, including the Python loop/assert and transfer overhead, not a
pure C ABI cost. Query wall residual separately subtracts the internal C++ query
timer from Python solve wall time: it also includes native cleanup/wrapping and
clock noise, so it must not be described as isolated binding overhead.

macOS time reported peak process RSS **187,777,024 bytes** and peak footprint
154,010,320 bytes. Python resource sampled RSS **187,596,800 bytes** just before
exit; the small difference reflects measurement instants. These cover the complete
Python/geospatial/API benchmark process, not per-query allocator usage. Measured
command wall duration is retained in delivery_performance.json.
BMSSP remains slower than native Dijkstra on these fixtures. Task 5 measurements
are preserved unchanged; no speedup, asymptotic transfer, engine substitution or
unrestricted default promotion follows from these observations.

## Acceptance scope and remaining risks

The implemented binding, conversion, directed matrix and API gates pass on macOS.
The legacy path works without a native import; frontend/VRP execution paths and
all existing tests remain available. The graph loader's graph/place pair is
published/read atomically under a lock. Mutation of graph content during snapshot
capture still requires owner serialization; immutable snapshot queries themselves
are concurrent. Historical road-length caches require explicit reload, trusted
local pickle provenance matters, and no real-road/production-scale or Linux
acceptance claim is made. Structural budgets do not impose hard heap/time limits.
Task 5's binary64 and theoretical-complexity limits remain unchanged. The legacy
VRP path is not certified for exact directed-road feasibility. Task 7 is not started.
