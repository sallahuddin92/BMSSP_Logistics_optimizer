# Task 7 validation — verified offline logistics integration

Status: PASS, scoped to deterministic offline integration. Date: 2026-11-05,
Asia/Kuala_Lumpur. Workspace `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer`,
branch `codex/genuine-bmssp-engine`, expected clean baseline
`2b41eae3465ea941df4c9de63b70304b292a1693`. Origin was verified as
`https://github.com/sallahuddin92/BMSSP_Logistics_optimizer.git`.
Native C++ research sources, original native tests and all existing backend tests
remain unchanged. [Contracts and architecture](exact_logistics.md) describe the
API, hard constraints, cost/time rounding and geometry behavior.

## Environment and reproducibility

macOS 26.5.1, Apple M4 arm64, 10 logical CPUs, 16 GiB RAM; Apple Clang 21.0.0,
CMake 4.3.3, Python 3.11.15, OR-Tools 9.7.2996, pybind11 2.11.1, NetworkX 3.2.1,
NumPy 1.24.4. Reused the isolated Task 6 environment and its unchanged compiled
native modules/build trees. No Python dependency upgrade occurred. Browser tooling
was installed externally: Node 24.12.0, npm 11.6.2, Playwright 1.56.1 and Leaflet
1.9.4; actual headless Google Chrome 156.0.8078.80. No browser download occurred.

Raw command JSON/logs/JUnit, complete benchmark JSON, actual native browser response,
screenshots, environment versions and source/binary hashes are retained outside
Git in `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task7-evidence`.
Temporary run root is `/private/tmp/bmssp-task7.hYcc0N`. Each command record contains
exact argv, cwd, exit code and monotonic wall seconds, including fixed failures.
No binaries, generated caches or graph datasets are committed.

Python commands use these environment overrides:

```sh
export PYTHONDONTWRITEBYTECODE=1
export GRAPH_CACHE_DIR=/private/tmp/bmssp-task7.hYcc0N/cache
export MPLCONFIGDIR=/private/tmp/bmssp-task7.hYcc0N/mpl
export PYTHONPATH=/private/tmp/bmssp-task6.ZTijar/guard:/private/tmp/bmssp-task6.ZTijar/release/python:/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer/backend
```

The Task 6 socket guard rejects outbound IPv4/IPv6 connections; no road dataset was
downloaded. Legacy failure-path tests attempted the existing OSM loader but the
guard rejected connections. Test fixtures are declared code-generated graphs;
production api.py never imports the browser fixture app or substitutes these graphs.
The application loader now raises on OSM load failure in every mode and refuses
marked synthetic cache/current graphs; the explicit demo helper is retained.

From the checkout:

```sh
ctest --test-dir /private/tmp/bmssp-task6.ZTijar/debug -V
ctest --test-dir /private/tmp/bmssp-task6.ZTijar/release -V
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --test-dir /private/tmp/bmssp-task6.ZTijar/sanitizers -V
node --test frontend/tests/contracts.test.cjs
node --check frontend/app.js
```

From backend, with the environment above:

```sh
/private/tmp/bmssp-task6.ZTijar/venv/bin/python -m pytest tests native_tests logistics_tests -vv --tb=long -p no:cacheprovider --junitxml=/private/tmp/bmssp-task7.hYcc0N/final-all.xml
```

For Python ASan/UBSan replace release/python with sanitizers/python in PYTHONPATH:

```sh
/private/tmp/bmssp-task6.ZTijar/venv/bin/python ../native/python/run_sanitized_macos.py --compiler /Library/Developer/CommandLineTools/usr/bin/clang++ -- -m pytest native_tests logistics_tests -q --tb=long -p no:cacheprovider --junitxml=/private/tmp/bmssp-task7.hYcc0N/final-asan.xml
```

This instruments the native engine/binding, not the distributed third-party
OR-Tools/geospatial binaries. Apple leak detection is disabled as unsupported;
no leak-check claim is made. Task 6's documented framework interpreter launch is
used to load ASan early. Fresh build instructions remain in native_python.md.

| Gate | Result | Command wall seconds |
|---|---|---:|
| Debug CTest | 13/13 | 9.907264 |
| Release CTest | 13/13 | 1.113501 |
| Native ASan/UBSan CTest | 12/12 | 34.417573 |
| All Python suites | 117 passed | 13.135153 |
| Sanitized Python native/logistics suites | 83 passed | 3.754423 |
| Node response/ID contracts | 5/5 | 0.056999 |
| Real Chrome + Leaflet workflow | PASS | 3.067646 |

A final response-key correction preserves submitted alias IDs in location_coordinates.
The entire native VRP API group (14 cases) passed again after that correction; the
full-suite count is unchanged.

The full Python set comprises 34 unchanged original cases, 49 unchanged Task 6
cases and 34 new logistics cases. No tests are skipped or xfailed. Sixteen existing
dependency/API deprecation warnings remain. The 79 native named cases, two native
CLI smokes and binding import smoke pass (sanitizer CTest excludes the Python smoke
because it needs its separate preload launch). The original 34 tests also passed
with the native module directory removed from PYTHONPATH. Final source checks
verify no change to native engine files, CMake, dependencies or earlier test files.

## Correctness evidence

Tests independently sum every returned selected matrix transition and original
edge sequence, check directed original identities, compare costs, enumerate all
small one-vehicle tours where practical, and verify mandatory-stop coverage and
capacity. Seeded six-node graphs use seeds 2025, 17033 and 45141 with feasible
capacity [3,3] and provably insufficient [2,2] for five unit demands. No accuracy
percentage or objective-optimality assertion replaces these checks.

Hard-arc cases include impossible return to depot for one/two/three vehicles,
unreachable cross-customer arcs that require two vehicles, disconnected stops,
zero costs/demands/capacities, equal-cost parallel edges, and exact total checks.
Time cases use genuine seconds, waiting, service, infeasible depot returns and
vehicle start/end windows, missing/invalid duration sources, and fractional-second
post-validation. Injected OR-Tools status tests explicitly verify timeout/failure
mapping; they are not claimed as measured real timeout events. Actual unreachable
native fixtures produce ROUTING_INFEASIBLE and no route.

API cases reject duplicate/overflow/malformed inputs, partial capacity inputs,
unknown native data, execution failures and resource overruns. Missing geometry
preserves verified distance while splitting display segments. Reversed/curved
LineStrings, parallel selected edge identity, WGS84/projected-coordinate rejection,
string aliases and >2^53 IDs are exercised. Mutation after matrix capture cannot
change the in-flight snapshot's costs or geometry; the next request captures the
new graph. Worker-thread/health-progress checks verify solver work stays off the
FastAPI event loop. Native missing-import/error behavior from Task 6 remains tested.

The actual browser response has three distinct native SSSP invocations, one degree
reduction, 36 recursive calls, 33 frontier pulls, 18 BaseCase calls and 151 relaxed
edges. Two capacity-one vehicles serve one customer each, total 1203.0 meters, with
seconds-based service/travel schedules. Every chosen edge uses the same retained
SSSP results that produced the matrix. Native tests disable NetworkX shortest_path,
legacy fallback and the Dijkstra constructor during BMSSP execution. No independent
second route search is used to draw the solution.

## Browser acceptance

Start the declared fixture server from the checkout with the environment above:

```sh
/private/tmp/bmssp-task6.ZTijar/venv/bin/python -m uvicorn logistics_tests.fixture_app:app --host 127.0.0.1 --port 8877
npm install --prefix /private/tmp/bmssp-task7.hYcc0N/browser playwright@1.56.1 leaflet@1.9.4
NODE_PATH=/private/tmp/bmssp-task7.hYcc0N/browser/node_modules BROWSER_EVIDENCE=/private/tmp/bmssp-task7.hYcc0N node frontend/tests/browser.cjs
```

A fresh real Chrome profile loads the actual frontend and real Leaflet library.
Leaflet JS/CSS are served from the external pinned npm package by the harness;
remote tile/font requests are blocked. Blank offline base tiles do not assert road
coverage. Map clicks perform real HTTP node search against the local backend,
including large string IDs. The test sets depot, adds/removes/re-adds stops, rejects
a duplicate, selects two vehicles, enables capacity/time/service and native BMSSP,
solves, inspects vehicle assignments and the curved coordinate [3.002,101.005],
then verifies zero capacity/demand inputs, impossible directed-return HTTP 200,
native execution HTTP 500 without leaked private error text, no stale polylines,
and Clear All. No JavaScript page errors occur. Screenshots and the first actual
native response are retained. The fixture-mode endpoint exists only in fixture_app,
not production. The harness resets it before each independent run.

Fixed intermediate failures are preserved:

- Initial browser map clicks were intercepted by the decorative coverage polygon's
  popup. Decorative layers and selected markers are now noninteractive; real map
  click acceptance passes. The old raw-DOM coordinate workaround was removed.
- A repeated browser run inherited deliberate failure mode from its predecessor;
  the harness now explicitly resets its fixture. No success assertion was removed.
- The combined legacy-failure test initially inherited an original API test's
  import-time solver mock. That new test now explicitly binds the real solver;
  its unchanged NO_SOLUTION assertion passes alone and in the full suite.
- Removing synthetic loader substitution exposed legacy geometry-loading failures
  in two original API tests. Geometry absence is now explicitly reported instead
  of fabricating a segment or failing an otherwise established legacy result.
  Production matrix loading failure still fails the request. All original tests
  pass unchanged, and loader failure has a dedicated no-substitution assertion.

## Bounded end-to-end measurements

Executed from the checkout with the Release extension and offline environment:

```sh
/usr/bin/time -l /private/tmp/bmssp-task6.ZTijar/venv/bin/python benchmarks/logistics/run.py
```

Seed 2025, eight vertices, 15 directed edges (density 0.234375), eight SSSP sources,
two vehicles, seven unit-demand mandatory stops and capacities [4,4]. Each native
engine receives identical graph data/query sets and solver policy. Thirty samples
per engine/state; cold clears snapshot cache, warm retains snapshot/engine after
warmup. This is cache-cold versus cache-warm, not fresh-process startup. Every
returned edge/total and customer coverage is verified. Both modes report 121.25
meters on this fixture; no global optimum is claimed. Time windows are not enabled
in this performance corpus; their correctness is tested separately.

Component/HTTP timings in milliseconds (p50 / nearest-rank p95):

| Engine/state | Matrix | OR-Tools | Paths | Geometry | JSON probe | API latency |
|---|---:|---:|---:|---:|---:|---:|
| native_bmssp_2025/cold | 0.405896 / 0.433584 | 0.637333 / 0.713375 | 0.037603 / 0.041625 | 0.031084 / 0.033249 | 0.091438 / 0.097500 | 2.111021 / 2.363417 |
| native_bmssp_2025/warm | 0.405250 / 0.420292 | 0.639125 / 0.791667 | 0.036958 / 0.048333 | 0.031063 / 0.033623 | 0.088771 / 0.093916 | 1.879480 / 2.242834 |
| native_reference_dijkstra/cold | 0.034041 / 0.036916 | 0.626730 / 0.675709 | 0.037543 / 0.040624 | 0.031187 / 0.032292 | 0.068541 / 0.070709 | 1.688437 / 1.815125 |
| native_reference_dijkstra/warm | 0.031000 / 0.034167 | 0.604354 / 0.627750 | 0.036522 / 0.038582 | 0.030605 / 0.032417 | 0.067104 / 0.071625 | 1.406771 / 1.527833 |

API latency is in-process TestClient including worker dispatch, snapshot validation,
all stages and actual response encoding; it is not deployed network latency.
Matrix timing covers prepared-engine/native queries/extraction, while full API time
also includes snapshot capture. Serialization is explicitly a JSON encoding probe
before final JSONResponse encoding; it is not an additive estimate of all final
serialization overhead. Component medians are independently measured and must not
be summed as a single median pipeline. P95 is the 29th of 30 samples, not a
production-tail claim. Peak process RSS was 191,561,728 bytes, peak footprint
155,763,408 bytes, covering Python/API/geospatial/solver libraries and the entire
fixture process, not per-query allocation. Command wall time was 2.289937 seconds.
BMSSP remains slower than native Dijkstra on this small fixture. Prior Task 5/6
measurements are preserved; no speedup or fastest-engine substitution is claimed.

## Limits and delivery scope

PASS covers verified offline integration, with explicit native selection. No
validated local OSM road dataset or Linux browser/runtime was exercised. Road-data
coverage/traffic quality, conservative millisecond discretization, heuristic search
completeness/optimality and native binary64/theoretical-complexity limits remain
separate. Projected road geometry is marked unavailable rather than reprojected.
Structural/admission limits are not hard heap or cancellation guarantees. Source
mutation during snapshot capture requires owner serialization. Legacy approximation
remains explicitly non-certified, and synthetic loader substitution is removed.
No Task 8 work is started. Only the development branch is authorized for delivery.

OR-Tools references: [routing status/search options](https://developers.google.com/optimization/routing/routing_options),
[time-window duration model](https://developers.google.com/optimization/routing/vrptw).
The implementation was executed against installed OR-Tools 9.7.2996, including its
actual status constants and successor-domain removal behavior.
