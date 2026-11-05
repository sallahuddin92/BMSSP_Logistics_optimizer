# Task 9 — measured native execution engineering

**PASS.** Correctness, supported memory/race checks, native latency/allocation improvements, real-road replay and application regressions passed. No theoretical complexity improvement or universal floating-point theorem is claimed.

## Baseline and method

Clean branch `codex/genuine-bmssp-engine`, baseline `698c14951399aca25a2409c8d1e26532c9d26587`. Immutable source archive SHA-256: `677e38c7a8d908459fece86ffe0c78179be0cd60e9ff95c6cf70cdd82f52964f`. Fresh baseline Release extension SHA-256: `623b4544161f9c618d45d24657ebcd6e37381b27d4e25caf2cab7fc50454005d`; final candidate: `eb13427e77a6e74cd6941e642b47330cf941adc165d2706478e2eb631058aab1`. The archive, baseline binaries, stage source snapshots, native source hashes and compile commands are retained outside Git.

Apple M4 arm64, 10 logical CPUs, 16 GiB RAM; Apple Clang 21.0.0, CMake 4.3.3, Python 3.11.15. Both engines use C++20, `-O3 -DNDEBUG`, the same arm64 SDK and warning flags, without fast-math/LTO. Existing Task 8 GraphML checksums and canonical snapshots are unchanged; see [dataset inventory](road_dataset_inventory.json). No new download or dependency upgrade was needed. Task 8 graph selection was not reimplemented.

Fresh uninstrumented pre-change baseline medians were 3.733/85.357/146.370 ms; these are setup observations, not the speedup comparison. The final experiment uses four fresh-process trials, eight equal untimed warmups/job, identical 100-source lists, AB/BA/BA/AB order and reversed graph/load orders. Every full distance vector, sampled original path and deterministic BMSSP work counter agrees A/B. Profiling and allocation interception are absent from timed binding queries. Every sample/failure, host load/memory/thermal record and per-trial build/preprocessing record is retained.

## Bottleneck evidence and focused changes

| Function / area | Evidence | Change / decision |
|---|---|---|
| LabelArena::allocate | Representative corridor query: 925,086 immutable 48-byte nodes; original code allocated each separately | Retained mutex/shared ownership; stable 32→4096-node array slabs and iterative destruction |
| Frontier containers | Ordinary/all-aligned allocation probe: baseline corridor query 4,008,438 C++ new calls; source and stack samples identify list/map/hash-node allocation | Per-frontier PMR pool for existing lists, fences, handles and batch index; no structural queue substitution |
| validate_frontier | Baseline structural probe: 126,318 checks, 380,016 allocations, 10,632,816 requested bytes in one corridor query | Workspace-owned dense uint32 epoch marks, consumed only within a completed validity check |
| compare(SymbolicLabel) | All 30 baseline probe queries had maximum vertex/edge chain walk 1; corridor example 6,210,330 calls but only 481,806 vertex steps | Complete ordering unchanged; no speculative comparison cache |

Each change was compiled, checked by the native oracle/invariant suite, and measured before adding the next. Two-trial incremental comparisons retained the immutable original and prior-stage binaries. Slabs improved medians; pooling improved them further; marks improved them again on every workload in both exploratory trials. No implemented optimization was rejected or a mismatch suppressed.

Rejected/deferred designs were not benchmarked as successes: mutex removal would break shared-arena extension safety; a vector of nodes would invalidate parents; swap-erasing frontier vectors could change in-block iteration/handles; sharing one live completed/pivot scratch set across depths would corrupt parent state. Broad pivot/complete-set rewrites and comparison caching were deferred.

Files: `native/src/symbolic_label.cpp` (slabs); `native/include/bmssp/bounded_frontier.hpp` and `native/src/bounded_frontier.cpp` (local pools); `native/include/bmssp/detail/dense_marks.hpp`, workspace header and bounded implementation (validity marks); new memory/wrap tests and isolated allocation/benchmark tools. Ownership proofs, tradeoffs and commands are in [native_performance_workflow.md](native_performance_workflow.md).

## Controlled A/B latency

Pooled empirical nearest-rank percentiles, **400 retained samples per variant/graph** (four independent process trials of the same 100-source distribution). p99 is descriptive, not a production tail SLA.

| Graph | Baseline p50/p95/p99 ms | Candidate p50/p95/p99 ms | Pooled p50 reduction | Paired trial reductions |
|---|---:|---:|---:|---|
| seremban-small | 3.809/4.096/4.187 | 2.746/2.909/3.017 | 27.90% | 29.89%, 27.32%, 28.08%, 27.40% |
| seremban-medium | 86.003/88.830/91.542 | 64.216/66.405/67.560 | 25.33% | 25.27%, 25.69%, 25.52%, 24.98% |
| seremban-port-dickson | 146.478/150.817/157.322 | 109.588/112.601/114.834 | 25.18% | 25.27%, 25.46%, 24.86%, 25.07% |

| Graph | 1-source matrix p50 ms A→B | 4-source A→B | 8-source A→B |
|---|---:|---:|---:|
| seremban-small | 3.777→2.716 | 7.714→5.624 | 18.815→13.600 |
| seremban-medium | 85.739→64.544 | 345.978→258.017 | 687.366→514.059 |
| seremban-port-dickson | 147.848→111.070 | 589.409→441.553 | 1172.120→879.749 |

Matrix distributions retain 20 samples/variant/graph/source count, including extraction on both sides. Preprocessing is unmodified and measured separately in each fresh process; it is never subtracted selectively. Wall query time includes binding wrapping and workspace teardown. CPU frequency/scheduling were not pinned; load, vm_stat and thermal snapshots accompany each job. All four paired trial medians improved for every graph, so the conclusion does not rely on one lucky run.

## Memory and safety

The following allocation totals cover the same first **10 recorded sources** per graph, using the same current probe driver linked separately to the immutable baseline and candidate. Counts cover successful ordinary and aligned C++ new/new[] requests; bytes are cumulative requested allocation traffic, not live heap or allocator metadata. Peak RSS covers each whole native-only probe process (graph/reduction, query results and reference checks), not Python geometry storage.

| Graph | Heap calls A→B | Requested bytes A→B | Peak native process RSS bytes A→B |
|---|---:|---:|---:|
| seremban-small | 657,707→311,122 | 35,924,896→33,302,776 | 8,536,064→8,536,064 |
| seremban-medium | 23,429,404→11,160,195 | 1,510,215,008→1,361,648,416 | 60,112,896→53,805,056 |
| seremban-port-dickson | 39,785,208→18,905,172 | 2,429,800,288→2,286,205,696 | 97,189,888→89,882,624 |

Counted allocations/deallocations balance for every probed query. This is scoped evidence, not a general leak detector. Slabs may retain up to one unused tail and saved labels retain their complete arena, as before. Pool chunks retain size-class capacity until frontier destruction; cumulative requested-byte savings are smaller than the ~52% reduction in heap calls. Dense marks cost four bytes per transformed vertex, initialized per query. Python worker RSS/peaks include all three road/geometry snapshots and are reported independently; they are not compared to native-only RSS.

Debug **14/14**, Release **14/14**, ASan+UBSan **13/13**, ThreadSanitizer **13/13** passed. Supported sanitizer tests reported no findings; this does not prove all-program race freedom. Leak detection is disabled/unsupported on the macOS runtime; no leak-detection claim is made. New tests inject root, slab-growth, query and frontier allocation failures; validate saved parent references and retries; exercise shared-arena concurrent growth/tie order, independent queries, repeated large/deep arena destruction, frontier reinitialization and forced epoch wrap. All existing zero-cycle, deep-path, ordered-model and bounded-contract tests remain intact.

## Regressions and remaining costs

- seremban-small: 3 query-index medians regressed:
  - source 7613411579 (2 reachable original vertices): 28.333→30.105 µs, +1.772 µs / 6.25%.
  - source 11957995110 (1 reachable original vertices): 22.437→23.813 µs, +1.376 µs / 6.13%.
  - source 5735886101 (1 reachable original vertices): 27.250→27.687 µs, +0.437 µs / 1.61%.
- seremban-medium: no query-index median regressed across the four trials.
- seremban-port-dickson: no query-index median regressed across the four trials.

These tiny-component regressions are consistent with fixed slab/pool setup and the per-query dense-mark array, plus unpinned timer/scheduling noise; the experiment does not isolate their exact causal share. No graph-level p50/p95/p99 regressed. All raw slower samples remain included.

An interleaved same-process current reference replay used 100 recorded queries/graph and equal warmups, alternating BMSSP/Dijkstra order. Full vectors agree exactly. Candidate BMSSP remains **approximately 78–82× slower** than native Dijkstra:

| Graph | Current BMSSP p50 ms | Dijkstra p50 ms | Ratio |
|---|---:|---:|---:|
| seremban-small | 2.739 | 0.035 | 78.5× |
| seremban-medium | 64.149 | 0.782 | 82.0× |
| seremban-port-dickson | 109.606 | 1.370 | 80.0× |

Uninstrumented post-change macOS sampling (2,524 main-thread samples) still shows compare (297), xzone free (199), tiny malloc (180), additional free (163), hash insertion (157), recursive run (108), and BaseCase (40), with allocator/hash work also attributed through callees. This remains substantial repeated recursive/temporary-container work; short chain walks do not justify a path-comparison cache. Sampling/counter diagnostics are separate from latency trials.

## Full correctness and application

All **960,816** established real-road distance comparisons and **643,571** original directed reachable paths passed, including geometry, one-way/reverse reachability, parallel roads, disconnected components, mandatory-stop/capacity/return-to-depot and infeasible logistics cases. The exact binary64 contract and existing path sums are unchanged. The full gate took 260.529 seconds; incidental road-run timing samples were collected alongside correctness builds and are **not** the controlled performance comparison.

Python/native/API/logistics/fixture tests **123 passed**; sanitizer-backed integration **89 passed**; frontend contracts **5/5**. Real Chrome/Leaflet evidence is retained separately. No test expectations were weakened and no successful-looking fallback replaced an engine error. All genuine mechanisms, equality-valid relaxations, deterministic distance/hop/reversed-vertex/parallel-edge ordering, strict bounds, complete-set disjointness and original-edge reconstruction remain intact. Production defaults are unchanged.

## Evidence, reproducibility and limits

Persistent evidence: `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task9-evidence`. Primary directories: `final-ab`, `allocations-verified`, `real-roads`, `reference-replay`; source/archive/binary hashes, stage copies, profiler outputs, full stdout/stderr and compiler commands are retained. [Machine-readable summary](native_performance_summary.json) contains all primary percentiles, matrix summaries, allocation totals, trial reductions and query regressions.

All three native candidates were kept; no failed optimization was relabeled PASS. Setup failures are retained: direct CLT compilation omitted CMake SDK flags (`cfenv` missing); baseline probe preservation mistakenly removed execute/write permissions, causing permission/link failures. Fresh standalone probe builds fixed this without changing the preserved baseline engine/library. Empty failed-attempt JSONs are not measurement records. The current source verifier refuses mixed baseline/candidate private layouts.

The implementation still has full symbolic comparisons, expected-time hash tables, CSR sorting, retained snapshots, fixed-size pool/slab tradeoffs and IEEE binary64 limits; the paper’s exact-real unit-cost bound is not established. Linux/other toolchain performance, production tail guarantees and exhaustive race/leak freedom are unmeasured. Road clipping/quality and unsupported turns/durations/traffic remain as documented in Task 8.

Next single task: reduce remaining BaseCase/recursive temporary-container allocation using lifetime-safe reusable scratch, beginning with bounded BaseCase heap/membership storage and retaining independent ordered/bounded oracles. Post-change sampling and remaining ~1.9 million allocations in a corridor query justify prioritizing allocation/hash bookkeeping rather than comparison caching. Task 10 was not started.
