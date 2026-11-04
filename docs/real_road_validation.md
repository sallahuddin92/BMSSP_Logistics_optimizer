# Task 8 measured acceptance — 5 November 2026

**PASS: real-road acceptance. PASS: integration optimization. Native BMSSP remains slower than native Dijkstra.**

Baseline was clean branch `codex/genuine-bmssp-engine`, commit `611b3450bc226360067b044a684318106e726975`, with the requested origin. No existing functionality, history, dependency pins or production defaults were removed. This task did not merge to main.

## Dataset and correctness

Source: [Geofabrik Malaysia/Singapore/Brunei](https://download.geofabrik.de/asia/malaysia-singapore-brunei.html), 252,760,912 PBF bytes. PBF header replication time: **2026-11-03T21:24:23Z**. Downloaded/extracted 2026-11-04 UTC (5 November Malaysia local time). SHA-256:

`4807c977d1cf559928f41ca004f6e0a51722db0e994d06ab4597088189c60668`

Full rectangles, file checksums and canonical native identities are tracked in [road_dataset_inventory.json](road_dataset_inventory.json). Data © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright). No research code was copied.

| Workload | Vertices | Directed edges | Weak/strong components | Distance comparisons | Validated reachable paths | Longest checked path |
|---|---:|---:|---:|---:|---:|---:|
| seremban-small | 834 | 1,776 | 9/56 | 20,016 | 11,113 | 7.46 km |
| seremban-medium | 14,464 | 35,530 | 22/157 | 347,136 | 242,088 | 31.41 km |
| seremban-port-dickson | 24,736 | 60,214 | 44/220 | 593,664 | 390,370 | 57.89 km |

Total: **960,816 exact distance comparisons and 643,571 valid original-edge paths**. Twenty-four oracle sources per graph; every destination checked. BMSSP/native Dijkstra/NetworkX agree exactly under the documented binary64 policy. No tolerance or changed expectation masked a mismatch.

Checks included one-way/reverse asymmetry, disconnected components, parallel roads, curved geometry, original IDs beyond 32 bits, repeated-source matrices and predecessor endpoints/edge sums. All selected finite paths had usable geometry. `ENDPOINTS_ONLY` identifies actual unsimplified two-node road edges, not invented stop-to-stop connectors. The fixed workloads are boundary-clipped; missing boundary connections are not claimed to be engine errors or complete regional coverage.

Initial medium preparation hit the default 10,000-node admission limit. Its actual requirement was 14,464 vertices/35,530 edges; the corridor needs 24,736/60,214. No area was shrunk. Preparation resumed with explicit local benchmark caps of 40,000 nodes, 100,000 edges and 600,000 geometry points. Production defaults remain 10,000/40,000/200,000. The data directory used about 316 MiB against a 1 GiB budget and 5 GiB reserve; the source was reused, not downloaded again. Initial failure and resumed logs are retained.

## Logistics and browser

Each graph passed production `/vrp` requests for one vehicle and two capacity-limited vehicles, all mandatory stops exactly once, directed return-to-depot paths, exact native leg distances, and road geometry. Capacity-infeasible and genuinely disconnected requests returned `NO_SOLUTION`, without successful route geometry. Time windows without valid durations returned HTTP 400; no duration, speed or traffic data was fabricated.

Real Chrome 156.0.8078.80 + Leaflet 1.9.4 passed actual map clicks, native node discovery, two vehicles/capacities, source and snapshot identity, native execution diagnostics, exact displayed-polyline/API equality, and dataset-change clearing. The screenshot and request/response JSON are retained. Remote basemap tiles/fonts were intentionally blocked; this proves real selected road geometry, not a live basemap.

## Uninstrumented query performance

Apple M4 arm64, 10 logical CPUs, 16 GiB RAM; Apple Clang 21.0.0, CMake 4.3.3, Python 3.11.15, Node 24.12.0. Release flags `-O3 -DNDEBUG`, C++20; no fast-math. Per-build compile command records are retained. One hundred seeded sources per graph/engine, all retained. Empirical nearest-rank percentiles; p99 is coarse with 100 samples.

| Workload | BMSSP p50/p95/p99 (ms) | Dijkstra p50/p95/p99 (ms) | BMSSP/Dijkstra p50 |
|---|---:|---:|---:|
| seremban-small | 3.782/4.074/4.306 | 0.033/0.035/0.036 | 115.9× slower |
| seremban-medium | 86.422/89.578/94.496 | 0.769/0.834/0.916 | 112.4× slower |
| seremban-port-dickson | 171.861/180.235/188.679 | 1.559/1.669/1.684 | 110.2× slower |

The full post-compatibility replay also passed with identical correctness counts. Native query timings vary substantially across runs with uncontrolled host conditions; they are not production tail guarantees. Replayed medium queries using the original release extension and the pre-compatibility instrumented build with profiling disabled are also retained: original p50 266.2 ms versus 200.5 ms in the later process. These are sequential, unpaired process runs, **not evidence of a native algorithm improvement or a reliable measurement of profiling-hook overhead**. The primary table above compares engines on identical snapshots and recorded source lists.

## Measured bottleneck and optimization

Before optimization, Python capture profiling attributed 0.089/0.125 instrumented seconds to `capture_roads` on the small graph (two captures during cold construction). Warm mutable validation medians in the full run were 25.2 ms, 496.2 ms and 889.5 ms. Repeated geometry validation/copying and canonical hashing were a demonstrated integration bottleneck.

The optimization retains an explicit immutable native snapshot inside the verified fixture registry. Mutable NetworkX inputs still validate fully. File bytes/checksums are checked on every selection; admission/geometry caps are checked on immutable reuse. No mtime/identity/version-token shortcut, Dijkstra substitution, equality-relaxation change or research-invariant change was introduced. Added native instrumentation is opt-in and does not change routing logic.

Paired before/after fixture selection includes file verification and adapter admission on both sides. Thirty alternating-order samples per workload, identical graph/snapshot IDs. The before side performs full mutable graph capture; the after side reuses the private immutable snapshot.

| Workload | Before p50/p95 (ms) | After p50/p95 (ms) | p50 cost reduction |
|---|---:|---:|---:|
| seremban-small | 25.782/43.516 | 0.393/0.543 | 98.48% |
| seremban-medium | 502.202/512.876 | 7.154/8.488 | 98.58% |
| seremban-port-dickson | 901.973/923.560 | 12.453/16.304 | 98.62% |

No p99 is reported for 30 samples. This is an integration improvement, not an SSSP speedup or improved theoretical complexity. Cold snapshot creation, degree reduction, 1/4/8-source matrices, result extraction, paths, OR-Tools, geometry, serialization and all raw timings are retained separately. Peak acceptance-process RSS was 1,576,321,024 bytes (~1.47 GiB), cumulative across sequential workloads; it is not per-query allocation volume. Label-node allocation counts are retained; total allocator bytes and importer peak RSS were not independently measured.

Opt-in exclusive scope profiles on medium/corridor attributed approximately 29.7% to recursive bookkeeping, 24.8% to comparison, 23.4% to frontier, 9.7% to BaseCase, 6.8% to pivots and 5.6% to label allocation. Clock overhead materially inflates frequent scopes; these percentages describe **instrumented** work. A separate uninstrumented three-second macOS sample had 2,546 main-thread samples: tiny malloc 263, xzone free 328, additional `_free` 236, label comparison 227, hash insertion 136, recursive run 76. Other allocator/helper frames are present in the raw profile; blocked worker-thread samples are excluded from this main-thread denominator. Allocation/hash bookkeeping and comparison are demonstrated remaining native costs; symbolic-label allocation alone is not established as the primary bottleneck.

## Regression gates and reproducibility

Final gates: Native Debug CTest **13/13**, Release **13/13**, ASan+UBSan **12/12**; Python **123 passed**, sanitizer-backed native/Python/logistics/fixture integration **89 passed**; frontend contracts **5/5**; real-road browser **PASS**; three real-road workloads **PASS**. Existing numerical, independent-oracle, randomized differential, bounded-recursion, tie, path, integration and logistics checks remain intact. A new C++ case verifies legacy aggregate options and opt-in profiling; the added profile flag follows the existing observer. No test expectations were weakened.

Commands and contracts are in [real_road_workflow.md](real_road_workflow.md). Local execution used `/private/tmp/bmssp-task8.gS01c3/{debug,baseline,sanitizers}`, the Task 6 Python 3.11 virtualenv, and external fixture root `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-road-data`. Exact command argv/exit codes/durations, source manifests, compiler flags, original and final query samples, `.prof`/native stack samples, API payloads and browser proof are retained in `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task8-evidence`.

Core final commands (from the repository root, with environment shown in the workflow):

```sh
ctest --test-dir /private/tmp/bmssp-task8.gS01c3/debug --output-on-failure
ctest --test-dir /private/tmp/bmssp-task8.gS01c3/baseline --output-on-failure
ctest --test-dir /private/tmp/bmssp-task8.gS01c3/sanitizers --output-on-failure
python -m pytest backend/tests backend/native_tests backend/logistics_tests backend/road_tests -p no:cacheprovider -q
python native/python/run_sanitized_macos.py --compiler /Library/Developer/CommandLineTools/usr/bin/clang++ -- -m pytest backend/native_tests backend/logistics_tests backend/road_tests -p no:cacheprovider -q
node --test frontend/tests/*.test.cjs
python tools/road_acceptance.py --output /private/tmp/bmssp-task8.gS01c3/after-compat
python tools/road_snapshot_benchmark.py --output /private/tmp/bmssp-task8.gS01c3/paired-compat.json
node frontend/tests/road_browser.cjs
```

The initial complete road run took 460.863 seconds; the final post-compatibility replay took 297.748 seconds; the final paired integration measurement took 51.522 seconds (the earlier paired run took 102.360 seconds and independently showed the same cost reduction). Final post-compatibility Python runner took 12.553 seconds; sanitizer Python runner 3.028 seconds. Final native CTest runner durations were Release 9.448 s, Debug 16.490 s and ASan+UBSan 39.677 s. Earlier final-gate and concurrent smoke records remain retained separately. The initial 252.8 MB download took 132.119 seconds; resumed extraction scans took 45.097/141.516/33.000 seconds for nodes/ways/coordinates. These scans are shared across regions, not costs to add three times.

## Remaining limitations and next task

OSM quality and static access tags, clipping, absent turn restrictions/durations/traffic, binary64 numerical limitations, and unmeasured Linux performance remain. The PBF latest URL is mutable; exact reproduction requires retained verified source bytes or an archive with the same SHA-256. One hundred queries are not a production-scale certification. Native BMSSP remains roughly two orders of magnitude slower than Dijkstra here; the default engine was not changed.

Next single task: reduce demonstrated native frontier/recursive allocation and hash-table overhead, using paired real-road replay and the full correctness/invariant regression gates before accepting a change. Task 9 was not started.

The initial complete run and the complete replay after the C++ source-compatibility
fix are both retained; correctness counts and snapshot identities agree. The final
report uses `after-compat`, `paired-compat.json`, `native-sample-current.txt` and
`browser-compat`. Earlier measurements, including the initial medium admission
failure, are preserved separately. `precompat-code.patch` records the earlier
instrumentation build against the clean baseline. No source compatibility fix
changed the shortest-path algorithm or relaxed a gate.
