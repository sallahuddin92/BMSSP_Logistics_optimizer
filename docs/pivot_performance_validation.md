# Task 11 — FindPivots membership and allocation optimization

## 1. Task 11 Verdict

**PASS, with reported memory and latency tradeoffs.** Research integrity,
FindPivots equivalence, correctness, allocation reduction, useful repeated median
improvement and application regression gates passed. The combined dense-membership
candidate is retained. Small-road p99 and five source medians regressed; those
observations remain included. Production routing defaults are unchanged.

## 2. Baseline Verification

Clean branch `codex/genuine-bmssp-engine` at
`62b2d0d8926df6ff4ac46b3a4e5c2deabea03b49` in
`/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer`. Origin remains
`https://github.com/sallahuddin92/BMSSP_Logistics_optimizer.git`.

Immutable Task 10 source archive SHA-256: `b7710922c85ffc54aed531804818bba6bd92ddb54799b5a1f97db94c14873988`.
Fresh baseline binding: `29ab3b4dcbdfa22c82f3d17fa37a560ac98dce1b7ade7101d5cf7bfdf6410b98` (identical to Task 10's
delivered binary). Final candidate: `303274e560a65465ee75899d72c7d720fb2654b2290355198f03ac3f17d2e80b`. A separate final
Release rebuild matched the measured candidate byte-for-byte. Baseline CTest
passed 15/15. Source archives, stage sources/binaries, hashes, CMake caches and
compiler commands remain outside Git.

Apple M4 arm64, 10 logical CPUs, 16 GiB; Apple Clang 21.0.0, CMake 4.3.3,
Python 3.11.15. Both variants use C++20, `-O3 -DNDEBUG`, the same arm64 SDK and
warning flags, without fast-math/LTO or dependency upgrades. Reused the three
verified GraphML snapshots, existing 17-digit round-trip native probe exports,
and exact Task 8 100-source lists. No new OSM download. Their identities/checksums
are in [inventory](road_dataset_inventory.json), the machine summary and raw build
records; all four process trials verified identical binaries and query identities.

## 3. FindPivots Allocation Evidence

Before native changes, isolated instrumentation established the allocation target.
The following is the baseline total for the first ten recorded corridor sources.
Operation clocks shown here include observation/counter work, exclude later
container teardown and are **not uninstrumented query latency**. The whole-function
clock includes raw trace/registry overhead. The residual includes loops, label
work, teardown and instrumentation; it is not exclusive time for just the other
allocation category. Non-early forest work was rare in these road queries.

| Function/operation | Calls/work units | Allocations | Requested bytes | Measured diagnostic cost |
|---|---|---:|---:|---:|
| Whole FindPivots | 9,459 | 2,979,934 | 249,240,504 | 396.071 ms inclusive |
| Cumulative membership | 1,624,331 insert attempts including seeds | 1,647,683 | 66,824,640 | 74.810 ms operation scopes |
| Round membership | 1,043,619 inserts; 18,890 constructions | 1,153,086 | 50,774,224 | 67.400 ms operation scopes |
| Current/next vectors | 18,890 rounds plus initial current copies | 140,916 | 24,062,496 | 22.824 ms operation scopes |
| Forest maps | 1 non-early invocation | 43 | 1,824 | 0.004 ms operation scopes |
| Owned W/P vectors | 9,459 returned results | 37,838 | 37,184,224 | 16.902 ms operation scopes |
| Other/unscoped/teardown | 9,459 invocations | 368 | 70,393,096 | 214.131 ms residual |

Membership accounted for about 94% of FindPivots allocation requests. The two sets
were therefore targeted; forest maps were left intact. Current/next vectors and
owned results were measured separately and retain their original representation.

| Graph (10 queries) | FindPivots calls | Rounds | Early returns | Selected pivots total | Calls with pivots |
|---|---:|---:|---:|---:|---:|
| seremban-small | 357 | 693 | 357 | 7,637 | 357 |
| seremban-medium | 5,573 | 11,130 | 5,568 | 345,627 | 5,573 |
| seremban-port-dickson | 9,459 | 18,890 | 9,458 | 581,004 | 9,459 |

Raw per-call [current size, next size, cumulative visited size] rows, membership
attempts/unique/duplicates, hash construction counts, returned-data retention and
peak tagged live bytes are retained. On the corridor, cumulative attempts were
1,624,331 (1,581,959 unique / 42,372 duplicates); round attempts were 1,043,619
(1,043,325 unique / 294 duplicates). These and every recorded call/round/result
size agree between baseline and combined probes.

Separate five-second sampling of ordinary corridor bindings (75 repeats of the
first recorded source after warmup) placed FindPivots on **616/4,227 main-thread
stacks (14.6%)**, versus **255/4,209 (6.1%)** selected. This statistical inclusive
share confirms meaningful native cost; it is not an exact CPU decomposition.
Sampling/probes did not overlap timed A/B or reference jobs.

## 4. Implemented Changes

| File | Change | Justification | Lifetime guarantee |
|---|---|---|---|
| `native/src/bmssp_bounded.cpp` | Replace round and cumulative membership sets with distinct epoch arrays | Dominant measured requests | Fresh cumulative epoch/call; fresh round epoch/round; traversal and returned vectors unchanged |
| `native/include/bmssp/detail/pivot_scratch.hpp` | Two private workspace DenseMarks instances and a non-reentry RAII guard | Isolate operation lifetimes | No global scratch; active flag clears on normal, early and exceptional exits |
| Workspace header | Own PivotScratch separately from BaseCase/validation marks | Preserve active state | No caller/child set shares these arrays |
| Frozen reference, pivot tests and CMake test derivation | Compare actual current FindPivots round/label state with Task 10 | Verify full procedure equivalence | Hooks compile only into pivot_tests, never the library/binding/CLI/timing binaries; native tests need no Python |
| Probe driver/generator/measurement support | Scoped allocation/live-byte attribution and optional operation clocks | Measure before selecting changes | Executable-only allocation observer; registry recording disables its own accounting; frozen support source/hashes retained |

A and B were built, tested and probed independently before combination. Both
passed 16 Release tests; both reduced every graph median in both exploratory
trials, with noisy tail samples retained. On ten corridor queries, round-only
requests were 14,583,203 and cumulative-only 14,088,606, versus baseline 15,736,279;
combined reached 12,935,530. The final four-trial replay validates the combination.

No failed optimization was disguised as a pass. No vector/forest representation
experiment was needed: membership removal eliminated about 94% of scoped requests,
while current/next requests remain only 140,916 per ten corridor queries. Further
capacity reuse is deferred instead of bundled into this attribution.

## 5. Algorithm Equivalence

The test-only frozen Task 10 procedure preserves original sets, maps and control
flow. CMake derives a separate test translation unit from the current source and
adds before/after/round hooks. **1,846 calls and 3,775 rounds** compare exact current,
next, W and P sequences, early flags, every symbolic label/predecessor/edge choice,
required rounds, edge scans, equality-valid updates and deterministic counter
deltas. Tests include actual nested recursive execution, not only standalone
FindPivots. Independent full-path Bellman-Ford and bounded-contract observers
check complete-frontier coverage, child-set disjointness and boundary monotonicity.
Existing independent symbolic/frontier/BaseCase/random oracles remain intact.
Final review added explicit strict-above-B and duplicate/shared-successor fixtures;
the expanded pivot target passed again in Release, Debug, ASan/UBSan and TSan.

Covered k=1/larger k, empty expansion, duplicate/shared successors, zero/equal paths,
directed cycles, parallel edges, degree-reduced high-degree originals, early and
exact workload limits, multiple/no pivots, disconnected vertices, sinks/isolates,
large IDs, repeated calls with/without reset, saved returned vectors, injected lazy
initialization failures and recovery, forced uint8 epoch wrap, concurrent independent
workspaces and actual reentry rejection. CHECK assertions stay active under NDEBUG.
The BaseCase suite still compares 4,071 Task 9 leaves as before.

Algorithm 1 still relaxes **without B** where required, then restricts membership
expansion strictly below B. k/t, degree reduction, symbolic order, forest tightness,
subtree counts, pivot roots and early `W.size() > k*|S|` termination are unchanged.
No approximate membership, sorting substitute, skipped equality or Dijkstra fallback.

Control-flow proof: FindPivots finishes and consumes its forest membership before
run creates its frontier and executes recursive children. Returned P/W own their
vectors, so parents never read marks afterward. The two dedicated arrays are
therefore reusable; validation and BaseCase marks remain separate. The guard rejects
overlapping FindPivots entry and unwinds on exceptions. Reset after an exception
remains the existing contract; new epochs ignore abandoned membership. Other
concurrent/reentrant mutation of one workspace remains unsupported.

## 6. Performance A/B

Four fresh baseline/candidate process pairs, eight identical untimed warmups/job,
AB/BA/BA/AB order, reversed graph/preparation order, identical compiler settings
and source lists. No heavy build, test, interception or sampling overlapped timed
jobs. Every **400 samples/variant/graph** is retained. Complete binary64 distance
vectors, selected original path fingerprints, matrices and all deterministic work
counters agree. Wall time includes binding/result/workspace teardown.

| Graph | Baseline p50/p95/p99 ms | Candidate p50/p95/p99 ms | Pooled p50 reduction |
|---|---:|---:|---:|
| seremban-small | 2.560/2.781/2.955 | 2.335/2.606/3.110 | 8.80% |
| seremban-medium | 61.312/66.783/81.446 | 54.580/58.736/64.756 | 10.98% |
| seremban-port-dickson | 104.750/113.985/131.426 | 94.445/101.352/105.619 | 9.84% |

| Graph | Paired trial p50 reductions |
|---|---|
| seremban-small | 8.65%, 10.74%, 7.78%, 7.31% |
| seremban-medium | 11.46%, 10.16%, 10.18%, 12.09% |
| seremban-port-dickson | 10.87%, 9.78%, 9.25%, 10.22% |

| Graph | 1-source matrix p50 ms A→B | 4-source | 8-source |
|---|---:|---:|---:|
| seremban-small | 2.539→2.310 | 5.168→4.804 | 12.704→11.619 |
| seremban-medium | 61.214→55.228 | 245.785→218.259 | 486.257→435.749 |
| seremban-port-dickson | 105.148→96.225 | 415.835→376.696 | 827.790→759.902 |

Matrix distributions retain 20 observations per graph/variant/source count,
including extraction. All raw timings, p95 distributions, host load/vm_stat/thermal
and process memory records persist. These are repeats of a fixed query distribution,
not 400 independent sources or a production tail SLA. Frequency/scheduling were
not pinned. Preprocessing is measured separately, not selectively subtracted:

| Graph | Baseline native preprocessing range ms | Candidate range ms |
|---|---:|---:|
| seremban-small | 0.415–0.488 | 0.412–0.459 |
| seremban-medium | 10.398–11.241 | 10.353–11.703 |
| seremban-port-dickson | 19.517–23.990 | 19.627–24.904 |

## 7. Memory

Matched ordinary/all-aligned C++ allocation probes use the same ten recorded sources
and exported files. Counts include full query workspace/result destruction, exclude
reference checks and preprocessing, C malloc, metadata and OS allocations. Requested
bytes are cumulative traffic, not live memory. RSS covers the whole native-only
probe process, distinct from Python/GIS/geometry worker RSS in the machine summary.

| Graph | C++ requests A→B | Requested bytes A→B | Peak native RSS bytes A→B |
|---|---:|---:|---:|
| seremban-small | 255,299→215,350 | 31,997,120→30,708,264 | 8,536,064→8,536,064 |
| seremban-medium | 9,292,263→7,626,446 | 1,316,189,392→1,251,915,712 | 58,064,896→56,852,480 |
| seremban-port-dickson | 15,736,279→12,935,530 | 2,209,092,112→2,101,127,488 | 93,175,808→92,389,376 |

Corridor requests fell **17.8%**, bytes about **4.9%**. Within FindPivots,
2,979,934 requests became 179,185; membership allocations became just 20
(two arrays per query). Forest, vector and other-category requests are unchanged.
All counted ordinary query and tagged FindPivots allocations/deallocations balance.
This is scoped evidence, not a general leak detector; RSS can vary by allocator state.

Additional array payload is **8 bytes per transformed vertex**, plus fixed
container/guard metadata, when FindPivots first
runs: 28,416 / 568,480 / 963,424 bytes on the three graphs. It is retained through
workspace reset and dies with the workspace. It is not allocated by construction
or by pure level-zero queries. uint32 epochs avoid full-array clearing except wrap.

Memory retention is measured after local destruction, separately from global
peak tagged live bytes. A one-reachable-vertex small-road source `11957995110`
performed ten scoped allocations in both variants, but requested bytes increased
4,256→32,632; retained bytes at its FindPivots return increased 8→28,424. The result
still owns its eight-byte vector; the added 28,416 bytes belong to workspace marks.
A 69-reachable-vertex corridor source `11056440882` used five FindPivots calls;
scoped requests fell 123→45, but bytes increased 3,720→964,792 because of the
963,424-byte dense arrays. These extra diagnostics do not change primary queries.
Tiny-component initialization can therefore outweigh local hash savings; this is
an explicit tradeoff rather than a universal improvement claim.

## 8. Regressions

Small-road pooled p99 increased **5.22%** (2.955→3.110 ms), despite lower
p50/p95. One ordinary small-road source had slower observations in trials 0/1 and
faster observations in 2/3; its four-trial median still regressed. No cause for
those bursts was established. All slow/outlying observations remain present.
Five unique source medians regressed:

| Graph | Source | Reachable originals | Median µs A→B | Delta µs | Change |
|---|---:|---:|---:|---:|---:|
| seremban-small | 586359377 | 784 | 2710.229→2809.917 | +99.687 | +3.68% |
| seremban-small | 6535592704 | 2 | 28.583→31.688 | +3.104 | +10.86% |
| seremban-small | 7613411579 | 2 | 29.437→29.605 | +0.167 | +0.57% |
| seremban-small | 11957995111 | 7 | 35.291→36.438 | +1.147 | +3.25% |
| seremban-port-dickson | 11056440882 | 69 | 928.145→933.292 | +5.146 | +0.55% |

The combination is retained because all twelve paired graph medians improved
7.3–12.1%, p95 improved on all three graphs, meaningful medium/corridor p99 improved,
and allocation reduction is directly demonstrated. This meets Task 11's useful
improvement criterion while retaining the small-road tail/source tradeoffs. It is
not production-default promotion. Dense setup is a plausible contributor to tiny
source overhead; the experiment does not isolate its exact causal share from host
noise. No medium-road source median regressed.

## 9. Full Correctness Gates

Debug **16/16**, Release **16/16**, ASan/UBSan **15/15**, supported ThreadSanitizer
**15/15** passed. Native sanitizers used `ASAN_OPTIONS=detect_leaks=0` and
`UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`; no findings were reported.
Leak detection is disabled; executed tests do not prove all-program race freedom.
Final Release is byte-identical to the measured candidate.

Python/native/API/logistics/fixture **123 passed**, sanitizer-backed native/logistics/
road **89 passed**, frontend **5/5** and actual Chrome **156.0.8078.80** / Leaflet
passed. Existing 16 framework deprecation warnings are retained. Browser acceptance
used real map clicks, native capacity routes, exact original geometry/snapshot
identity and dataset changes; outbound tiles/fonts were blocked and cached Leaflet
used. Only the harness's own local server was stopped.

The unchanged full road gate passed **960,816 exact distances**, **643,571 original
directed reachable paths** and **317,245 unreachable comparisons**, checking original
edge IDs/direction/cost, geometry, reachability, capacities, mandatory stops, vehicle
returns and infeasible/API cases. Synthetic duration tests and real-data unsupported
time-window rejection remain covered. Road gate: 258.206 s;
incidental timings ran alongside correctness builds and are excluded from A/B.

Exact commands, exit codes, elapsed times, environments and complete output are in
the evidence root's native/application command records, A/B manifests, measurement
commands and build records. Individual diagnostic-build wall times were not
separately captured and are marked null; diagnostic clocks are retained instead.
No blocked/skipped gate counted as PASS, and no expectations or existing tests
were weakened. Initial probe setup failures remain visible: source-identity strings
needed symlink resolution; an inactive warmup dereferenced a null metrics pointer;
a formatted-source edit helper failed before modification. The guarded rebuilt
probes passed; failed/empty outputs are not measurements. Production code did not
cause the probe crash.

## 10. Remaining Bottlenecks

Fresh selected normal-binding sampling still shows comparison (567 top frames),
allocator free/malloc (269/233 plus 159 additional free), recursive run (223),
unsigned-key set insertion (159), frontier insertion (132) and arena allocation (81).
These are descriptive samples with callees/inlining, not exact latency fractions.

1. Recursive completed membership and remaining temporary allocation. The remaining
   hot unsigned-key set is run's complete_members; degree validation is outside the
   sampled steady query and optional frontier validation is disabled. Its lifetime
   spans recursive children, so one workspace epoch array would be unsafe.
2. Symbolic comparison and label creation/synchronization remain unchanged; a typical
   corridor query still creates roughly 925,086 labels. No speculative comparison
   cache or mutex removal was attempted.
3. BaseCase owned results, frontier maps and current/next vectors remain allocation
   costs. FindPivots forest maps are not a meaningful road target in this measured
   early-heavy workload. Performance on forest-heavy graphs is not established.

The equally warmed, interleaved separate reference replay checked every complete
vector. The candidate remains far slower than native Dijkstra:

| Graph | Current BMSSP p50 ms | Dijkstra p50 ms | Ratio |
|---|---:|---:|---:|
| seremban-small | 2.349 | 0.034 | 68.5× |
| seremban-medium | 54.992 | 0.782 | 70.3× |
| seremban-port-dickson | 94.522 | 1.371 | 68.9× |

No theoretical complexity improvement, universal binary64 theorem, production tail
SLA, cross-platform performance or exhaustive race/leak guarantee is claimed.
Existing road clipping/turn/duration/traffic limitations remain as documented.

## 11. Git Delivery

Scope is FindPivots, its dedicated scratch, required native tests/probe support and
documentation. No BaseCase, symbolic, degree/frontier algorithm, logistics/default,
frontend design or dataset change. Exclude binaries, caches, datasets and temporary
evidence from Git. Origin/main remains
`94f54b5206b46541dc12f5c7d8cb7fa019e4f877`. Commit/push/clean-tree proof is written
after delivery to `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task11-evidence/git-delivery.json`, avoiding a
self-referential tracked commit hash. No force push or main merge.

Persistent evidence: `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task11-evidence`. Archives, stage sources/binaries,
original/corrected/frozen probes, all raw measurements, reference replay, source
hashes, host/build metadata, road/browser proofs and the SHA-256 index are retained.
See [machine summary](pivot_performance_summary.json) and
[reproduction and lifetime details](pivot_performance_workflow.md).

## 12. Next Single Task

Measure and reduce **run's per-frame completed-membership allocation**, preserving
live parent/child isolation, completed-set disjointness and recursive boundaries.
Task 12 has not been started.
