# Task 12 completed-membership validation

## 1. Task 12 Verdict

**PASS.** All required correctness and application gates passed. The measured candidate is the adaptive per-frame exact membership. No engine replacement, hidden fallback, production-default change or complexity claim.

## 2. Baseline

Workspace `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer`, branch `codex/genuine-bmssp-engine`, origin `https://github.com/sallahuddin92/BMSSP_Logistics_optimizer.git`. Initial HEAD was clean and exactly `6019d2752345d977f568635e344fd8c959fbd328`. Read-only source extracted from git archive; archive SHA-256 `7de81d3d1960e5b7d2069aa922a0837ea90b6f4f6fc549a135fc92f1719a96b7`.

Release binding SHA-256 baseline `303274e560a65465ee75899d72c7d720fb2654b2290355198f03ac3f17d2e80b`; candidate `1b7e5d053c8b0307a9340b4dab2b684b4769a31ca8423f179420df9091254c4d`. Final Release binding is byte-identical to the adaptive binding used for A/B. Apple clang 21.0.0 (clang-2100.1.1.101), Apple M4 arm64, macOS 26.5.1, macOS SDK from matching CMake caches; CMake 4.3.3, C++20 Release `-O3 -DNDEBUG`, Python 3.11.15, pybind11 2.11.1. No dependency upgrade. Node 24.12.0, Chrome 156.0.8078.80.

| Graph | Snapshot SHA-256 | Transformed V/E |
| --- | --- | --- |
| seremban-small | ee772ad6f5e66e90556fccb44ab3ba83cfbe4ad287dc96d06a69dfdc4f167c11 | 3552/5307 |
| seremban-medium | 17b023d65bd0af6d1319a9fe4ed26c61eca795f09ca7ea17c98eec8df2b2c1d2 | 71060/106487 |
| seremban-port-dickson | 3a404e0196a500ec2320cffb600efe960ff4b50f4dbe0d91bc81c303411ac8df | 120428/180496 |

Exact original graph and query-file hashes are in the companion JSON and raw A/B build manifests. Existing snapshots, Task 8 100-source lists and Task 9 native exports were reused; no OSM download. Task 11 historical 2.335/54.580/94.445 ms medians, approximately 69–70x Dijkstra ratio and +5.22% small-road p99 regression remain recorded in the unchanged Task 11 report. Fresh paired measurements below are the Task 12 comparison.

## 3. Recursive Membership Profiling

Isolated canonical probes: ten unchanged exported sources per graph. Baseline/candidate receive identical calls, insert outcomes, contains counts, complete cardinalities and live depths. Counts include all run calls; membership constructions are non-base frames.

| Graph | run/base calls | Membership frames | Insert attempts / unique / duplicate | contains | Rehashes | Peak live calls / active members |
| --- | --- | --- | --- | --- | --- | --- |
| seremban-small | 11,484/11,127 | 357 | 74,023/62,781/11,242 | 18,754 | 2,203 | 4 / 3,440 |
| seremban-medium | 372,186/366,613 | 5,573 | 2,539,536/2,108,250/431,286 | 712,238 | 39,617 | 4 / 70,275 |
| seremban-port-dickson | 631,854/622,395 | 9,459 | 4,297,293/3,581,190/716,103 | 1,203,391 | 67,182 | 4 / 119,373 |

| Operation (corridor, 10 queries) | Calls | Allocations A → B | Requested bytes A → B | Instrumented operation seconds A → B |
| --- | --- | --- | --- | --- |
| membership | 4,297,293 inserts + 1,203,391 contains | 3,648,372 → 7,170 | 177,011,960 → 14,561,360 | 0.2850 → 0.1133 |
| owned | see raw frames | 81,156 → 81,156 | 86,871,144 → 86,871,144 | 0.0585 → 0.0575 |
| children | see raw frames | 688,174 → 688,174 | 14,634,960 → 14,634,960 | 0.0329 → 0.0303 |
| prepend | see raw frames | 431,470 → 431,470 | 52,636,768 → 52,636,768 | 0.0436 → 0.0306 |
| other | see raw frames | 6,347,955 → 6,347,955 | 1,438,798,448 → 1,438,798,448 | not separately clocked |
| base | see raw frames | 1,559,078 → 1,559,078 | 140,477,608 → 140,477,608 | not separately clocked |
| pivots | see raw frames | 179,185 → 179,185 | 141,275,880 → 141,275,880 | 0.0670 → 0.0653 |

Membership accounts for 28.2% of ordinary corridor query allocation requests. It is a material allocator cost, while other bookkeeping remains larger in bytes. The table separates result ownership, child frontiers and prepend temporaries; all their allocation counts/bytes match exactly. Instrumented clocks include observer overhead, are not normal latency, and exclude later set destruction. Frame setup includes FindPivots/frontier setup; teardown includes every local.

| Graph | Cardinality min / median / max | Frames ≤8 / ≤16 | Baseline setup / teardown / exclusive frame seconds |
| --- | --- | --- | --- |
| seremban-small | 4 / 64 / 3440 | 3 / 6 | 0.0058/0.0034/0.0391 |
| seremban-medium | 2 / 128 / 70275 | 2 / 3 | 0.1830/0.0934/1.0660 |
| seremban-port-dickson | 9 / 128 / 119373 | 0 / 2 | 0.3106/0.1725/1.8572 |

Raw probes retain each frame cardinality, bucket peak, setup/destruction clocks and bytes alive after frame exit. Inclusive recursive times overlap. Separate five-second macOS samples of ordinary binding queries show baseline hash emplacement (139 flat samples), run (193), comparison (612) and allocator work. Candidate comparison (680), frontier insertion (127), run (191), relaxation (104) and label allocation (102) remain visible. Sampling is diagnostic, with inlining/deduplicated-symbol uncertainty; it does not establish percentages of membership CPU.

## 4. Implementation

`native/include/bmssp/detail/completed_membership.hpp` adds stable separately allocated slots behind depth-indexed unique_ptr handles. RAII leases enforce one active state per slot. Growing handles cannot invalidate live parent leases; siblings reuse released slots with a fresh epoch. A parent stays active across child recursion. Returned complete vectors remain independently owned.

Candidate A: lazy dense epochs. Candidate B: eight inline exact keys, then a lazily allocated directory of 512-index uint32 epoch pages (2 KiB/page). Both are deterministic and exact; graph size is checked without a cap. Inline promotion switches only after successful allocation/insertion; failure leaves inline answers intact. Exceptions release leases. Epoch wrap clears allocated pages, and independent workspaces share no mutable membership. Copying a workspace starts with empty frame caches, preserving its public copy capability. Moving/mutating one active workspace concurrently remains unsupported.

Production run diff is one acquisition and two insert-return adaptations. FindPivots, BaseCase, degree reduction, k/t, frontier semantics, symbolic order, equality-valid relaxation and Dijkstra remain byte-identical/unchanged. Test-only frozen Task 11 files and generated test hooks are outside production binaries; `frame_probe_build.py`, `frame_measurement.hpp` and `frame_probe.cpp` are optional executable-only probes. See [ownership/reproduction workflow](completed_membership_workflow.md).

Both candidates passed 17/17 Release tests and two separate exploratory latency trials, with frozen state/allocation comparison. Dense was slightly faster on large graphs (corridor medians 79.069/78.841 ms versus adaptive 79.562/79.338 ms; baseline 93.576/93.459 ms). Adaptive was selected for lower measured tiny-component fixed cost and comparable large-graph results. Both source/binary stages and every rejected measurement are retained externally.

## 5. Algorithm Equivalence

Final focused test: **2,309 frozen recursive traces and 5,071 intermediate membership states**, with exact completion order, B′ boundaries, before/after symbolic vertex/edge paths, seeded equality-valid states, frontiers and every deterministic work counter. Independent Bellman-Ford and bounded-contract oracles supplement the frozen implementation. Full road A/B checks distance-vector, selected directed-path and 1/4/8 matrix fingerprints plus work counts on all 100 sources in every trial.

Tests exercise active parents/children, repeated siblings, 70 stable slots, nested recursion, partial/full bounds, zero cycles, parallel edges, large IDs, disconnected/tiny components, epoch wrap, slot/page allocation failure, nested exception unwind/reset, copies/moves and concurrent independent workspaces. Defined fault injection must catch each intended overlap, stale-frontier, no-progress and nonmonotone-boundary error message, then reset and complete successfully. Assertions remain active in Release.

## 6. Controlled Performance

Fresh AB/BA/BA/AB process trials, reversed graph/preparation orders, eight identical warmups, 400 retained observations per graph/variant, no profiling/interception or concurrent heavy jobs. Nearest-rank pooled milliseconds; improvements are latency reductions. Every source/outlier/failure is retained.

| Graph | Task 11 p50/p95/p99 ms | Task 12 p50/p95/p99 ms | p50 / p99 reduction | Four trial p50 reductions |
| --- | --- | --- | --- | --- |
| seremban-small | 2.333/2.478/2.559 | 1.950/2.069/2.128 | 16.39% / 16.82% | 16.20%, 16.32%, 16.45%, 16.30% |
| seremban-medium | 54.646/56.329/57.257 | 46.629/48.173/49.467 | 14.67% / 13.61% | 14.03%, 15.03%, 14.94%, 14.55% |
| seremban-port-dickson | 92.971/95.923/97.859 | 79.594/81.894/83.580 | 14.39% / 14.59% | 14.58%, 14.28%, 13.70%, 14.93% |

| Graph | 1-source matrix p50 A → B ms | 4-source | 8-source | BMSSP / native Dijkstra median ratio |
| --- | --- | --- | --- | --- |
| seremban-small | 2.295 → 1.942 | 4.741 → 3.993 | 11.472 → 9.655 | 55.90x |
| seremban-medium | 54.591 → 47.337 | 217.524 → 186.579 | 438.146 → 372.355 | 59.71x |
| seremban-port-dickson | 94.554 → 80.202 | 377.292 → 321.088 | 746.966 → 638.847 | 58.22x |

Each matrix size has 20 retained observations/variant/graph; companion JSON includes p95 (p99 withheld for this small count). Native Dijkstra ratios use a separate interleaved reference replay, rather than dividing unrelated historic runs. Preprocessing is unchanged code and is measured separately:

| Graph | Preprocessing A range ms | Preprocessing B range ms |
| --- | --- | --- |
| seremban-small | 0.405–0.422 | 0.407–0.448 |
| seremban-medium | 10.470–10.873 | 10.502–11.030 |
| seremban-port-dickson | 18.243–21.162 | 17.949–19.225 |

Raw manifests retain host CPU/load, VM and thermal snapshots. No thermal/performance warning was reported. Load and allocator residency vary; evidence supports these measured workloads, not a universal speedup. Cold warmup observations remain separate in raw files; this is a warmed-query comparison, not a cold-start performance guarantee.

## 7. Memory

| Graph (10 queries) | Total C++ requests A → B | Requested bytes A → B | Peak native RSS A → B MiB | Peak active / retained membership bytes B |
| --- | --- | --- | --- | --- |
| seremban-small | 215,350 → 150,612 | 30,708,264 → 27,966,680 | 8.14 → 8.14 | 43,608 / 43,640 |
| seremban-medium | 7,626,446 → 5,482,839 | 1,251,915,712 → 1,159,285,248 | 51.64 → 53.56 | 857,784 / 857,816 |
| seremban-port-dickson | 12,935,530 → 9,294,328 | 2,101,127,488 → 1,938,676,888 | 86.12 → 85.27 | 1,456,080 / 1,456,112 |

Ordinary allocation-probe RSS is native process peak; profiler-registry RSS is excluded. Python A/B RSS (approximately 0.9–1.0 GB, including Python/graph and process high-water effects) is retained separately, not attributed to marker scratch. Requested bytes exclude allocator rounding/C malloc/OS mappings. All tagged allocations disappear at public solve exit. Low-level workspace caches survive reset and can retain prior large-query pages; public solve owns/destroys its workspace. Allocator RSS may retain freed pages.

## 8. Regressions

Small-road pooled p99 improves 16.82% (2.559 → 2.128 ms). All twelve graph/trial medians improve. A medium trial p99 rose from 57.621 to 61.977 ms; this outlier is retained and pooled medium p99 improves 13.61%. Tail improvements are not uniform in every trial. Source medians pooled over their four observations regress as follows:

| Graph / source | Reachable original vertices | A → B µs | Delta µs / percent |
| --- | --- | --- | --- |
| seremban-small / 5735886101 | 1 | 26.875 → 27.000 | 0.124 / 0.463% |
| seremban-small / 11957995111 | 7 | 33.625 → 34.646 | 1.021 / 3.036% |
| seremban-port-dickson / 3069838223 | 19 | 817.500 → 821.688 | 4.188 / 0.512% |

Tiny extra probes: one-vertex inline frame uses 152 retained bytes versus 14,296 dense; two-original-vertex cases use 464 retained bytes versus 42,896 dense. Seven original reachable vertices can expand beyond eight transformed keys, promoting pages: 19,064 retained bytes versus 42,896 dense. Baseline local hash allocations are 40/456/2,208 requested bytes in those cases; adaptive still adds fixed slot/page bytes. Dense is retained as an experiment, not selected as a universal winner. Medium native RSS rises 1.92 MiB; corridor falls 0.86 MiB. No peak-memory improvement is claimed for every graph.

## 9. Full Correctness

| Gate | Result | Elapsed seconds |
| --- | --- | --- |
| release-ctest | 17/17 | 7.735 |
| debug-ctest | 17/17 | 20.879 |
| asan-ctest | 16/16 | 61.208 |
| tsan-ctest | 16/16 | 193.357 |
| python-integration | 123 passed | 12.463 |
| frontend | 5 passed | 0.073 |
| real-roads | 3 regions PASS | 265.946 |
| chrome-browser | Chrome/Leaflet PASS | 7.571 |
| sanitized-python | 89 passed | 2.780 |

Road oracle totals: **960,816 exact binary64 distances, 643,571 original directed paths, 317,245 unreachable comparisons**. One-way/asymmetry, parallel-edge identity, path cost, mandatory stops, capacities, unavailable routes, API failures and road geometry retain their existing acceptance checks. Actual Chrome uses cached Leaflet with basemap tiles intentionally blocked offline.

Separate verdicts: recursive integrity PASS; frame ownership/memory safety PASS; membership equivalence PASS; allocation improvement PASS; native latency PASS; peak/retained memory PASS with disclosed workload-dependent tradeoffs; small-road p99 PASS; road correctness PASS; application regressions PASS.

Exact commands, exit codes, elapsed seconds and logs are retained externally in `native-suite-commands.json`, `application-commands.json`, stage/probe command records and their logs. Standard gates include BaseCase/FindPivots/frontier/symbolic/oracle and frozen recursion tests. No failed expectations were changed.

The first isolated profiler build failed because its generated driver had unmatched braces; a subsequent generator correction failed with a Python NameError. Both attempts/logs remain archived; corrected v3 and all canonical final probes succeeded. These failed development attempts are excluded from measurements. ASan uses the established macOS loader helper; `detect_leaks=0` is explicit, so this is not LeakSanitizer coverage.

## 10. Remaining Bottlenecks

1. Symbolic comparison/label handling: compare is the largest identifiable candidate algorithm flat sample (680); label extension/allocation and relaxation remain prominent.
2. Other recursive bookkeeping/frontier structures: 6,347,955 tagged requests / 1,438,798,448 requested bytes on the corridor, with frontier insert/selection/pull visible in normal samples.
3. BaseCase and child/prepend/result vectors: substantial remaining requests; their counts are unchanged. Membership is now 7,170 requests and is no longer the allocation leader.

Sampling and category allocation counts rank different aspects of cost; they do not establish that any one module alone explains the remaining 56–60x gap to native Dijkstra.

## 11. Git Delivery

All gates passed; the verified change is committed/pushed on the development branch. See external `git-delivery.json` for exact delivery SHA and clean-tree verification. Baseline/final source archives, stages, binaries, probes, trials, failed attempts, commands/toolchain, hashes and reports are preserved outside Git at `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task12-evidence`. Compact JSON/report/workflow belong in Git; binaries/cache/roads do not. Main remains `94f54b5206b46541dc12f5c7d8cb7fa019e4f877`. Final commit/remote verification is recorded externally to avoid a self-referential commit hash.

## 12. Next Single Task

Profile symbolic label comparison paths and allocation ownership in isolation, then select one measured optimization while retaining exact ordering. No Task 13 implementation begins here.

All added source retains Apache-2.0 notices. Frozen tests derive from this repository’s Task 11 code; no external reference implementation code was imported.
