# Task 11 FindPivots performance workflow

Use the immutable Task 10 commit
`62b2d0d8926df6ff4ac46b3a4e5c2deabea03b49`. Start with a clean verified branch
and unchanged origin/main, retain `git archive` plus SHA-256, extract read-only
outside the checkout and build a separate Release library/binding. Use Task 10's
[compiler, data and A/B contracts](basecase_performance_workflow.md), the same
three snapshots and exact Task 8 100-source lists. Never rebuild the baseline
from edited workspace sources. No new road download or dependency upgrade is needed.

## Isolated attribution

Before native edits, build the optional executable:

```sh
"$PYTHON" tools/pivot_probe_build.py --source "$BASELINE_SOURCE" \
  --library "$BASELINE_BUILD/libbmssp_foundation.a" \
  --compiler /Library/Developer/CommandLineTools/usr/bin/clang++ \
  --output "$NEW_PIVOT_PROFILE_BUILD"
"$NEW_PIVOT_PROFILE_BUILD/build/pivot_probe" \
  "$TASK9_INPUTS/seremban-port-dickson.txt" \
  "$TASK9_INPUTS/seremban-port-dickson-sources.txt"
```

Repeat for all regions and independently built candidates. The builder refuses
existing output, resolves CMake source-directory identities (including /var
symlinks), hashes source/headers/library/support and freezes its driver/support
and generated source. Identity is a provenance guard, not a cryptographic proof
that an arbitrary supplied library was built from matching source; retain the
matching source/build records and verify hashes.

The executable wraps FindPivots operations only. An optional allocation observer
in the existing executable-only interceptor attributes ordinary/aligned C++ new
requests, requested bytes and frees to cumulative membership, round membership,
current/next vectors, forest maps, owned result vectors, and other work. Other
includes label-arena growth and the leaf queue. Forest attribution covers map
insertion; lookups in the completed forest allocate nothing. Algorithm container
allocators and traversal remain unchanged. The observer's registry and raw-round
recording temporarily disable both interception and observation, so their own
allocations do not contaminate algorithm counts. Observer failure makes the probe
fail rather than emitting plausible measurements.

Every call retains raw [current size, next size, cumulative visited size] rows,
frontier size, early flag, pivot/visited counts and diagnostic wall time. Membership
attempts include initial cumulative seeds, unique insertions and duplicates.
Constructions count actual hash-table objects; dense epochs instead reset logically.
The registry records requested live bytes by allocating call/category, including
bytes still live **after local destruction at return**. This includes returned W/P
vectors, label-arena blocks and newly allocated workspace marks; it is not a leak
claim. Earlier calls can still own arrays/results, so summing retained snapshots
is not a live-memory total. The explicit scratch-byte field gives the logical
workspace array footprint even when allocated by an earlier call. All tagged
allocations must be freed by the end of each complete solver query.

Warmup runs with instrumentation disabled; explicit native Dijkstra checks occur
outside tracking. Operation clocks include observation/counter work and omit later container
destruction; the function-clock residual includes loop, trace and teardown work.
Repeated nested scopes of the same category are not timed twice. Scope clocks,
pointer registries and raw trace recording perturb execution substantially. These times are **diagnostics only**. Use separate
ordinary-binding sampling to estimate inclusive FindPivots cost, and ordinary
allocation_probe executables for whole-query allocation/RSS comparisons. RSS
from the instrumented registry process is unsuitable for that comparison.

## Stages and acceptance

Build A (round membership only) and B (cumulative membership only) in external
source snapshots. Run native/frozen-reference tests, attribution and ordinary
allocation probes, then two fresh matched trials against the immutable baseline.
Only then measure A+B. Current/next vectors, forest maps and result ownership
remain unchanged unless a separately justified experiment is validated.

Final replay uses the existing unmodified controller:

```sh
"$PYTHON" tools/native_ab_benchmark.py --queries "$TASK8_EVIDENCE/after-compat" \
  --variant "baseline=$BASELINE_BUILD/python" \
  --variant "combined=$CANDIDATE_BUILD/python" \
  --trials 4 --matrix-repeats 5 --output "$NEW_FINAL_AB_DIRECTORY"
```

No heavy tests, builds, interception or sampling overlap timed jobs. Both variants
use identical flags/SDK/dependencies, eight identical untimed warmups per job,
fresh processes/trial, AB/BA/BA/AB and reversed graph/preparation orders. Keep
all 400 observations per graph/variant, host conditions and 20 matrices at each
1/4/8-source size. Verify complete binary64 vector/path/matrix fingerprints and
all deterministic work counters. Record preprocessing separately, every source
regression and native-only versus Python RSS separately. Use a separate
`--reference` replay for the remaining Dijkstra gap. Scheduling/frequency are not
pinned; fixed-source empirical percentiles are not production tail guarantees.

## Ownership and exact behavior

FindPivots finishes before run constructs its frontier or invokes any recursive
child. Its forest consumes membership before return. Parent run frames retain
only owning PivotResult vectors, never either membership array. No production
callback occurs inside FindPivots. Two **dedicated** epoch arrays therefore reuse
capacity safely across calls/rounds; validation and BaseCase marks are untouched.
Each workspace owns its arrays; arrays initialize only when the relevant operation
first runs. They cost four bytes each per transformed vertex. This can penalize
tiny reachable components and must be measured on the unchanged query distribution.

PivotScratch::Use rejects overlapping FindPivots entry and clears its active flag
on every exit. Reset after an exception remains the existing workspace contract;
the next call/round begins a new epoch, ignoring abandoned marks. Epoch wrap clears
before reuse, and index access uses the verified bounds-checked DenseMarks API.
Concurrent mutation or other reentrant mutation of the same workspace remains
unsupported. No mutable state is shared between independent workspaces.

The frozen Task 10 reference retains its original sets/maps/control flow. A CMake
**test-only** generated translation unit adds exact before/after and round hooks
to the current source; production libraries/bindings/CLI/timing builds never
compile those hooks. No Python dependency is introduced for standalone native
tests. Tests compare complete W_i/W/P sequences, every symbolic predecessor label,
rounds, early returns and deterministic counter deltas on actual recursive calls.
Independent Bellman-Ford/bounded observers, existing frontier and BaseCase suites
provide additional checks. All CHECK assertions remain active in Release.

Run full Debug/Release, ASan/UBSan, supported TSan, native/Python/logistics/frontend,
real Chrome/Leaflet and the unchanged 960,816-distance/643,571-path road gates.
Keep raw failures and corrected setup attempts; no blocked gate counts as PASS.
