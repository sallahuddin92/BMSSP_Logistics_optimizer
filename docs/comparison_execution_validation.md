# Task 14 scalar comparison and disabled-profiling validation

## 1. Task 14 Verdict

**PASS.** All required correctness/application gates passed. The selected optimization has repeatable modest median gains and exact semantics; primary medium/corridor p99 regressions remain an explicit tradeoff. Replication and temporal pairing improve tails but do not erase initial observations or establish their cause. No universal performance guarantee is claimed.

| Acceptance dimension | Verdict |
| --- | --- |
| symbolic_equivalence | PASS |
| profiling_correctness | PASS |
| algorithm_integrity | PASS |
| whole_query_performance | PASS: modest repeatable medians, supported by controls and temporal pairing |
| tail_latency | MIXED: primary medium/corridor p99 +10.74%/+21.68%; replication and temporal-pairing p99 improve; initial regressions retained, causal explanation unresolved |
| memory | PASS: heap requests/bytes/materialization unchanged; observed RSS variability disclosed |
| real_roads | PASS |
| application_integration | PASS |
| reproducibility | PASS: all valid/rejected/protocol-failed experiments preserved |
| production_scope | PASS: symbolic_label.cpp profiling dispatch/layout only |


## 2. Verified Baseline

Verified clean `cafea0f36091396dff6ebd5efd88d59cd1e97f77`, branch `codex/genuine-bmssp-engine`, origin `https://github.com/sallahuddin92/BMSSP_Logistics_optimizer.git`, workspace `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer`. Immutable source archive SHA-256 `8307d03297b0f80ceaa207a5c5ed9f6aab2007e4d51b538bb1ce5de20387c53c`; read-only extracted files. Independent baseline Release CTest 18/18.

Baseline binding SHA-256 `740c5a3c41217290895975024bba46562ee68bffc48c78e8e3e174948f8ed241`; selected/control/final binding `af98ef92185b6de05c55b37e272a2e693d46caae28d27997f4b0e8061b0c07fb`. Matched Apple clang 21.0.0 (clang-2100.1.1.101), Apple M4 arm64, macOS 26.5.1, CMake 4.3.3, C++20 Release `-O3 -DNDEBUG`, Python 3.11.15, pybind11 2.11.1. SDK, packages, caches and compile commands are preserved. No dependency upgrade or dataset download.

| Graph | Unchanged snapshot SHA-256 | Transformed V/E |
| --- | --- | --- |
| seremban-small | ee772ad6f5e66e90556fccb44ab3ba83cfbe4ad287dc96d06a69dfdc4f167c11 | 3552/5307 |
| seremban-medium | 17b023d65bd0af6d1319a9fe4ed26c61eca795f09ca7ea17c98eec8df2b2c1d2 | 71060/106487 |
| seremban-port-dickson | 3a404e0196a500ec2320cffb600efe960ff4b50f4dbe0d91bc81c303411ac8df | 120428/180496 |

Existing graph bytes and exact Task 8 100-source lists are verified by each process. Historical Task 13 medians 1.779/42.349/72.979 ms, corridor p95/p99 97.290/109.496 ms and +8.67%/+6.71% regressions remain unchanged historical evidence. Task 13 included a 17.93% median-regressing trial. Fresh comparisons below do not normalize away those observations.

## 3. Scalar Comparison Profiling

| Comparison category, ten corridor sources | Calls | CPU evidence | Cost |
| --- | --- | --- | --- |
| Pointer identity | 3,638,629 | fast terminal | 2.481 → 2.230 ns |
| Finite/infinite | 11,144,278 | fast terminal | 2.693 → 2.269 ns |
| Different distance | 37,339,151 | largest terminal class | 2.476 → 1.983 ns |
| Different hops | 3,866,469 | after distance tie | 2.727 → 2.490 ns |
| Equal distance/hops subtotal | 4,773,341 | 4,773,341 vertex-pair visits | overlaps later outcomes |
| Vertex-path difference | 669 | exact reverse order | no shortcut |
| Edge-pass subtotal | 4,772,672 | 4,772,672 edge-pair visits | overlaps later outcomes |
| Parallel-edge difference | 0 | zero observed in this probe | covered adversarially |
| Fully equivalent | 4,772,672 | accepted equality | 3.242 → 3.218 ns |

Total 60,761,868; maximum combined ancestry walk 2 pair visits. Subtotals overlap; terminal categories sum to total. Fresh diagnostic baseline/candidate counts, chain steps and all materialization/work outcomes match. The probe intentionally mirrors the full comparator for classification; its clock is not a dispatch-cost benchmark. No comparison cache is justified.

Ordinary five-second native binding samples identify compare_nodes as the largest algorithm flat frame: 719 baseline / 650 candidate samples. Allocation/free and recursive/frontier work remain visible. Fixed-duration sampling executes different query counts and includes inlining/deduplicated symbols, so flat counts are not per-query speed ratios.

## 4. Disabled Profiling Investigation

| Control | Compiler/overhead evidence | Clean corridor p50 ms, two trials | Finding |
| --- | --- | --- | --- |
| Task 13 baseline | 96-byte frame; Scope lifetime already inlined | 72.127, 72.068 | disabled bookkeeping still costs work |
| Remove comparison ProfileScope | distance micro 1.237 ns; leaf comparator | 66.646, 66.820 | diagnostic only; enabled timing intentionally absent |
| Alternative exact scalar expression | same 96-byte frame; little micro difference | 72.196, 72.139 | no consistent useful query gain; rejected |
| Single-function conditional dispatch | compiler retains 96-byte frame | 71.201, 71.017 | smaller improvement; not selected |
| Separate profiled helper | 16-byte ordinary frame; exact original pure comparator | 70.656, 70.687 | selected narrow layout/dispatch change |

Baseline inactive construction/destruction already inline and read no clocks. Clang still emits scope-state stores, spills and branch/return bookkeeping; the separate helper removes those from the ordinary frame. **Both ordinary paths still resolve active_profile TLS once.** This does not eliminate TLS or claim that public compare forwarding was unoptimized: the wrapper already tail-branches. Enabled dispatch adds another active-profile check/resolution before the original timed helper.

| Control | Static instructions in comparison entry | Estimated ARM64 entry bytes | Indirect TLS call sites, all branches |
| --- | --- | --- | --- |
| baseline | 128 | 512 | 3 |
| no_scope | 56 | 224 | 0 |
| scalar | 127 | 508 | 3 |
| dispatch | 204 | 816 | 2 |
| outlined | 72 | 288 | 1 |

Static instruction counts include enabled branches where present and exclude the separately emitted profiled helper. They are not dynamic instruction counts or total module footprints. Full compiler assembly and actual binding disassembly are preserved. Separate CPU Counters traces completed; raw exported process metric arrays were not validated as retired-instruction/branch-misprediction counts, so no such rate or causal claim is made.

Guarded microbenchmarks use volatile selected-label pointers to prevent hoisting, matched source/library definitions and checksums, three repeats in two reversed process orders. Unprofiled inline-reference versus library differences combine call boundaries and profiling, not pure call latency. An earlier unguarded micro run is retained but unused for that inference. Microbench improvements alone are not application evidence.

| Graph, separate native ten-source query probe | Baseline disabled/enabled p50 ms | Candidate disabled/enabled p50 ms | Enabled comparison calls, each variant |
| --- | --- | --- | --- |
| seremban-small | 1.815 / 6.657 | 1.764 / 6.799 | 1,706,026 |
| seremban-medium | 43.049 / 171.378 | 43.886 / 183.618 | 71,976,174 |
| seremban-port-dickson | 77.533 / 301.062 | 74.245 / 300.871 | 121,523,736 |

These twenty retained observations/mode/variant/region are separate from primary binding timings. They measure all opt-in ProfileScopes, not comparison alone; enabled medium p50 worsens in this small probe and remains disclosed. Scalar micro enabled distance cost is 35.512 → 35.400 ns. Counts, fingerprints and work match in every paired record. Entry/return/workspace teardown residuals and profile inclusive/exclusive arrays are retained; residuals are not pure destructor time.

Protocol failure: a CPU Counters diagnostic overlapped the first exploratory `controls` batch. The **entire batch is ineligible for acceptance**, with every observation/log preserved. Full uniform `clean-controls` and `clean-dispatch-controls` reruns completed after counters stopped. The independent initial `dispatch-controls` batch is also retained. This is a documented scheduling failure, not removal of slow sources or unfavorable outliers.

## 5. Selected Optimization

Only production `native/src/symbolic_label.cpp` changes. Both paths share the original pure pointer/infinity/distance/hop/reverse-vertex/edge comparator. compare_nodes tests active_profile; disabled calls execute the pure body, enabled calls enter a separate helper containing the original ProfileScope. A GNU/Clang noinline annotation keeps bookkeeping off the hot frame, with a standard C++ correctness-preserving fallback elsewhere. No forced hot inlining, new global state, cache, ABI/data-layout change or altered build flags. Performance portability beyond this toolchain is unmeasured.

The improvement targets residual disabled bookkeeping established by assembly, micro controls and whole-query comparisons. Header profile.hpp and all native headers are byte-identical. Arena, ownership, materialization policy, numerical validation, relax, BaseCase, FindPivots, run, frontier, degree reduction, parameters, Dijkstra and production routing defaults remain byte-identical/unchanged.

## 6. Equivalence and Profiling Correctness

Frozen Task 13 symbolic implementation checks **92,416 ordered pairs**, all signs and < / <= / ==, with independent vector ordering, long shared/distinct ancestry, parallel IDs, zero-cost paths, large IDs, boundary binary64, invalid roots/arithmetic and numerical environments. Existing Task 13 lifetime, reset, allocation failure and independent-workspace/public-arena tests remain intact.

Separate matched-library Task 13/candidate processes emit **byte-identical full JSON** for 260 cases, **3,122 bounded traces and 322,500 label values**. Evidence includes every before/after vertex/edge ancestry, bound, completion sequence, BaseCase/pivot result, deterministic/materialization counter and enabled profile call count. Independent Bellman-Ford bounded contracts run in the driver and CTest. No private-access workaround or mixed-definition process is used.

Test-only actual-entry counters prove profile call counts inside/outside the solver. Tests cover enabled/disabled, early returns, same/different-part nesting, inclusive/exclusive attribution, exception unwind, repeated and disabled/nested sessions, parent restoration, independent threads and shared arenas. Durations must be finite/nonnegative and consistent, with ordinary clock variation allowed. No hooks enter production/timing binaries. No expectation was weakened.

## 7. Controlled Performance

Each primary batch has four fresh counterbalanced AB/BA/BA/AB process trials, all 100 sources, eight identical warmups, reversed graph-job/variant-start orders and five 1/4/8 matrices per graph/job. No sampling, counters, interception, builds or heavy tests overlap valid timed runs. Host CPU/load/VM/thermal records and every outlier remain. The first final batch showed material tail regressions, so an explicit four-trial replication was requested before acceptance.

**Initial final batch: 400 observations/variant/graph**

| Graph | Task 13 p50/p95/p99 ms | Task 14 p50/p95/p99 ms | p50 / p99 reduction |
| --- | --- | --- | --- |
| seremban-small | 1.792/1.987/2.165 | 1.753/1.946/2.118 | 2.17% / 2.15% |
| seremban-medium | 42.150/45.779/50.466 | 41.592/46.445/56.546 | 1.32% / -12.05% |
| seremban-port-dickson | 72.549/80.373/97.815 | 70.787/84.177/142.893 | 2.43% / -46.09% |

**Replication: 400 observations/variant/graph**

| Graph | Task 13 p50/p95/p99 ms | Task 14 p50/p95/p99 ms | p50 / p99 reduction |
| --- | --- | --- | --- |
| seremban-small | 1.785/1.920/2.088 | 1.742/1.853/1.887 | 2.43% / 9.65% |
| seremban-medium | 42.194/43.304/45.244 | 41.010/42.013/42.757 | 2.80% / 5.50% |
| seremban-port-dickson | 72.245/74.034/75.122 | 70.264/72.378/73.856 | 2.74% / 1.69% |

**Combined primary batches: all 800 observations/variant/graph**

| Graph | Task 13 p50/p95/p99 ms | Task 14 p50/p95/p99 ms | p50 / p99 reduction |
| --- | --- | --- | --- |
| seremban-small | 1.788/1.951/2.109 | 1.748/1.889/2.037 | 2.24% / 3.39% |
| seremban-medium | 42.174/44.485/49.260 | 41.163/44.088/54.551 | 2.40% / -10.74% |
| seremban-port-dickson | 72.349/77.503/92.334 | 70.476/78.331/112.352 | 2.59% / -21.68% |

| Graph / initial then replication trial | Task 13 p50/p95/p99 ms | Task 14 p50/p95/p99 ms | p50 reduction |
| --- | --- | --- | --- |
| seremban-small / 0 | 1.781/2.022/2.109 | 1.750/2.045/2.218 | 1.69% |
| seremban-small / 1 | 1.782/2.010/2.165 | 1.739/1.849/1.855 | 2.39% |
| seremban-small / 2 | 1.815/1.967/2.219 | 1.801/1.986/2.051 | 0.77% |
| seremban-small / 3 | 1.779/1.929/2.021 | 1.730/1.853/1.871 | 2.76% |
| seremban-small / 4 | 1.800/1.909/2.091 | 1.740/1.858/1.871 | 3.38% |
| seremban-small / 5 | 1.790/1.998/2.138 | 1.741/1.842/1.878 | 2.72% |
| seremban-small / 6 | 1.785/1.916/2.018 | 1.748/1.853/1.901 | 2.09% |
| seremban-small / 7 | 1.769/1.883/1.906 | 1.737/1.846/1.857 | 1.83% |
| seremban-medium / 0 | 41.807/43.611/44.675 | 41.314/43.934/50.579 | 1.18% |
| seremban-medium / 1 | 42.550/46.817/56.487 | 42.226/47.166/56.190 | 0.76% |
| seremban-medium / 2 | 42.288/48.812/50.466 | 42.698/54.551/80.709 | -0.97% |
| seremban-medium / 3 | 42.152/43.291/44.500 | 40.925/42.583/43.704 | 2.91% |
| seremban-medium / 4 | 42.218/43.746/46.139 | 41.257/41.974/42.815 | 2.28% |
| seremban-medium / 5 | 42.187/43.582/45.433 | 40.847/42.095/42.515 | 3.18% |
| seremban-medium / 6 | 42.227/42.990/43.391 | 40.943/41.810/42.547 | 3.04% |
| seremban-medium / 7 | 42.146/42.965/43.750 | 41.020/41.973/42.691 | 2.67% |
| seremban-port-dickson / 0 | 72.328/78.539/97.815 | 70.196/80.011/93.778 | 2.95% |
| seremban-port-dickson / 1 | 74.733/90.928/98.140 | 73.771/141.067/158.985 | 1.29% |
| seremban-port-dickson / 2 | 72.320/75.493/88.896 | 71.279/80.307/91.622 | 1.44% |
| seremban-port-dickson / 3 | 72.141/75.824/80.373 | 70.319/72.988/73.638 | 2.53% |
| seremban-port-dickson / 4 | 72.163/74.215/74.810 | 70.317/72.139/73.790 | 2.56% |
| seremban-port-dickson / 5 | 72.117/73.975/74.890 | 70.182/71.642/72.597 | 2.68% |
| seremban-port-dickson / 6 | 72.387/74.169/74.757 | 70.299/72.674/74.031 | 2.88% |
| seremban-port-dickson / 7 | 72.199/73.525/75.146 | 70.256/72.844/73.734 | 2.69% |

| Graph | 1-source matrix p50 A → B ms | 4-source | 8-source | Separate native Dijkstra median ratio |
| --- | --- | --- | --- | --- |
| seremban-small | 1.760 → 1.733 | 3.644 → 3.567 | 8.853 → 8.675 | 50.16x |
| seremban-medium | 42.746 → 41.489 | 170.117 → 165.309 | 337.216 → 328.374 | 52.52x |
| seremban-port-dickson | 73.518 → 71.548 | 291.341 → 284.078 | 579.184 → 564.972 | 51.48x |

Forty matrix observations/size/variant/graph remain; p95 is in JSON, p99 withheld for this small count. Full vectors, directed selected paths, matrix fingerprints and all algorithm/materialization work match. Preprocessing ranges are recorded separately in JSON and raw process manifests; preprocessing code is unchanged. Reference ratios use a separate interleaved replay, not historic denominators.

**Supplemental temporal pairing, not pooled into primary distributions:** two fresh trials retain all 100 sources, alternating AB/BA per source with the same binaries/warmup/worker solve boundary. This investigates block-order variability without selecting a favorable subset.

| Graph | Task 13 p50/p95/p99 ms | Task 14 p50/p95/p99 ms | Candidate faster pairs |
| --- | --- | --- | --- |
| seremban-small | 1.807/1.924/1.972 | 1.758/1.880/1.926 | 179/200 |
| seremban-medium | 42.708/44.179/44.583 | 41.528/43.081/44.397 | 190/200 |
| seremban-port-dickson | 72.728/74.768/76.213 | 70.707/72.283/73.599 | 196/200 |

## 8. Corridor Tail Analysis

Historical Task 13 primary corridor p99 is 102.612 → 109.496 ms, including candidate source **3302605187** at 166.435 ms (166.096 ms internal) and **4866711343** at 141.705 ms. Those observations remain preserved. Task 14 initial corridor p99 is 97.815 → 142.893 ms; replication is 75.122 → 73.856 ms. Combined primary p99 remains **92.334 → 112.352 ms (+21.68%)**, and medium remains **49.260 → 54.551 ms (+10.74%)**. They are not dismissed or normalized away.

| Task 14 initial candidate tail source | Trial | Wall ms | Internal native ms | Ratio to same-source candidate median |
| --- | --- | --- | --- | --- |
| 4866711343 | 1 | 193.957 | 193.673 | 2.80x |
| 3069810875 | 1 | 158.985 | 158.666 | 2.26x |
| 4872869469 | 1 | 158.949 | 158.536 | 2.27x |
| 3186223086 | 1 | 148.446 | 148.073 | 2.13x |
| 4846712491 | 1 | 142.893 | 142.235 | 2.09x |
| 1681331805 | 1 | 141.067 | 140.768 | 1.99x |
| 4958400466 | 1 | 137.145 | 136.877 | 1.92x |
| 4872869469 | 2 | 120.818 | 120.538 | 1.72x |

Source order/mix and deterministic work are identical in both historical/current cohorts; repeated executions of the same source vary. Most large outliers are inside the internal native elapsed interval, whose steady-clock time also includes descheduling. The much smaller wall-minus-native residual does not support a purely binding/return/destruction explanation. Equal allocation requests/bytes narrow volume differences but do not prove identical allocation timing.

Host CPU/load/VM/thermal snapshots are retained for each fresh job; historical first Task 13 batch lacks the later-added top-CPU snapshot. No thermal warning was reported. These snapshots do not establish scheduler, CPU-frequency, cache, allocator or environmental causation. The initial Task 14 outliers cluster in a candidate process block; the per-source pairing and replication do not reproduce a general tail penalty, but they cannot erase or causally explain the primary regressions.

Acceptance weighs a modest repeatable whole-query gain, compiler/micro mechanism, 179/190/196 of 200 faster temporal pairs and full correctness against this explicitly retained tail risk. **Tail verdict is MIXED / primary regression**, not universal improvement. Workloads requiring a p99 guarantee need further controlled attribution; the production routing default is unchanged.

**Initial per-source median regressions**

| Graph / source | Reachable | A → B ms | Delta ms / percent |
| --- | --- | --- | --- |
| seremban-small / 4882418195 | 784 | 1.780230 → 1.863479 | 0.083250 / 4.6764% |
| seremban-small / 4881016931 | 56 | 0.122146 → 0.125021 | 0.002875 / 2.3537% |
| seremban-small / 5748074393 | 784 | 1.746938 → 1.784375 | 0.037437 / 2.1430% |
| seremban-small / 7613411579 | 2 | 0.026083 → 0.027500 | 0.001417 / 5.4326% |
| seremban-small / 7610550429 | 4 | 0.029167 → 0.029813 | 0.000646 / 2.2148% |
| seremban-small / 4885879400 | 784 | 1.708313 → 1.719271 | 0.010959 / 0.6415% |
| seremban-small / 579607580 | 784 | 1.859188 → 1.904479 | 0.045291 / 2.4361% |
| seremban-small / 5743060074 | 56 | 0.118646 → 0.119438 | 0.000792 / 0.6675% |
| seremban-small / 5742437287 | 784 | 1.870812 → 1.877875 | 0.007063 / 0.3775% |
| seremban-small / 4904504174 | 784 | 1.832479 → 1.860021 | 0.027542 / 1.5030% |
| seremban-small / 4884533214 | 58 | 0.122834 → 0.125021 | 0.002187 / 1.7809% |
| seremban-small / 5742579429 | 784 | 1.857979 → 1.861042 | 0.003063 / 0.1648% |
| seremban-small / 7597016378 | 784 | 1.790042 → 1.790583 | 0.000541 / 0.0302% |
| seremban-medium / 3250604903 | 14239 | 41.914416 → 45.007792 | 3.093375 / 7.3802% |
| seremban-medium / 6136309793 | 14239 | 41.768813 → 42.443604 | 0.674792 / 1.6155% |
| seremban-medium / 7483121715 | 14239 | 41.473271 → 42.314291 | 0.841020 / 2.0279% |
| seremban-medium / 7415805249 | 14239 | 41.522917 → 42.074187 | 0.551271 / 1.3276% |
| seremban-medium / 7525749618 | 14239 | 40.417313 → 41.086625 | 0.669312 / 1.6560% |
| seremban-medium / 4999010002 | 14239 | 41.801917 → 43.013062 | 1.211145 / 2.8973% |
| seremban-medium / 5748272917 | 14239 | 41.713084 → 41.741333 | 0.028250 / 0.0677% |
| seremban-medium / 7603964430 | 14239 | 42.271625 → 42.848480 | 0.576855 / 1.3646% |
| seremban-medium / 4882048339 | 14239 | 41.686813 → 42.370312 | 0.683499 / 1.6396% |
| seremban-medium / 3782899156 | 14239 | 41.613000 → 42.928667 | 1.315667 / 3.1617% |
| seremban-medium / 3241915038 | 14239 | 42.111729 → 43.733313 | 1.621583 / 3.8507% |
| seremban-medium / 13800342073 | 14239 | 41.600938 → 41.901770 | 0.300833 / 0.7231% |
| seremban-medium / 2103924444 | 14239 | 42.179625 → 42.362438 | 0.182813 / 0.4334% |
| seremban-medium / 5263606000 | 14239 | 40.956750 → 41.413729 | 0.456980 / 1.1158% |
| seremban-medium / 10028797574 | 14239 | 42.189917 → 43.060188 | 0.870271 / 2.0627% |
| seremban-medium / 2482330430 | 14239 | 41.890396 → 41.891875 | 0.001479 / 0.0035% |
| seremban-medium / 5263404749 | 14239 | 41.831771 → 41.902729 | 0.070959 / 0.1696% |
| seremban-medium / 5738449604 | 14239 | 41.459646 → 42.122500 | 0.662854 / 1.5988% |
| seremban-medium / 2103908242 | 14239 | 41.470938 → 42.807792 | 1.336854 / 3.2236% |
| seremban-medium / 6413105494 | 14239 | 42.113875 → 42.155479 | 0.041604 / 0.0988% |
| seremban-medium / 5674139391 | 14239 | 42.073312 → 42.130687 | 0.057375 / 0.1364% |
| seremban-medium / 6952635092 | 14239 | 41.261292 → 42.053000 | 0.791708 / 1.9188% |
| seremban-medium / 7256930773 | 14239 | 41.496229 → 43.187770 | 1.691541 / 4.0764% |
| seremban-medium / 5750822673 | 14239 | 42.509605 → 42.948416 | 0.438812 / 1.0323% |
| seremban-medium / 11545361816 | 14239 | 42.069334 → 42.666229 | 0.596895 / 1.4188% |
| seremban-medium / 5278083312 | 14239 | 42.547105 → 43.191770 | 0.644666 / 1.5152% |
| seremban-medium / 8179288192 | 14239 | 42.836896 → 43.295479 | 0.458583 / 1.0705% |
| seremban-medium / 9252053156 | 14239 | 41.956208 → 42.009459 | 0.053251 / 0.1269% |
| seremban-medium / 6141518670 | 14239 | 41.724000 → 41.877208 | 0.153208 / 0.3672% |
| seremban-medium / 9202294952 | 14239 | 42.270167 → 43.076562 | 0.806395 / 1.9077% |
| seremban-medium / 6136508143 | 14239 | 42.727167 → 42.771333 | 0.044166 / 0.1034% |
| seremban-medium / 6137635394 | 14239 | 40.930333 → 41.480563 | 0.550230 / 1.3443% |
| seremban-medium / 5755213858 | 14239 | 41.354500 → 41.502979 | 0.148478 / 0.3590% |
| seremban-port-dickson / 2483602786 | 24395 | 71.989375 → 73.100875 | 1.111500 / 1.5440% |
| seremban-port-dickson / 5750821211 | 24395 | 72.827354 → 73.055000 | 0.227646 / 0.3126% |
| seremban-port-dickson / 3069838223 | 19 | 0.806187 → 0.815979 | 0.009791 / 1.2145% |
| seremban-port-dickson / 7607043334 | 24395 | 73.694375 → 74.498104 | 0.803729 / 1.0906% |
| seremban-port-dickson / 4958400466 | 24395 | 73.490604 → 74.878542 | 1.387938 / 1.8886% |
| seremban-port-dickson / 7003561324 | 24395 | 73.112771 → 73.227979 | 0.115208 / 0.1576% |
| seremban-port-dickson / 3186223086 | 24395 | 71.630959 → 74.535750 | 2.904791 / 4.0552% |
| seremban-port-dickson / 4866711343 | 24395 | 71.357187 → 78.199209 | 6.842021 / 9.5884% |
| seremban-port-dickson / 3069810875 | 24395 | 74.034355 → 74.572979 | 0.538624 / 0.7275% |
| seremban-port-dickson / 4872869469 | 24395 | 72.320916 → 95.433875 | 23.112959 / 31.9589% |
| seremban-port-dickson / 1681331805 | 24395 | 73.435229 → 81.124500 | 7.689271 / 10.4708% |
| seremban-port-dickson / 12397356586 | 24395 | 73.543542 → 74.974646 | 1.431104 / 1.9459% |
| seremban-port-dickson / 7472858377 | 24395 | 72.240458 → 73.215833 | 0.975375 / 1.3502% |
| seremban-port-dickson / 6136428341 | 24395 | 71.840604 → 72.615062 | 0.774458 / 1.0780% |
| seremban-port-dickson / 11056440882 | 69 | 0.890688 → 0.897625 | 0.006938 / 0.7789% |
| seremban-port-dickson / 4874870412 | 24395 | 73.694771 → 74.954125 | 1.259354 / 1.7089% |
| seremban-port-dickson / 6137258172 | 24395 | 71.266687 → 72.121000 | 0.854313 / 1.1988% |
| seremban-port-dickson / 8817387205 | 24395 | 71.660396 → 72.805938 | 1.145541 / 1.5986% |
| seremban-port-dickson / 4877837323 | 24395 | 72.403917 → 73.793125 | 1.389208 / 1.9187% |
| seremban-port-dickson / 7569557273 | 24395 | 73.661646 → 73.983271 | 0.321625 / 0.4366% |

**Replication per-source median regressions**

| Graph / source | Reachable | A → B ms | Delta ms / percent |
| --- | --- | --- | --- |
| seremban-small / 4884708975 | 784 | 1.681708 → 1.695792 | 0.014084 / 0.8375% |
| seremban-small / 11957995111 | 7 | 0.033353 → 0.037625 | 0.004271 / 12.8067% |
| seremban-small / 4881017003 | 56 | 0.116917 → 0.121230 | 0.004313 / 3.6885% |
| seremban-small / 5738559492 | 784 | 1.664230 → 1.678334 | 0.014105 / 0.8475% |
| seremban-small / 4881017008 | 56 | 0.119208 → 0.123958 | 0.004750 / 3.9846% |
| seremban-port-dickson / 3069838223 | 19 | 0.799438 → 0.817333 | 0.017895 / 2.2385% |
| seremban-port-dickson / 11056440882 | 69 | 0.871166 → 0.945458 | 0.074292 / 8.5278% |

**Combined primary per-source median regressions**

| Graph / source | Reachable | A → B ms | Delta ms / percent |
| --- | --- | --- | --- |
| seremban-small / 4881016931 | 56 | 0.124417 → 0.125021 | 0.000604 / 0.4859% |
| seremban-small / 7613411579 | 2 | 0.026750 → 0.027104 | 0.000354 / 1.3234% |
| seremban-small / 7610550429 | 4 | 0.029437 → 0.029813 | 0.000375 / 1.2739% |
| seremban-small / 11957995111 | 7 | 0.033353 → 0.037521 | 0.004168 / 12.4949% |
| seremban-small / 4881017008 | 56 | 0.120458 → 0.122854 | 0.002396 / 1.9891% |
| seremban-medium / 3241915038 | 14239 | 42.422500 → 42.858355 | 0.435855 / 1.0274% |
| seremban-port-dickson / 3069838223 | 19 | 0.806187 → 0.815979 | 0.009791 / 1.2145% |
| seremban-port-dickson / 11056440882 | 69 | 0.887916 → 0.919438 | 0.031521 / 3.5500% |

## 9. Memory and Allocation

| Graph, ten native queries | Requests, each variant | Requested bytes, each | Peak native RSS A → B MiB | Arena publications, each |
| --- | --- | --- | --- | --- |
| seremban-small | 150,561 | 20,801,880 | 8.14 → 8.14 | 22,088 |
| seremban-medium | 5,481,670 | 935,312,896 | 31.78 → 29.19 | 756,878 |
| seremban-port-dickson | 9,292,376 | 1,558,799,512 | 49.16 → 49.12 | 1,283,618 |

Every per-query request/byte/free/bin/materialization record is exactly equal. Public label layout, slabs, caches, ownership and synchronization remain unchanged. No persistent storage is added. Ordinary comparison frame falls 96 → 16 bytes on this compiler; that is one active frame, not an 80-byte retained saving per call. Observed RSS differences are separate process high-water values and are not attributed causally to the change. Python RSS, slab payload/utilization and current ancestry remain in JSON/raw evidence.

## 10. Full Correctness

| Gate | Result | Elapsed seconds |
| --- | --- | --- |
| release-ctest | 20/20 | 2.938 |
| debug-ctest | 20/20 | 24.677 |
| asan-ctest | 19/19 | 76.736 |
| tsan-ctest | 19/19 | 222.569 |
| python-integration | 123 passed | 12.342 |
| frontend | 5 passed | 0.077 |
| real-roads | 3 regions PASS | 275.004 |
| chrome-browser | Actual Chrome/Leaflet PASS | 8.101 |
| sanitized-python | 89 passed | 3.176 |

Verified **960,816 exact binary64 distances, 643,571 original directed paths and 317,245 unreachable comparisons**. Road directions, parallel/original edge identities, path costs, geometry, capacities, mandatory stops, vehicle/depot returns and API errors retain all established acceptance checks. Chrome 156 uses cached Leaflet with offline tiles intentionally blocked.

Release/Debug include Python binding smoke. Sanitizer CTest contains all nineteen supported native tests; ASan Python integration uses the separate established macOS loader helper, while TSan targets native threads. No skipped/blocked gate is counted as PASS. LeakSanitizer is explicitly disabled. Full argv/cwd/exit/duration records and logs remain outside Git.


## 11. Remaining Bottlenecks

1. Comparison frequency and remaining per-call TLS/function boundaries: unchanged 60.76 million comparisons across ten corridor queries; the selected change reduces implementation overhead, not algorithm work.
2. Recursive/frontier work and allocator traffic: sampled run/insert/hash-map/pool/free frames and unchanged 9.29 million corridor allocation requests remain.
3. Scalar/ancestry data access and BaseCase/relax work: full exact semantics still execute; short observed road walks do not justify caching.

Primary tail variability needs source-matched OS/allocator attribution before promising tail performance. No theoretical complexity improvement or claim that one module explains the remaining Dijkstra gap is made.

## 12. Git Delivery

All correctness and scope gates passed. Exact commit/push/main/clean-tree verification is recorded externally in git-delivery.json. Evidence root `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task14-evidence` retains baseline/candidate/control sources and binaries, successful and protocol-failed experiments, all trials, full traces, counter/assembly/micro/native/binding measurements, tests and hashes outside Git. Main remains `94f54b5206b46541dc12f5c7d8cb7fa019e4f877`. Only the narrow production change, tests, optional diagnostic tools and compact documentation belong in the development commit. External git-delivery.json records final exact local/remote SHA and tree state without a self-referential commit hash.

Frozen code retains Apache-2.0 notices; no external implementation code is imported.

## 13. Next Single Task

Attribute process-batch native tail variability on the same source IDs using separate scheduling/frequency and allocator diagnostics. Preserve uninstrumented replay boundaries. No Task 15 execution begins here.
