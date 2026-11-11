# BMSSP Exploratory Optimization E1 — results

**EXPLORATORY_BMSSP_PERFORMANCE — INCONCLUSIVE. Candidate not accepted.**

The single H1 change removes the one-element vector staging allocation in bounded-frontier insertion. All correctness gates pass and allocation counts decrease, but distributed medium/corridor high-tail increases remain unexplained. All observations are retained. Active native source has been restored to the starting baseline; the tested candidate remains available as candidate-engine.diff, source snapshot and hashed binaries. This is not an accepted production optimization or a Task15 scientific result.

## Baseline and controlled environment

Starting native source commit: `5e8b11b4db8a0883969e7fe1405b048f419d7f07`. Baseline source is exported from Git and built outside the checkout. Candidate is that engine plus the retained single-file patch. Same CLT AppleClang21, SDK26.5, arm64, deployment26.0, Release optimization and native library compiler argv after replacing only source/build paths. Python bindings, sanitizers and allocation interception OFF for primary workers. The separate Debug ASan/UBSan suite is not a latency experiment. No developer tools were installed or upgraded.

Host: Apple M4,10 logical CPUs,16GiB RAM, macOS26.5.1 build25F80. Current compiler SHA `1220c0afafa12a6ae599d097ee7cf8b87c6b4d8e3fbb9783cee6b319a80683ba`. Fresh selected SDK tree SHA `c375ba5901e2da9253d4ebc0e5ba0cb29a6a5d528e5312855a96e706f00d62d0` (49,730 entries; this experiment's deterministic record ordering). This is a current identity, not recovered historical bytes. Full CMake caches, actual compiler/linker flags and tool output are retained in native-build-manifest.json.

Baseline executable SHA: `c84b24bc605ccabcb530d7b5bffd3eeb6918fd2a23d46aebca0d7caa6d8c2473`.

Candidate executable SHA: `c58f2cd5c590393dc9c2729f3644a70a12da1707bf5bb8be11c905d792c83bbe`.

Graphs retain834/1776,14464/35530 and24736/60214 vertices/directed edges. GraphML/native identities and the independent exact directed parallel-edge/weight-multiset comparison are retained. All100 original source occurrences per graph are correctness inputs; first10 occurrences are performance inputs. No graph/source alteration, topology-specific optimization or Dijkstra fallback.


Measured median degree-reduction/preparation cost (baseline → candidate): seremban-small: 0.470 → 0.459ms, seremban-medium: 10.753 → 10.716ms, seremban-port-dickson: 18.558 → 18.525ms. These construction costs are excluded from all query quantiles.

## Measured native comparison

Primary ordinary latency, milliseconds. Each cell is p50 / p95 / p99, nearest rank over500 samples per graph/condition. BMSSP/Dijkstra is the p50 ratio of quantiles; paired per-query ratios are also in the JSON summary. No profiled samples are included.

|Road|Baseline BMSSP|Baseline Dijkstra|BMSSP/Dijkstra|Candidate BMSSP|Candidate Dijkstra|
|---|---:|---:|---:|---:|---:|
|Small|1.723333 / 2.069875 / 2.474000|0.013542 / 0.019000 / 0.024833|127.26x|1.657667 / 2.011084 / 2.204542|0.013583 / 0.019250 / 0.023083|
|Medium|43.584167 / 49.037500 / 52.095125|0.689459 / 0.839458 / 0.993958|63.22x|42.417958 / 47.463417 / 57.815958|0.698583 / 0.817084 / 0.864625|
|Corridor|74.645167 / 81.031375 / 87.699375|1.277458 / 1.438958 / 1.567208|58.43x|73.374667 / 81.502459 / 91.304625|1.282292 / 1.489250 / 1.704083|

The fresh BMSSP implementation remains substantially slower than native Dijkstra on these SSSP requests. No comparison to Valhalla target-directed routing or StarNAV service performance was performed.

## Candidate versus baseline

Ratios below1 favor the candidate. Intervals resample the ten complete measurement blocks with seed20261112 and are exploratory sensitivity estimates, not confirmatory confidence guarantees.

|Road|p50 ratio|p95 ratio|p99 ratio|Paired sample ratio median|Block-bootstrap p50 ratio95%|
|---|---:|---:|---:|---:|---:|
|Small|0.961896|0.971597|0.891084|0.964749|0.951283–0.974992|
|Medium|0.973242|0.967900|1.109815|0.981727|0.940795–0.998383|
|Corridor|0.982979|1.005814|1.041109|0.984200|0.974665–0.995878|

All6000 primary samples came from120 fresh serial processes:10 blocks ×3 roads ×2 builds ×2 algorithms;50 observations/source/condition, one warmup/source/process. Forward/reverse condition orders balance algorithm and build precedence; graph/source orders rotate. Equal outer solve-return boundaries include workspace cleanup and exclude construction, output fingerprinting, result destruction and I/O. Prior results are destroyed before the next sample. Input preparation is measured separately in every process header. No sampler/build/test/allocation probe overlaps primary measurement.

## Bottleneck and single hypothesis

Stored ordinary CPU samples show general allocation/new/delete exclusive activity at22.9–24.4%, frontier insert inclusive activity at23.3–25.3%, and symbolic comparison exclusive activity at13.3–13.6%. These overlapping quantities cannot be added. Built-in per-operation profiling significantly increases latency and is reported separately. Insertion stages a singleton owning label through a heap-backed vector despite already knowing the destination list. H1 replaces only that staging call with the identical list append/location/peak-key updates. It leaves selection/splitting, ordering, recursion, numerical checks, graph access and API contracts unchanged.

## Correctness and memory safety

Baseline Release19/19; candidate Release19/19; candidate Debug ASan/UBSan19/19. Two analysis-definition tests passed. Existing tests/expectations were unchanged. Native suites include zero-weight/parallel-edge, symbolic ordering, bounded routines, numerical handling, ownership and allocation-failure checks. ASan detect_leaks=0 means LeakSanitizer coverage is not claimed.

Each variant passed all300 archived source-position checks:4,003,400 exact distance entries versus native reference Dijkstra and8,006,800 all-target reachable/unreachable path validations across both engines. Baseline and candidate full saved binary64 vector streams are identical. Every primary sample retains a result fingerprint, and paired BMSSP work counters match with profile counters zero. No unexpected native failures occurred. Finite testing is not a universal algorithm-correctness proof.

## Tails and memory

Medium p99 increased10.98%, corridor p99 increased4.11%, and corridor p95 increased0.58%. Seven medium candidate observations exceed baseline p99, across six blocks/five source positions. Nine corridor observations exceed baseline p99, across nine blocks/five positions. Small has no candidate samples above baseline p99. The investigation retains top observations, source/block/order/load information, per-source/per-block tails and Dijkstra controls. Recorded work is unchanged. Neither those counters nor coarse host-load averages explain CPU/cache/scheduling causes. No bad-block or unfavorable-sample exclusion was applied.

|Road|Median C++ allocation-call reduction|Median requested bytes saved/query|Median process RSS baseline → candidate|
|---|---:|---:|---:|
|Small|8.51%|65,760|4.375 → 4.398MiB|
|Medium|9.48%|1,661,184|30.125 → 30.875MiB|
|Corridor|9.46%|2,814,896|51.289 → 51.586MiB|

The byte savings equal32 times the removed allocation count on every diagnostic query, supporting the stated mechanism. They do not establish lower RSS. Whole-process RSS increases about24KiB,768KiB and304KiB respectively; it includes graph/preprocessing/allocator retention and page granularity, rather than query-only live memory. Allocation probes count ordinary/aligned C++ requested bytes, excluding C malloc and OS allocations.

## Decision and limitations

INCONCLUSIVE: all three p50 estimates and allocation counts improve, but acceptance is withheld because medium/corridor tail increases persist across multiple blocks and cannot be justified from the available evidence. No minimum speedup or post-hoc tolerance was invented. No second optimization or favorable rerun was attempted. Keep the tested candidate as evidence, not active accepted source.

One host, ten blocks,50 samples/source and a mixed-source p99 do not support precise extreme-tail claims. Background machine activity and frequency/scheduling/cache effects were not isolated; host load is retained per process. SDK metadata and current build hashes do not imply a fully archived runtime environment or historical byte equivalence. This experiment establishes neither superiority over Valhalla nor end-to-end routing performance.

Next single task: diagnose H1's distributed tail increases with a separately scoped paired thread-CPU/wall and allocator-behavior experiment before accepting H1 or introducing a second optimization. This follows measured native behavior, not a provenance/readiness audit.

## Evidence and source integrity

External evidence: [/Users/sallahuddin/Projects/BMSSP-exploratory-E1-q8k1o451](/Users/sallahuddin/Projects/BMSSP-exploratory-E1-q8k1o451). Authoritative index: completion-receipt.json, with streaming SHA-256 identities for all retained files and committed experiment sources. It includes fresh build manifests, full graph/source identities, baseline/candidate correctness reports and vectors, raw measurements, statistical summaries, profiling/sample evidence, hypothesis, candidate patch/source snapshot, tail investigation, allocation/RSS data and verdict.

The original codex/genuine-bmssp-engine branch remains at5e8b11b; all starting tracked files, Task15 protocol/harness/locks and frozen binaries remain unchanged. Task15 remains independently blocked. Source/data failure notes preserve the initial unsupported default-Python extraction attempt and corrected sample-summary parser; neither discarded benchmark observations or changed test expectations. Git delivery adds only the exploratory experiment and retained candidate patch. See the Git commit for final delivery identity; this document does not grant scientific approval or initiate further work.
