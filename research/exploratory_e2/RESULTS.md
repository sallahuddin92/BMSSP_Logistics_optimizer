# BMSSP Exploratory E2 — Tail Attribution

## 1. Verdict

**INCONCLUSIVE.** The E1 medium/corridor candidate-specific p99 pattern was not stably reproduced. Median wall/CPU benefits recur, but broad exploratory tail intervals, unchanged-control variation and extreme mixed CPU/wall spikes prevent a complete causal explanation. H1 is not promoted.

## 2. Source and Build Identity

Label: EXPLORATORY_BMSSP_TAIL_ATTRIBUTION. Starting E1 commit04cf15c043e290c375155d7b0f2cd30c4c65d4f5; original engine5e8b11b4db8a0883969e7fe1405b048f419d7f07. External A source is unchanged native engine; external B differs only by the exact retained H1 patch. A1/A2/D execute the same baseline executable, B its candidate executable. No active native source or H1 patch edits. CLT AppleClang21, SDK26.5, Release/arm64, deployment26.0, equivalent strict-C++20 engine flags; all actual compiler/linker argv and caches retained.

A executable SHA: 4f828fe6a9d2351bf78c0f424a9ef9cee62d63e000902a427a459ff05dbb41e4.

B executable SHA: 0da4213d8b527856ac28f25571d9535a6a0906dbff60cd0d9716e33223f1059f.

## 3. Correctness

Fresh A/B native suites passed19/19 each. Both passed all100 archived positions on each of three roads,4,003,400 distance entries/variant versus native Dijkstra and8,006,800 reachable/unreachable path checks/variant, with zero bit mismatches. Full binary64 streams match A/B. The clock-only rebuild preserved identical correctness-executable bytes and all eight native object members, verified before primary. Every ordinary BMSSP sample has matching fingerprints/work and zero enabled-profile calls. Original graph counts834/1776,14464/35530 and24736/60214 and all source occurrences are retained.

## 4. Experimental Design

Twelve blocks ×3 roads ×A1/A2/B/D ×10 sources ×5 repetitions =7200 primary observations,144 fresh serial processes, one warmup/source/process. Williams-balanced orders and rotated graphs/sources are fully predeclared. No failed/replaced/excluded primary observations.

The initial microsecond-quantized wall clock was rejected BEFORE primary measurements. Both old datasets and the pre-data clock correction remain retained. Corrected CLOCK_MONOTONIC_RAW/threadCPU both report42ns resolution and show41ns minimum positive read increments; this is not an accuracy guarantee.10000 corrected empty pairs have no clock failures or CPU-outside-envelope cases. Their tight-wall median is0ns, CPU median125ns; endpoint work explains negative empty differences. No instrumentation cost is subtracted.

## 5. Wall-Time Results

Milliseconds, nearest-rank p50 / p95 / p99;600 samples/condition/road.

|Road|A1|A2 (same bytes)|B (H1)|D|
|---|---:|---:|---:|---:|
|Small|1.584083 / 1.906708 / 3.390958|1.582916 / 1.835083 / 2.004583|1.545125 / 1.809042 / 2.060042|0.013500 / 0.020125 / 0.031875|
|Medium|39.519625 / 41.067417 / 41.717167|39.349458 / 40.829458 / 45.044167|38.275584 / 40.068875 / 41.557458|0.666250 / 0.757167 / 0.817458|
|Corridor|68.000958 / 71.140083 / 77.737875|68.119666 / 71.789542 / 75.285667|66.550667 / 69.399834 / 73.073750|1.246791 / 1.369791 / 1.451500|

## 6. Thread-CPU Results

Milliseconds, p50 / p95 / p99. These are separate quantiles: subtracting CPU quantiles from wall quantiles does not calculate paired off-CPU quantiles.

|Road|A1|A2|B|D|
|---|---:|---:|---:|---:|
|Small|1.584250 / 1.895834 / 2.928625|1.583125 / 1.834458 / 2.004334|1.545250 / 1.791500 / 1.974917|0.013584 / 0.020208 / 0.029958|
|Medium|39.463333 / 40.903834 / 41.511083|39.308667 / 40.761458 / 43.988959|38.245083 / 39.957750 / 41.285958|0.666417 / 0.757333 / 0.809334|
|Corridor|67.955875 / 70.850750 / 77.438667|68.046750 / 71.380709 / 74.890459|66.472083 / 69.071333 / 72.544458|1.244542 / 1.369959 / 1.448166|

All7200 clocks succeeded.4007 signed wall-minus-CPU values are negative and retained; no CPU interval exceeds its wall envelope. Read apertures and raw timestamps are retained, with no clamp or overhead subtraction.

## 7. Tail Attribution

|Road|B/A1 wall p99|B/A2 wall p99|A2/A1 wall p99|B/A1 p99 block-bootstrap95%|B/A2 p99 interval|
|---|---:|---:|---:|---:|---:|
|Small|0.6075|1.0277|0.5912|0.4436–1.0701|0.9424–1.0495|
|Medium|0.9962|0.9226|1.0798|0.9640–1.0699|0.8831–1.0789|
|Corridor|0.9400|0.9706|0.9685|0.7929–1.1034|0.8993–1.0801|

These single-host block-resampling intervals are exploratory, not confirmatory guarantees. Per-source/block/slot and signed off estimates are retained. At n60/source,p99 is the observed maximum; block n50 p99 is also the maximum.

Medium B has12 wall observations exceeding their A1 source p95;9 also exceed CPU references. Corridor B has22 such wall observations;18 also exceed CPU references. Controls show corresponding CPU tails. Off-CPU-like excess also contributes: worst medium B observations include65.077ms wall/55.934ms CPU and63.213/53.071ms; worst corridor B126.867/108.844ms. Unchanged controls also show large mixed spikes, e.g. corridor A1 108.168/90.947ms. These extremes remain in all analyses. A1 small's largest observations concentrate in block0, but other tails span blocks/sources; order/host association does not establish a cause. No retroactive causal claim about E1 is possible because E1 lacked paired CPU observations.

## 8. Allocator Findings

Separate360 diagnostic queries and six ordinary CPU samples completed. Each saved allocation corresponds to a removed32-byte allocation within insertion, paired with same-scope frees. Aggregate histograms, phases, observed address reuse and requested live bytes are retained.

|Road|Paired allocation-call reduction|Diagnostic p50/primary p50 A → B|Allocator-exclusive CPU samples A → B|
|---|---:|---:|---:|
|Small|8.51%|1.207 → 1.269|22.09% → 18.16%|
|Medium|9.48%|1.193 → 1.200|18.82% → 18.07%|
|Corridor|9.46%|1.191 → 1.172|19.53% → 18.62%|

The observer uses5.375MiB of static bounded storage. Every process retains8192 events and explicitly counts additional nonretained event records; aggregate callbacks/histograms have no table overflow or unknown frees. Requested tracked live bytes on return are20016/347136/593664, respectively, and become0 after result destruction in both variants. This is limited C++ callback coverage, not a universal leak or malloc-cache proof. RSS includes graphs/buffers/allocator retention. Tracing increases latency17–27%; it cannot explain ordinary primary tails by timing substitution. Address reuse is observed, but cache/heap-layout causality is unestablished. CPU sampling succeeded for all six processes; exclusive/inclusive categories are not added.

## 9. Hypothesis Assessment

- H2-A: partial support for non-CPU contributions to some tails, not proof of descheduling or a complete explanation.
- H2-B: observed on-thread CPU-time increases in tail subsets, including unchanged controls; H1-specific CPU regression is not established.
- H2-C: H1 temporary-removal mechanism is verified; allocator/cache/layout explanation for E1 tails remains unresolved.
- H2-D: source/block/order/host associations exist; no direct core-placement, frequency, thermal or cache evidence identifies the mechanism.
- H2-E: strongest evidence supports substantial experimental tail variability and limited precision. Identical A2/A1 medium p99 differs7.98%; candidate/control p99 intervals span1.

The strongest supported conclusion is shared on-thread variability plus occasional substantial wall-minus-CPU components, not an identified low-level cause.

## 10. H1 Acceptance Recommendation

**STILL_INCONCLUSIVE.** Positive median wall/CPU effects recur, but available tail precision and extreme observations do not justify promotion. No acceptance threshold was invented after data. Active native source stays unchanged; H1 remains an unaccepted E1 patch.

## 11. Measurement Limitations

One host,12 blocks,60 observations/source, imperfect host isolation, cross-clock precision limits and separate diagnostic perturbation. Empty overhead is not subtracted. Endpoint plain/paired controls have only30 samples and vary substantially, particularly small B; those process-level differences cannot be labeled pure clock overhead. No full malloc/realloc trace, cache-miss/core-placement/thermal events or scheduler traces were collected. Process RSS/buffer coverage was monitored during tracing; system-wide memory pressure was queried only post-campaign, without a time-resolved pressure history. Neither p99 nonreproduction nor callback-count reduction proves absence of a candidate-specific extreme-tail problem.

## 12. Scientific Separation

Task15 protocol/harness/approvals/archived binaries remain unchanged and independently blocked. The E1 branch, patch and sealed evidence remain unchanged. All source/graph/binary/toolchain identities and pre-primary locks verify. SDK verification checks the full49730-entry selected current SDK against E1's current inventory without copying SDK bytes or inferring historical continuity. No StarNAV integration, Valhalla claim, second optimization or scientific approval.

## 13. Git Delivery

Only the E2 research directory is delivered on research/bmssp-exploratory-tail-e2, starting04cf15c. See Git for final commit; source/evidence SHA locks and completion-receipt.json identify retained artifacts. The receipt includes the original clock arm, corrected plan, all observations/failures, native checks, source/vector manifests, allocator/sampling evidence and authored assessments.

## 14. Next Single Optimization

Before choosing another algorithm patch, capture synchronized scheduler and hardware-execution evidence for the retained medium/corridor spike sources under A1/A2/B, using supported tools. Target the measured mixture of CPU-time inflation and wall excess. No additional optimization or campaign starts here.
