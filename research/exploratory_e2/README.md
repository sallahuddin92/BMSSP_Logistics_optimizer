# EXPLORATORY_BMSSP_TAIL_ATTRIBUTION — E2

E2 is one native diagnostic campaign, not an algorithm optimization or Task15 execution. See DIAGNOSTIC_PLAN.md and RESULTS.md. EVIDENCE_PATH.txt identifies its fresh external evidence root. A1/A2 use exactly the same executable file in different fresh processes; B uses the exact E1 H1 patch in an external source copy; D calls native reference Dijkstra. Active native source and the E1 patch never change.

## Reproducing the retained campaign

Use the recorded existing Python3.11 interpreter and standard library, CLT compiler and SDK; no software installation. Preserve the original evidence root and use a new absolute external root for any reproduction. The source preparation was:

1. Export Git commit04cf15c043e290c375155d7b0f2cd30c4c65d4f5 into source-A; copy into source-B.
2. Apply research/exploratory_e1/candidate-engine.diff only to source-B. Compare every native source/header to source-identities.json: only native/src/bounded_frontier.cpp differs; its B SHA matches the E1 candidate. Copy the retained input-identities.json (or equivalent identical archived paths/hashes) and generate source files as original_position external_vertex_id, all100 and first10 occurrences.
3. Set campaign.ROOT to the new root before importing other E2 modules or calling phases; do not overwrite this committed run's EVIDENCE_PATH.txt or retained logs. All actual argv, process exits, environment selection, source/binary hashes, CMake caches and compiler/link commands are retained. Native builds are external, Release/arm64/deployment26.0, strict C++20, Python/sanitizers/allocation-probe OFF for primary executables.
4. Generate the same complete12-block plan. Four condition orders are [A1,A2,D,B], [A2,B,A1,D], [B,D,A2,A1], [D,A1,B,A2], repeating three times; graph order rotates modulo3, sources modulo10. Five measurements plus one warmup/source/process.
5. The initial CLOCK_MONOTONIC endpoint arm was rejected before primary collection because its1us quantization invalidated aperture-only empty intervals. Its source versions, build directories, calibration and360 endpoint observations remain retained. The final code uses CLOCK_MONOTONIC_RAW. predeclared-plan-raw.json preserves the unchanged jobs and correction with zero preceding primary samples. A raw-first reproduction should declare this clock directly; it need not repeat the known coarse-clock arm. Never pool the two clock versions.
6. Run the build, correctness and clock phases. quality.py's byte-continuity check is specific to this run's pre-data clock rebuild; a raw-first reproduction instead runs fresh full native/road checks and validates all corrected-clock reads/empty pairs directly. Correctness logs retain all100 positions and full interleaved BMSSP/Dijkstra distance bits. The old/new correctness executable hashes and all eight native object-member hashes are identical in this retained run.
7. Require supported monotonic clocks, no read failures/backward steps, and a validated empty aperture envelope before calling measure. Retain negative off estimates. It launches144 serial fresh processes and stops on failure without replacements. Primary logs are exclusive-created.
8. Only after primary completes, run analyze.py, then diagnostics.py build, allocations and sampling serially. Allocation instrumentation is confined to a separate generated library/executable; removing its include/scope insertions reconstructs original source bytes exactly. A2's ordinary baseline bytes remain identical to A1. Allocator processes run two replicates/variant/road, three repetitions/source; sampling uses six separate ordinary spin workers. No diagnostic profiler/build/test overlaps primary timing.
9. Run summarize_diagnostics.py and test_analysis.py. Analysis uses all7200 observations, exact work/fingerprint checks, paired blocks/sources, descriptive nearest-rank quantiles and10000 bootstrap draws seed20261112. Correctness/raw filenames are documented by invocation journals; a raw-first reproduction must point readers at its corresponding fresh correctness logs.
10. finish.py records the authored interpretation for THIS dataset; it is not a generic automatic scientific classifier. A reproduction requires its own assessment, not blind reuse of these conclusions. Seal with seal.py only after review.

The actual run can be inspected/verified without launching queries:

    python -B test_analysis.py
    python -B seal.py verify

## Measurement semantics and limits

A paired endpoint reads wall_before, threadCPU, wall_after. Primary wall spans native solve/return; CPU spans the slightly wider CPU-read interval. Six raw values, errors and apertures are retained. No overhead subtraction or clamping. Wall-minus-CPU and envelope-minus-CPU are aperture-based observations, not scheduler/core-placement evidence or guaranteed clock-accuracy bounds.4007 negative primary estimates are retained; all7200 CPU intervals fit their wall envelopes.

Requested C++ allocation/live bytes exclude C malloc/realloc/allocator metadata. Address reuse means previously observed addresses, not proof of a specific allocator cache policy. Event age is callback count, not duration. The5.375MiB static observer and8192 retained events/process bound memory; all truncated event records are counted, with complete aggregate histograms and no address-table overflow. Traced wall p50 is17–27% above primary, so diagnostic latency is never pooled. Whole-process RSS includes buffers and graph storage, not a single query's live heap.

CPU sampling records actual tool/worker exits. Allocator exclusive and insertion inclusive samples overlap and are never added. No thermal/core/cache causality is inferred without direct evidence. H1 remains unaccepted, Task15 remains blocked, and no StarNAV/Valhalla claim or production promotion occurs.

During allocator queries, resident bytes, bounded buffer occupancy/truncation and table coverage were monitored. System memory-pressure/VM queries were captured only after the campaign; no time-resolved system-wide pressure history is claimed. The retained report contains authored conclusions for this dataset, not an automatic classifier for future runs.
