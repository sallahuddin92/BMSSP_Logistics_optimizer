# Task 10 — bounded BaseCase memory and heap optimization

## 1. Task 10 Verdict

**PASS.** Correctness, bounded algorithm integrity, allocation reduction, repeated
latency improvement and graph-level regression gates passed for **heap reuse plus
dedicated extracted membership**. The completed-vector reserve experiment was
deferred. Production routing defaults are unchanged; Task 11 was not started.

## 2. Baseline Verification

Workspace: `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer`, branch
`codex/genuine-bmssp-engine`. Initial tree was clean at
`5c42a3f7e8e37373ab613f46e69bafb502514e4a`; origin remains
`https://github.com/sallahuddin92/BMSSP_Logistics_optimizer.git`.

Read-only source archive SHA-256: `e00d9d5736b4a5863b3406c14a26abead489e4bd3309bc4d4d63a7a6004207d8`.
Fresh baseline extension: `eb13427e77a6e74cd6941e642b47330cf941adc165d2706478e2eb631058aab1` (identical to Task 9's final binary).
Final candidate: `29ab3b4dcbdfa22c82f3d17fa37a560ac98dce1b7ade7101d5cf7bfdf6410b98`. A fresh final Release rebuild is
byte-for-byte identical to the measured combined candidate. Archive, native
library/bindings, stage sources, hashes and compiler commands are retained outside Git.

Apple M4 arm64, 10 logical CPUs, 16 GiB; Apple Clang 21.0.0, CMake 4.3.3,
Python 3.11.15. Both variants use C++20, `-O3 -DNDEBUG`, the same arm64 macOS SDK,
warning flags and dependencies; no fast-math/LTO or dependency upgrades.
The original three snapshots and exact Task 8 100-source lists retain their
checksums; see [inventory](road_dataset_inventory.json), the machine summary's
graph/query identities and the raw per-trial build records. No road data was downloaded. Baseline CTest passed 14/14.

## 3. BaseCase Bottleneck

Matched isolated instrumentation, ten recorded sources per graph. Totals include
label-arena allocations triggered inside BaseCase; requested bytes are cumulative
traffic, not live heap memory.

| Graph | BaseCase calls | Allocation requests A→B | Requested bytes A→B |
|---|---:|---:|---:|
| seremban-small | 11,127 | 83,086→27,263 | 4,390,832→3,085,176 |
| seremban-medium | 366,613 | 2,786,893→918,961 | 132,189,720→86,730,696 |
| seremban-port-dickson | 622,395 | 4,727,971→1,559,078 | 217,591,192→140,477,608 |

Corridor baseline: 623,410 queue allocation requests / 19,984,352 bytes;
2,545,523 membership requests / 61,948,592 bytes; 1,558,428 completed-vector
requests / 25,790,888 bytes. Queue peak size/capacity was 4/4; returned U sizes
were at most two (k=2), with partial boundary extraction accounted separately.
All 30 road probes had zero stale/identical-duplicate pops; targeted fixtures and
synthetic duplicate heap records exercise those paths instead of deleting them.
The corridor probe performed 1,558,428 insert attempts; full operation counts and
returned-size histograms are retained in the machine summary.

Corridor baseline instrumented setup/body/teardown totals were
20.759/190.846/32.318 ms over 622,395 calls (about 33.4/306.6/51.9 ns/call).
The selected candidate measured 17.903/147.090/15.628 ms. Initial instrumented
BaseCase occupied about 20% of instrumented road-query time. These clocks/proxies
perturb execution and are **not** ordinary query latency measurements.

Separate five-second sampling of ordinary corridor bindings (75 repeats of the
first recorded source after warmup) found BaseCase on 648/4,233
main-thread stacks (15.3%) in Task 9 versus 393/4,250 (9.2%) selected. This is a
statistical inclusive share, not an exact CPU-time decomposition. Background
waiting threads are excluded from that denominator. Sampling and probes did not
overlap the final timed replay.

## 4. Implementation

- `native/include/bmssp/detail/basecase_heap.hpp`: workspace vector heap with the
  exact prior comparison and standard push/pop primitives. An RAII lease clears
  label owners on every exit while retaining capacity. Growth is checked by vector
  and unrestricted by k. Top is copied before pop.
- `native/src/bmssp_bounded.cpp` and workspace header: reuse heap and a **separate**
  lazy DenseMarks instance for extracted membership; begin a fresh epoch each call.
  Reset clears heap ownership. No recursive parent set shares this scratch.
- `dense_marks.hpp`: bounds-checked contains and size access; existing explicit
  epoch-wrap clearing is preserved. Returned completed vectors still own storage.
- New BaseCase differential/failure/concurrency tests, CTest target, opt-in probe
  driver/generator and reproduction documentation. The allocation interceptor
  remains test/probe-only; the production binding imports its normal new operators.

Heap-only and membership-only stages each passed native tests and received matched
allocation/latency probes before combination. The first two exploratory trials
were noisy (a separate host CPU job was present): heap-only latency was mixed;
membership generally helped. No sample was excluded or unrelated process stopped.
All stage sources/binaries and exploratory results remain available.

A separate small owned-result reserve reduced corridor allocations further to
14,800,246/query-batch and improved medians. However, its exploratory timings were
mixed and the four-trial small-road p99 was **4.529 ms versus 3.071 ms baseline
(+47.5%)**, with retained trial-1 spikes up to 6.563 ms. Their cause was not
established. The reserve is absent from the delivered engine; its results are
not substituted for the selected candidate.

## 5. Bounded Algorithm Correctness

The Task 9 queue/set reference compares exact extraction sequence, boundary B',
ordered U, finite/unreachable symbolic labels, predecessor/edge sequences,
relaxation/update/equality counts. An independent full-vector Bellman-Ford oracle
separately checks symbolic ordering and bounded completeness. Actual multi-level
recursive traces compare **4,071 BaseCase leaves**, observed depth four.

New tests cover k=1/larger k, partial k+1 and exhausted returns, finite/symbolic
bounds, stale records, identical duplicate heap records, equal alternatives,
zero cycles, sinks/isolates, 2,500-vertex paths, repeated/reset workspaces, saved
result ownership, invalid input, injected query/heap-growth failures, forced
uint8 epoch wrap and four concurrent independent workspaces. All CHECK assertions
remain active under NDEBUG. Existing tests and expectations remain intact.

The BaseCase leaf calls no recursive child or observer. Its scratch is dead
before run's observer/next child executes. Dedicated marks therefore cannot
clobber parent completed/pivot collections. Every stage's 30 diagnostic queries
also matched all deterministic queue/membership/result counters (120 matched
source/variant comparisons). Final A/B vectors, selected paths, matrix hashes and
all deterministic BMSSP work counters agree. No change to k/t, degree reduction,
FindPivots, frontier semantics, comparison, strict bounds or valid relaxations;
no Dijkstra fallback. Existing binary64/theoretical limitations still apply.

## 6. Controlled Performance

Four fresh-process trials, eight equal untimed warmups per job, counterbalanced
A/B/C and C/B/A order (A=Task 9, B=selected, C=reserve experiment), reversed graph
and preparation orders, 100 identical sources/trial. All 400 observations per
variant/graph remain included. Times are ordinary binding wall times including
workspace teardown; profiling/interception are absent. Empirical nearest-rank
percentiles describe this fixed repeated distribution, not production tail SLAs.

| Graph | Baseline p50/p95/p99 ms | Selected p50/p95/p99 ms | Pooled p50 reduction | Paired trial p50 reductions |
|---|---:|---:|---:|---|
| seremban-small | 2.765/2.948/3.071 | 2.676/2.889/3.005 | 3.21% | 2.87%, 1.92%, 3.11%, 4.20% |
| seremban-medium | 65.068/67.306/68.260 | 63.065/65.086/65.862 | 3.08% | 3.38%, 3.22%, 3.17%, 2.71% |
| seremban-port-dickson | 111.911/118.154/146.702 | 107.298/110.939/114.483 | 4.12% | 5.64%, 3.46%, 5.00%, 2.87% |

| Graph | 1-source matrix p50 ms A→B | 4-source | 8-source |
|---|---:|---:|---:|
| seremban-small | 2.702→2.637 | 5.562→5.521 | 13.583→13.452 |
| seremban-medium | 64.824→63.621 | 261.450→252.506 | 519.284→503.464 |
| seremban-port-dickson | 113.874→108.759 | 448.711→432.949 | 889.090→865.086 |

Matrices retain 20 observations per graph/variant/source count, including extraction.
The summary also retains p95, every raw matrix timing and query-source regressions.
No selected graph-level p50/p95/p99 regressed. Six small-road source medians did:

| Source | Reachable original vertices | Median µs A→B | Delta µs | Change |
|---|---:|---:|---:|---:|
| 4882417843 | 784 | 2774.166→2817.105 | +42.938 | +1.55% |
| 5735886101 | 1 | 28.749→28.875 | +0.126 | +0.44% |
| 6535592704 | 2 | 28.417→29.896 | +1.479 | +5.20% |
| 7610550429 | 4 | 32.062→32.500 | +0.438 | +1.37% |
| 7613411579 | 2 | 28.271→28.833 | +0.562 | +1.99% |
| 11957995110 | 1 | 23.583→24.646 | +1.063 | +4.51% |

No medium/corridor source median regressed. Dense initialization/fixed setup can
penalize tiny components; the experiment does not isolate those costs from host
noise. The ordinary-source +43 µs regression is also retained. CPU frequency and
scheduling were not pinned. Load, memory and thermal records accompany every job;
all four paired graph medians improved without sampling exclusions.

Preprocessing is unchanged and recorded separately, never selectively subtracted:

| Graph | Baseline native preparation range ms | Selected range ms |
|---|---:|---:|
| seremban-small | 0.413–0.431 | 0.398–0.423 |
| seremban-medium | 10.293–11.110 | 10.513–10.985 |
| seremban-port-dickson | 18.097–19.555 | 18.172–18.464 |

## 7. Allocation and Memory

Same ordinary/all-aligned C++ allocation probe, same first ten sources, independent
processes. Reference checks and graph preparation lie outside allocation counting;
query workspace and result destruction are included. C malloc, metadata and OS
allocations are excluded. Native peak RSS covers the **whole native probe process**.

| Graph | C++ new requests A→B | Requested bytes A→B | Peak native RSS bytes A→B |
|---|---:|---:|---:|
| seremban-small | 311,122→255,299 | 33,302,776→31,997,120 | 8,536,064→8,536,064 |
| seremban-medium | 11,160,195→9,292,263 | 1,361,648,416→1,316,189,392 | 57,131,008→54,657,024 |
| seremban-port-dickson | 18,905,172→15,736,279 | 2,286,205,696→2,209,092,112 | 94,044,160→90,685,440 |

Overall requests fell about 17–18%; corridor BaseCase requests fell 67.0%.
Corridor queue growth fell 623,410→30 allocations (2,240 bytes retained growth
traffic across ten workspaces); membership 2,545,523→10 (one dense array/query).
Remaining completed-vector requests are unchanged. All counted new/delete totals
balance, which is not a general leak detector. RSS can vary by allocator/host state.

The additional dense array costs 14,208 / 284,240 / 481,712 bytes per workspace
on these transformed graphs. It is initialized only if a BaseCase occurs and
survives reset; the 100-source replay includes queries with zero BaseCase calls.
Observed heap peak capacity was four items (128 bytes); it can grow beyond that
on other workloads. Capacity is retained within a workspace, not shared globally
or across independent engine queries. Python RSS includes geometry/modules and
three snapshots; those measurements are recorded separately, not compared with
native-only probe RSS.

## 8. Regression Testing

Debug **15/15**, Release **15/15**, ASan/UBSan **14/14**, supported ThreadSanitizer
**14/14** passed. After an explicit utility-header include was added, Release and
Debug were rebuilt/rechecked and strict native ASan/UBSan reran with
`ASAN_OPTIONS=detect_leaks=0`, `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`.
The final Release binary still matches the measured SHA. No sanitizer findings
were reported; leak detection is disabled and race freedom is not proved.

Python/native/API/logistics/fixture tests **123 passed**; sanitizer-backed native/
logistics/road integration **89 passed**; frontend contracts **5/5**. Sixteen
existing framework deprecation warnings were retained in each Python run.
Actual Chrome **156.0.8078.80** / Leaflet acceptance passed native selection,
real map clicks, capacity feasibility, exact original geometry/snapshot identity
and dataset change. Basemap/font requests were blocked; cached Leaflet assets
were used. The harness stopped only its own local server.

All **960,816 distance comparisons**, **643,571 original directed paths** and
317,245 unreachable comparisons passed on the unchanged three snapshots, with
native Dijkstra and NetworkX checks. Directed reachability, binary64 path sums,
parallel roads, geometry, mandatory stops, capacity, return-to-depot, unreachable
arcs, API errors and time-window feasibility/unsupported-duration rejection remain
covered. Full road gate: 332.454 s.
Its incidental timings ran alongside correctness builds and are excluded from
performance acceptance. No test was replaced, weakened, skipped or counted as a
pass when blocked.

Exact argv, environment, exit codes, elapsed times and complete logs are retained
in `native-suite-commands.json`, `strict-check-commands.json`,
`application-commands.json`, benchmark manifests and profiler command records in
the evidence root. Two corrected setup errors are retained: the desktop resumed
in a directory without .git; the first baseline replay pointed to the build root
instead of its python extension directory. Neither is counted as a successful run.

## 9. Remaining Bottlenecks

1. Recursive temporary hash/allocator work: selected corridor stack sampling still
   shows unsigned-key hash insertion (275 top frames), tiny allocation/free and
   recursive run work. Attribute FindPivots round-local membership next; live
   parent/child collections cannot share one scratch set.
2. Symbolic comparison: 617 top frames in the selected sample; ordering is
   unchanged. Task 9's short-chain evidence does not justify a speculative cache.
3. Label creation/arena synchronization and remaining result ownership: a typical
   corridor query still creates about 925,086 label nodes and about 1.6 million
   C++ allocation requests. BaseCase completed vectors remain intentionally owned.

The same-process interleaved, equally warmed 100-source reference replay checked
complete vectors and found the selected engine still much slower than native
Dijkstra. These separate measurements are not the primary A/B table:

| Graph | BMSSP p50 ms | Dijkstra p50 ms | Ratio |
|---|---:|---:|---:|
| seremban-small | 2.541 | 0.035 | 72.7× |
| seremban-medium | 59.678 | 0.783 | 76.2× |
| seremban-port-dickson | 102.156 | 1.369 | 74.6× |

No asymptotic, exact-real arithmetic, universal speed advantage, production tail,
Linux-performance or exhaustive race/leak guarantee is claimed. Existing OSM
clipping, turns, durations and traffic limitations remain documented in Task 8.

## 10. Git Delivery

Only native BaseCase support, required tests/tools and documentation are changed.
No datasets, binaries, caches, secrets, production defaults or unrelated projects
belong in the commit. Origin/main remains
`94f54b5206b46541dc12f5c7d8cb7fa019e4f877`. Commit/push verification and final clean
status are written after delivery to `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task10-evidence/git-delivery.json`; this avoids a
self-referential commit hash in a tracked report. No main merge or force push.

Evidence root: `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task10-evidence`. It retains the source archive, stage binaries/sources,
raw initial/matched profiles, sampling, rejected reserve experiment, all A/B jobs,
preprocessing/RSS, road/browser results and SHA-256 index. See
[machine summary](basecase_performance_summary.json) and
[reproduction/ownership workflow](basecase_performance_workflow.md).

## 11. Next Single Task

Measure and reduce **FindPivots round-local membership allocation**, beginning with
scoped attribution and independent coverage/recursive tests. Preserve returned
W/P ownership and active parent/child state. No Task 11 implementation is included.
