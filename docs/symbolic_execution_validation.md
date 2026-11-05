# Task 13 symbolic-label execution validation

## 1. Task 13 Verdict

**PASS.** All required native, independent-oracle, sanitizer, road and application gates passed. Candidate A is selected based on reproducible median improvement and materially lower arena retention. Corridor pooled tails remain a measured tradeoff; no universal latency, complexity, or production-default promotion is claimed.

## 2. Verified Baseline

Clean Task 12 commit `71ddb767437df3df602d1ba81471c13540199996` on `codex/genuine-bmssp-engine`, origin `https://github.com/sallahuddin92/BMSSP_Logistics_optimizer.git`. Workspace `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer`. Immutable git archive SHA-256 `7c2e59572bc961f3e657e6a44a84a00423f836ca53c3024ec2579efc670a48c9`; extracted files read-only outside Git. Fresh baseline Release CTest 17/17.

Baseline binding SHA-256 `1b7e5d053c8b0307a9340b4dab2b684b4769a31ca8423f179420df9091254c4d`; candidate/final Release `740c5a3c41217290895975024bba46562ee68bffc48c78e8e3e174948f8ed241`. Independent baseline build reproduces the Task 12 binding hash. Candidate and final-test bindings are byte-identical. Apple M4 arm64, macOS 26.5.1, Apple clang 21.0.0 (clang-2100.1.1.101), CMake 4.3.3, Release C++20 `-O3 -DNDEBUG`, Python 3.11.15, pybind11 2.11.1. SDK/flags/dependencies and hashes are retained in raw toolchain/CMake manifests. No dependency upgrades or new datasets.

| Graph | Snapshot SHA-256 | Transformed V/E |
| --- | --- | --- |
| seremban-small | ee772ad6f5e66e90556fccb44ab3ba83cfbe4ad287dc96d06a69dfdc4f167c11 | 3552/5307 |
| seremban-medium | 17b023d65bd0af6d1319a9fe4ed26c61eca795f09ca7ea17c98eec8df2b2c1d2 | 71060/106487 |
| seremban-port-dickson | 3a404e0196a500ec2320cffb600efe960ff4b50f4dbe0d91bc81c303411ac8df | 120428/180496 |

Exact original graph/query bytes and 100-source lists are unchanged and verified in every process preparation. Historical Task 12 1.950/46.629/79.594 ms medians and 56–60x Dijkstra gap remain historical observations; comparisons below use fresh paired measurements.

## 3. Symbolic Comparison Profile

| Category, corridor ten queries | Calls | Chain steps | CPU evidence |
| --- | --- | --- | --- |
| Pointer identity | 3,638,629 | 0 | fast return |
| Finite/infinite | 11,144,278 | 0 | fast return |
| Different scalar distance | 37,339,151 | 0 | dominant terminal class |
| Different hops after distance tie | 3,866,469 | 0 | scalar return |
| Equal distance/hops (subtotal) | 4,773,341 | 4,773,341 vertex | includes subsequent outcomes |
| Vertex-path difference | 669 | included above | exact reversed vertices |
| Vertex-equivalent edge pass (subtotal) | 4,772,672 | 4,772,672 edge | includes subsequent outcomes |
| Parallel-edge difference | 0 | included above | zero observed on this road probe |
| Fully equivalent | 4,772,672 | included above | equality is accepted |

Total **60,761,868 comparisons**, maximum combined vertex/edge walk **2** node-pair visits. The two subtotals overlap; only terminal classes sum to total calls. All thirty baseline/candidate probe queries match categories, individual chain steps, maximum walk and outcomes exactly. Long independent chains are separately covered in tests, not inferred from short road walks.

Separate ordinary five-second binding samples show comparison as the largest identifiable algorithm flat frame: 711 baseline samples and 745 candidate `compare_nodes` samples. Baseline extension (102) and mutex lock (78) are visible. Candidate run (196), frontier insertion (134), relax (116), BaseCase (104) and allocation/free work remain. Fixed-duration samples execute different query counts; these counts are not per-query speed ratios or exact attribution of inlined work. Raw call trees retain arena work.

## 4. Label Ownership and Materialization

| Graph, ten queries | Attempts | Strict updates | Equality-valid | Rejected / bound subset | Arena nodes A → B | Final current roots / ancestry |
| --- | --- | --- | --- | --- | --- | --- |
| seremban-small | 154,648 | 22,078 | 77,157 | 55,413 / 14,657 | 154,658 → 22,088 | 20,927 / 20,927 |
| seremban-medium | 5,422,948 | 756,868 | 2,818,079 | 1,848,001 / 510,741 | 5,422,958 → 756,878 | 702,750 / 702,750 |
| seremban-port-dickson | 9,204,053 | 1,283,608 | 4,758,669 | 3,161,776 / 864,344 | 9,204,063 → 1,283,618 | 1,193,730 / 1,193,730 |

Corridor arena publications decrease **86.05%**. The original arena retains every published node through shared ownership until teardown, including obsolete/rejected candidates; final selected ancestry uses 1,193,730 nodes in both variants. Published nodes outside final ancestry fall from 8,010,333 to 89,888. This is the measured retention problem, rather than deep parent-chain comparison.

| Corridor ownership/clock | Baseline | Candidate |
| --- | --- | --- |
| copies | 21,207,476 | 21,207,476 |
| assigns | 3,310,881 | 3,310,881 |
| moves | 28,786,289 | 30,069,897 |
| destroys | 62,550,878 | 55,914,041 |
| arena_copies | 9,204,059 | 1,283,614 |
| locks | 9,204,063 | 1,283,618 |
| contended | 0 | 0 |
| allocation_seconds | 0.504958000 s | 0.070164890 s |
| lock_seconds | 0.151452600 s | 0.020938750 s |
| teardown_seconds | 0.000268250 s | 0.000048083 s |
| label_destruction_seconds | 0.953312900 s | 0.847164000 s |

Copies/assignments are high-level SymbolicLabel operations, and explicit arena copies are separately observed, not a count of all atomic instructions. Zero diagnostic try-lock misses does not prove absence of contention in arbitrary shared-arena workloads. Allocation clocks include lock time; label destruction can include arena teardown. Do not sum overlapping clocks. Final roots/ancestry are a census, not peak live frontier ownership.

## 5. Selected Implementation

Selected Candidate A only. `symbolic_label.hpp/.cpp` add private checked extension construction and arena publication, and factor the original comparator into a pointer-based helper with an identical decision body. `bmssp_bounded.cpp::relax` compares the temporary full node against the bound and destination, publishes only a strict improvement, and preserves equality-valid success. Public `extend` remains eager and fully functional. No comparison cache, slab/mutex redesign or independent Candidate B/C optimization was bundled.

Both distance addition and hop addition are checked in their original order before rejection. Local node fields are identical to a fully materialized extension. The source owns immutable ancestry during comparison; publication copies its values into stable arena storage, with the already-owned parent pointer. No temporary address escapes. Destination assignment occurs only after publication succeeds. Saved boundaries and public shared-arena extensions keep their original lifetime.

Legacy `label_nodes_created` remains the eager-equivalent logical root/extension-candidate work count. New `label_nodes_materialized` counts stable arena publications: successful queries satisfy `materialized = label_updates + 1 <= created`. A failed accepted allocation rolls back the legacy increment and preserves the destination. Rejected/equality-only attempts intentionally stop requiring unused arena allocation; public extend and accepted-growth failures remain tested.

Bindings expose the new counter. A/B retains it separately and excludes only this new storage counter from cross-version algorithm-work equality, with explicit correspondence assertions. The opt-in allocation clock counts actual materialization; its Python contract now checks that counter, strict publications and identical before/profile/after work. This explicitly separates logical work from allocation rather than weakening path or algorithm assertions. `allocation_probe` also exposes both counts.

The fully separate diagnostic builder rebuilds every source against consistent copied headers. Its support header/driver are executable-only; production libraries and latency bindings contain no hooks or replacement allocator. See [ownership and reproduction workflow](symbolic_execution_workflow.md).

## 6. Algorithm Equivalence

Frozen Task 12 public symbolic implementation in a separate type namespace checks full ordering against 91,204 label pairs plus independent vector ordering, long chains and parallel-edge refinement. Frozen eager Task 12 bounded code compares **345,378 labels and 2,841 bounded traces**, full vertices/edges, before/after labels, frontiers, completion sequences, B′ and every legacy deterministic counter. Existing Task 10/11 frozen BaseCase, FindPivots and recursive-membership tests remain intact. Thirty random graphs and independent Bellman-Ford bounded contracts plus native Dijkstra supplement frozen agreement.

Borrowed candidates exercise 1,199-hop pointer-distinct equal ancestry and oldest-edge refinement, zero cycles, equal costs/hops, strict bounds, disconnected/tiny graphs, large IDs, finite near-limit binary64 arithmetic, invalid operands, overflow/hop overflow before cheap rejection, out-of-domain edges, full slabs, allocation failure rollback, exception/reset, saved snapshots and concurrent independent workspaces/shared public arenas. All assertions remain active in Release.

Source verification confirms BaseCase, FindPivots, recursive run and all other engine source files are byte-identical, as are arena/slab/locking definitions. The comparator body is identical after pointer-parameter substitution. Original-edge reconstruction, parameters, ordering, weights, Dijkstra and production defaults are unchanged.

## 7. Controlled Performance

Two exploratory paired trials first improved all six graph medians; one corridor exploratory p99 worsened and is retained. The first final four-trial batch showed a corridor tail regression, prompting four additional trials with unchanged binaries and read-only CPU-process snapshots outside timed jobs. Both batches and every sample remain included. No build/test/sampling/interception overlapped timed jobs. Warmup is eight unchanged sources per process/job; graph/preparation order reverses, with AB/BA/BA/AB in each batch.

**Initial final batch: 400 observations/variant/graph**

| Graph | Task 12 p50/p95/p99 ms | Task 13 p50/p95/p99 ms | p50 / p99 reduction |
| --- | --- | --- | --- |
| seremban-small | 1.955/2.111/2.241 | 1.773/1.917/1.996 | 9.29% / 10.95% |
| seremban-medium | 47.614/64.109/71.226 | 42.037/45.648/60.844 | 11.71% / 14.58% |
| seremban-port-dickson | 80.574/94.516/106.920 | 73.734/102.280/117.270 | 8.49% / -9.68% |

**Replication: 400 observations/variant/graph**

| Graph | Task 12 p50/p95/p99 ms | Task 13 p50/p95/p99 ms | p50 / p99 reduction |
| --- | --- | --- | --- |
| seremban-small | 1.959/2.310/2.462 | 1.782/1.914/1.997 | 9.05% / 18.87% |
| seremban-medium | 46.834/49.709/55.146 | 42.679/45.434/46.839 | 8.87% / 15.06% |
| seremban-port-dickson | 80.270/84.273/89.195 | 72.697/77.131/84.718 | 9.43% / 5.02% |

**All eight trials: 800 observations/variant/graph**

| Graph | Task 12 p50/p95/p99 ms | Task 13 p50/p95/p99 ms | p50 / p99 reduction |
| --- | --- | --- | --- |
| seremban-small | 1.956/2.177/2.411 | 1.779/1.917/1.997 | 9.03% / 17.16% |
| seremban-medium | 47.143/60.542/69.762 | 42.349/45.505/52.013 | 10.17% / 25.44% |
| seremban-port-dickson | 80.398/89.529/102.612 | 72.979/97.290/109.496 | 9.23% / -6.71% |

All eight individual trials, with the initial batch followed by replication:

| Graph / batch / trial | Task 12 p50/p95/p99 ms | Task 13 p50/p95/p99 ms | Median reduction |
| --- | --- | --- | --- |
| seremban-small / initial / 0 | 1.970/2.121/2.216 | 1.764/1.872/1.934 | 10.45% |
| seremban-small / initial / 1 | 1.957/2.062/2.111 | 1.798/1.945/2.001 | 8.14% |
| seremban-small / initial / 2 | 1.926/2.072/2.113 | 1.766/1.886/1.961 | 8.34% |
| seremban-small / initial / 3 | 1.964/2.151/2.300 | 1.771/1.923/2.092 | 9.82% |
| seremban-small / replication / 0 | 2.036/2.403/2.504 | 1.773/1.877/1.951 | 12.91% |
| seremban-small / replication / 1 | 1.924/2.080/2.149 | 1.781/1.931/1.958 | 7.44% |
| seremban-small / replication / 2 | 1.929/2.057/2.120 | 1.789/1.904/1.944 | 7.26% |
| seremban-small / replication / 3 | 1.964/2.391/2.451 | 1.785/1.934/2.000 | 9.13% |
| seremban-medium / initial / 0 | 46.854/51.183/56.153 | 41.663/43.550/44.163 | 11.08% |
| seremban-medium / initial / 1 | 46.716/50.537/52.036 | 41.969/43.622/44.224 | 10.16% |
| seremban-medium / initial / 2 | 57.605/70.010/75.700 | 41.976/52.013/74.360 | 27.13% |
| seremban-medium / initial / 3 | 47.707/50.506/51.056 | 42.736/47.329/51.894 | 10.42% |
| seremban-medium / replication / 0 | 47.000/48.777/50.022 | 42.194/43.503/44.438 | 10.23% |
| seremban-medium / replication / 1 | 46.714/52.082/57.085 | 43.440/46.263/53.556 | 7.01% |
| seremban-medium / replication / 2 | 46.777/49.954/54.047 | 43.070/45.627/46.523 | 7.92% |
| seremban-medium / replication / 3 | 46.856/48.482/49.005 | 42.545/44.800/45.505 | 9.20% |
| seremban-port-dickson / initial / 0 | 80.651/90.799/102.257 | 73.917/80.459/86.245 | 8.35% |
| seremban-port-dickson / initial / 1 | 79.426/81.347/82.474 | 71.965/78.206/86.269 | 9.39% |
| seremban-port-dickson / initial / 2 | 80.465/96.687/118.057 | 94.890/112.512/121.435 | -17.93% |
| seremban-port-dickson / initial / 3 | 85.748/95.882/106.920 | 72.916/83.854/98.091 | 14.97% |
| seremban-port-dickson / replication / 0 | 80.663/87.660/91.159 | 72.971/79.422/91.427 | 9.54% |
| seremban-port-dickson / replication / 1 | 79.913/82.650/84.050 | 73.063/79.159/86.675 | 8.57% |
| seremban-port-dickson / replication / 2 | 80.688/84.085/85.734 | 72.330/74.799/76.046 | 10.36% |
| seremban-port-dickson / replication / 3 | 80.142/82.374/84.122 | 72.475/74.618/84.128 | 9.57% |

| Graph | 1-source matrix p50 A → B ms | 4-source | 8-source | Separate native Dijkstra ratio |
| --- | --- | --- | --- | --- |
| seremban-small | 1.947 → 1.747 | 3.982 → 3.618 | 9.705 → 8.781 | 50.92x |
| seremban-medium | 48.406 → 43.268 | 188.879 → 170.945 | 375.147 → 342.190 | 53.70x |
| seremban-port-dickson | 82.362 → 76.868 | 330.445 → 299.204 | 649.756 → 588.050 | 52.84x |

Matrices retain forty observations at each size/variant/graph across both batches; companion JSON contains p95 (p99 withheld for this small count). Full distance-vector, selected directed-path, matrix fingerprints and legacy work match on every source in every trial. Separate reference replay interleaves BMSSP and native Dijkstra; no historical denominators are used.

| Graph | Preprocessing A range ms | Preprocessing B range ms | Diagnostic/ordinary elapsed estimate A / B |
| --- | --- | --- | --- |
| seremban-small | 0.401–0.436 | 0.405–0.484 | 5.40x / 4.68x |
| seremban-medium | 10.526–13.119 | 10.356–11.017 | 4.41x / 3.75x |
| seremban-port-dickson | 17.756–19.865 | 17.521–22.278 | 4.45x / 3.74x |

Diagnostic elapsed includes clocked ownership operations, allocation tallying, census and teardown; ordinary native query clocks have a narrower scope and run separately. The ratio is an overhead estimate, not an A/B speed claim. Instrumented clocks never substitute for normal latency. Raw warmups remain separately available; this is warmed-query evidence, not a cold-start guarantee. Host load/VM/thermal snapshots persist. No thermal warning was reported; variable host activity is observed but does not establish the cause of individual outliers.

## 8. Memory

| Graph, ten native queries | C++ requests A → B | Requested bytes A → B | Peak native RSS A → B MiB | Slab slots A → B | Slab utilization A → B |
| --- | --- | --- | --- | --- | --- |
| seremban-small | 150,612 → 150,561 | 27,966,680 → 20,801,880 | 8.14 → 8.14 | 174,208 → 24,960 | 88.78% → 88.49% |
| seremban-medium | 5,482,839 → 5,481,670 | 1,159,285,248 → 935,312,896 | 53.56 → 29.19 | 5,443,264 → 777,920 | 99.63% → 97.30% |
| seremban-port-dickson | 9,294,328 → 9,292,376 | 1,938,676,888 → 1,558,799,512 | 87.28 → 49.11 | 9,223,872 → 1,310,400 | 99.79% → 97.96% |

LabelNode remains 48 bytes; corridor cumulative slab payload falls from 442,745,856 to 62,899,200 bytes. Slab policy is unchanged, and slightly lower utilization is expected at the smaller total workload. Arena publications fall sharply while ordinary allocation-request counts barely change because slabs amortized nodes already and recursive containers remain the request leader. Total requested bytes and medium/corridor native RSS fall substantially; small native RSS is unchanged.

No new persistent cache or arena-retention policy is added. The temporary node has stack lifetime; accepted nodes retain their original shared arena. Obsolete accepted versions remain until arena destruction, but rejected/equality-only nodes no longer occupy slabs. Requested bytes exclude malloc/allocator rounding/OS mappings. Python process high-water/resident measurements remain separate from native RSS and are retained in raw trials/JSON. No peak-memory guarantee is inferred for arbitrary graphs.

## 9. Regressions

Twenty-three of twenty-four final graph/trial medians improve. Initial corridor trial 2 median worsens 17.93%; the full initial corridor p99 worsens 9.68%. Replication improves every median and corridor p99 by 5.02%, but **all-eight pooled corridor p95/p99 still worsen 8.67%/6.71%**. These outliers and the entire original batch remain included. The p99 regression is a retained latency tradeoff, not erased by successful replication or attributed conclusively to host activity. Small/medium pooled p99 improve 17.16%/25.44%. Acceptance is based on repeatable useful medians and lower retention with transparent tails, not universal tail improvement.

**Initial batch source-median regressions**

| Graph / source | Reachable | Task 12 → Task 13 µs | Delta µs / percent |
| --- | --- | --- | --- |
| seremban-small / 5735886101 | 1 | 27.437505 → 29.208495 | 1.770990 / 6.454632% |
| seremban-port-dickson / 3069838223 | 19 | 829.229000 → 862.895999 | 33.666998 / 4.060036% |
| seremban-port-dickson / 4866711343 | 24395 | 80780.436998 → 84871.082996 | 4090.645998 / 5.063907% |
| seremban-port-dickson / 6138513271 | 24395 | 80719.541504 → 84356.166495 | 3636.624991 / 4.505260% |
| seremban-port-dickson / 11056440882 | 69 | 964.104001 → 968.000000 | 3.895999 / 0.404106% |
| seremban-port-dickson / 3302605187 | 24395 | 81055.645504 → 83123.562494 | 2067.916990 / 2.551231% |

**Replication source-median regressions**

| Graph / source | Reachable | Task 12 → Task 13 µs | Delta µs / percent |
| --- | --- | --- | --- |
| seremban-small / 7610550429 | 4 | 30.166499 → 30.166506 | 0.000007 / 0.000024% |
| seremban-small / 11957995111 | 7 | 34.500001 → 36.125006 | 1.625005 / 4.710160% |
| seremban-small / 5735886101 | 1 | 28.687500 → 31.458505 | 2.771005 / 9.659276% |

**All-eight source-median regressions**

| Graph / source | Reachable | Task 12 → Task 13 µs | Delta µs / percent |
| --- | --- | --- | --- |
| seremban-small / 5735886101 | 1 | 28.271003 → 29.208495 | 0.937493 / 3.316092% |

The remaining pooled one-reachable-original-vertex source regresses 0.937 µs/3.32% in binding wall time; its internal native-query median is 23.563 → 23.458 µs. Binding/teardown measurement scope and the additional diagnostic dictionary field are possible contributors, not a demonstrated causal explanation. The replication 4-vertex regression is roughly 7 picoseconds at this clock resolution and is retained without claiming significance. Rejected candidates intentionally cease causing unused-slab bad_alloc; accepted/public-extension error contracts and arithmetic error order remain verified.

## 10. Full Correctness

| Gate | Result | Elapsed seconds |
| --- | --- | --- |
| release-ctest | 18/18 | 2.549 |
| debug-ctest | 18/18 | 29.187 |
| asan-ctest | 17/17 | 90.391 |
| tsan-ctest | 17/17 | 243.513 |
| python-integration | 123 passed | 12.881 |
| frontend | 5 passed | 0.133 |
| real-roads | 3 regions PASS | 331.700 |
| chrome-browser | Actual Chrome/Leaflet PASS | 9.021 |
| sanitized-python | 89 passed | 4.030 |

Road totals: **960,816 exact binary64 distances, 643,571 original directed paths, 317,245 unreachable comparisons**. One-way/asymmetry, original parallel-edge identities, exact path costs, mandatory stops, capacities, depot returns, unreachable routing, API invalid requests, unsupported duration constraints and geometry all retain established checks. Actual Chrome 156 uses cached Leaflet and deliberately blocked offline basemap tiles.

Release/Debug include the Python binding smoke target. Sanitizer CTest suites contain the seventeen supported native tests; ASan Python integration runs separately through the macOS loader helper, while TSan targets native threads.

Exact argv/cwd/exit/timing records are retained in `native-suite-commands.json`, `application-commands.json`, stage/build/probe records and raw logs. The shipped diagnostic builder independently reproduces all sixty diagnostic-query counter records plus thirty final ordinary allocation queries; its verification clocks run during correctness gates and are excluded from performance evidence.


Two early diagnostic-builder attempts failed (copied read-only header permissions; duplicate allocator definitions). Both logs/outputs are preserved, then corrected independent v3 and canonical probes succeeded. These failed development attempts are not performance samples. The original archive and normal binaries were unaffected. Supported macOS ASan helper explicitly uses `detect_leaks=0`; no LeakSanitizer coverage is claimed.

## 11. Remaining Bottlenecks

1. Scalar symbolic comparison and disabled-profile/call overhead: 60.76 million comparisons in ten corridor queries, with 37.34 million different-distance exits and short road ancestry walks; comparison remains the largest identifiable sampled algorithm frame.
2. Frontier/recursive bookkeeping and allocation/free work: visible insert/pool/hash-map/run frames remain, with about 9.29 million ordinary native requests despite lower label storage.
3. BaseCase/relaxation and immutable ownership operations: still visible after eliminating unnecessary publication. Saved-label semantics and shared-arena synchronization remain necessary.

These are measurements of different cost aspects, not additive CPU percentages. No comparison caching is justified by the observed short road walks, and no claim is made that one module explains the remaining 51–54x native Dijkstra gap.

## 12. Git Delivery

All gates and scope checks passed. Commit/push verification is recorded in external `git-delivery.json` with exact local/remote SHA and clean-tree state. Source archives, binaries, stages, raw experiments, failed probe attempts, commands, test/browser/road artifacts and evidence hashes are preserved outside Git at `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task13-evidence`. Only source, tests, diagnostic tooling and compact documentation are committed. Main remains `94f54b5206b46541dc12f5c7d8cb7fa019e4f877`; exact local/remote delivery SHA and clean-tree verification are recorded externally to avoid a self-referential commit hash.

Frozen files retain original Apache-2.0 notices; no external reference-implementation code is imported.

## 13. Next Single Task

Measure the scalar-only comparison path and disabled-profiling overhead, then select one exact fast path with unchanged symbolic ties. Do not implement caching or begin Task 14 here.
