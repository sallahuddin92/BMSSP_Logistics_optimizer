# Task 14 comparison execution workflow

Baseline is `cafea0f36091396dff6ebd5efd88d59cd1e97f77`. Verify exact clean HEAD,
branch `codex/genuine-bmssp-engine` and unchanged origin; unexpected work stops
initialization. Archive/hash outside Git and extract read-only. Build a separate
Release engine, bindings and allocation probe against that source, never edited
candidate sources. Reuse Task 13's compiler/SDK/dependencies, C++20 `-O3 -DNDEBUG`,
three snapshots, exact 100-source lists and ten-source native exports. No downloads.

## Controls and compiler evidence

Each control is a separately copied/rebuilt source tree with matching headers,
compiler and flags. No different class/struct definitions are mixed in a process.

- Baseline: unmodified Task 13.
- `no_scope`: remove only comparison's ProfileScope. Diagnostic lower bound; this
  deliberately lacks enabled comparison timing and is never eligible for shipping.
- `scalar`: replace only distance/hop ternaries with differences of two boolean
  less-than results. This keeps both-less-than-false behavior, including NaN, and
  leaves pointer/infinity/ancestry/edge ordering intact.
- `dispatch`: branch around ProfileScope and call one pure original comparator.
- `outlined`: isolate the profiled helper, with the identical pure comparator used
  by both paths. Prevent timing/bookkeeping inlining on GNU/Clang; other compilers
  retain a standard C++ correctness-preserving fallback.

Use Clang `-S` plus `llvm-objdump --macho --disassemble --demangle` on the actual
bindings. Preserve source/binary hashes, full commands, assembly and disassembly.
Static ARM64 instruction counts/code bytes are not retired dynamic instructions.
Baseline constructors/destructors are already inlined: do not claim missed inlining
of them. The observed issue is residual scope state, spills and layout on disabled
calls. The ordinary path still resolves active_profile TLS once; this optimization
does not remove TLS access. Public compare forwarding already uses tail branching.

The selected helper's noinline annotation controls layout, not behavior. Profiling
continues to use the original ProfileScope, thread-local nesting and clocks. All
pointer/scalar/tie decisions share the exact original pure function. No mutable
global, dispatch cache, graph filter or alternate algorithm is introduced.

## Isolated costs

```sh
"$CXX" -std=c++20 -O3 -DNDEBUG -I"$VARIANT_SOURCE/native/include" \
  native/tools/comparison_microbench.cpp "$VARIANT_BUILD/libbmssp_foundation.a" \
  -o "$EXTERNAL_BUILD/comparison_micro"
"$EXTERNAL_BUILD/comparison_micro" baseline
```

The no_scope control passes that explicit name to validate its deliberately absent
profile calls; the argument does not change the engine implementation. Fixed public
labels exercise identity, infinity, distance, hops, equivalent and deep parallel
refinement, alternating signs with an exact checksum. Volatile selected-label
pointers prevent hoisting the pure inline reference out of the loop. Guard overhead
is common to all modes. Two reversed process orders each contain three repeats;
enabled/disabled/inline-reference loops have separate iteration counts and results.
An initial unguarded micro run is retained but not used to infer inlining cost.

The inline reference removes profiling and out-of-line boundary costs together;
its difference is not a pure function-call latency or an independent application
speedup. No microbench result alone supports acceptance. CPU Counters traces are
separate instrumented process experiments. Raw metric arrays need validated schema
interpretation before claiming retired instructions or branch-misprediction rates.

Compile `native/tools/profile_query_probe.cpp` against each matched variant for
separate enabled/disabled native-query measurements on the fixed ten sources per
region. Two counterbalanced process rounds retain all queries, full-result
fingerprints, deterministic work, every ProfileScope call count, inclusive/exclusive
arrays, native query time and external native call time. Warmup/reference checks are
outside measured calls. The call-minus-internal interval includes entry/return and
workspace teardown; it is not pure destructor time. These diagnostic measurements
are separate from unprofiled binding A/B. Inspect enabled overhead honestly; no
claim of exact nanosecond equality is required.

## Differential and profiling validation

`profile_scope_tests` derives one test-only comparator object with an entry counter;
all class definitions match production. The normal library object is not pulled
when its complete symbol implementation is provided by this test object. No hook
is linked into production, bindings or timed probes. Frozen Task 13 symbolic code
in a separate type namespace checks all signs/operators with independent vector
ordering, long shared/distinct ancestry, parallel edges, large IDs and numerical
boundaries. Existing lifetime/arithmetic/independent-workspace tests remain intact.

Tests cover disabled/enabled calls, actual solver comparison entry counts, same-part
and different-part nesting, parent/child exclusive attribution, early returns,
exception unwind, disabled/nested session restoration, repetition, outside-solver
calls, independent threads and shared-arena public extensions. Durations must be
finite/nonnegative with consistent nesting; no exact clock speed is asserted.

`comparison_trace_probe` independently validates bounded contracts/Bellman-Ford in
CTest. Compile the same driver once against immutable Task 13 and once against the
candidate and invoke `--full`. Compare parsed raw JSON and bytes, including every
before/after symbolic vertex/edge chain, bound, completion order, pivot/BaseCase
result, materialization and algorithm counters, and enabled profile call counts.
This separate-process design avoids private-access tricks and ODR violations.

## Whole-query acceptance and tails

Build controls and run allocation/diagnostic probes and ordinary sampling before
timing. Use separate clean paired control batches, then at least four fresh final
counterbalanced AB/BA/BA/AB processes with all 400 observations/variant/graph,
identical eight-source warmup, reversed graph-job/variant-start orders and twenty matrices
at each 1/4/8 size. No sampling, counters, interception, build or heavy test may
overlap timed jobs. Keep CPU/load/VM/thermal records and every source/outlier.

One initial exploratory control batch experienced a counter-probe overlap. Its
entire batch is explicitly a protocol failure, preserved and ineligible for
acceptance; rerun the complete batch uniformly. This is not an outlier filter.
Keep the failed protocol, retry and all rejected controls visible in the report.

Review Task 13's preserved eight-trial corridor observations. Compare source IDs,
within-source variation, internal time and binding/entry/teardown residuals; equal
source mix cannot alone explain varying repetitions. Do not attribute environmental
causation from load correlation. If Task 14 tails are inconsistent, document a new
replication without pruning the initial batch; show both and their combined results.
Use a separate interleaved native Dijkstra replay after A/B.

After timings finish, run fresh Release/Debug, supported ASan/UBSan/TSan, Python,
API/logistics/VRP, frontend, actual Chrome/Leaflet and all three road gates:
960,816 distances, 643,571 directed paths and 317,245 unreachable comparisons.
ASan's established macOS helper explicitly disables LeakSanitizer. Preserve all
source/build hashes, commands, artifacts and raw observations outside Git. Commit
and push only a verified development-branch PASS; leave main/defaults unchanged.

When the first final batch and its replication disagree on tails, a distinct
all-source temporal-pairing probe can alternate AB/BA for each unchanged source.
`tools/paired_source_probe.py` retains all 100 sources per region in two fresh
trials, identical eight-source warmup and worker solve boundaries. It checks full
distance/path fingerprints and all work counters. This supplemental protocol is
reported separately and never pooled into the primary process-batch distribution
to improve its percentiles. The initial and replicated regressions remain visible.
