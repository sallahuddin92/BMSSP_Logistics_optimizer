# Task 10 BaseCase performance workflow

The baseline is `5c42a3f7e8e37373ab613f46e69bafb502514e4a`. Preserve a
`git archive` of that commit, verify its SHA-256 against a fresh archive, extract
outside the checkout, make the extracted source read-only, and build a separate
Release library/binding. Never build the baseline from edited workspace sources.
Use the compiler, SDK, build flags, offline environment and exact road/query
identities described in [the existing workflow](native_performance_workflow.md).
Task 9's archived implementation and results remain historical records.

## Allocation attribution

Before production edits, build the opt-in BaseCase probe against the archived
source and its matching CMake library:

```sh
"$PYTHON" tools/basecase_probe_build.py --source "$BASELINE_SOURCE" \
  --library "$BASELINE_BUILD/libbmssp_foundation.a" \
  --compiler /Library/Developer/CommandLineTools/usr/bin/clang++ \
  --output "$NEW_PROFILE_BUILD"
"$NEW_PROFILE_BUILD/build/basecase_probe" \
  "$TASK9_INPUTS/seremban-port-dickson.txt" \
  "$TASK9_INPUTS/seremban-port-dickson-sources.txt"
```

Repeat for all three regions and each staged candidate. The builder refuses an
existing output and checks the library's CMake source-directory identity. It
records source, headers, driver, instrumentation and library hashes. Generated
source wraps only BaseCase; no instrumentation or replacement allocation operator
is linked into production. Keep generated source and commands with the evidence.
The caller must preserve the matching library/source inputs; directory identity
is not a cryptographic proof of their build provenance.

The probe counts successful ordinary/aligned C++ new requests, requested bytes,
frees, queue push/pop counts, peak size/capacity, membership insert/contains,
stale/duplicate records, and completed-result sizes. Queue and completed-vector
attribution covers their growth; dense membership attribution also covers lazy
initialization. Inclusive BaseCase allocation totals include label-arena growth
triggered inside BaseCase. Completed histograms describe **returned** U, after
removing the partial boundary, not the k+1 extraction count. Bucket 64 saturates.
Setup runs through queue/membership/result initialization; body runs through
boundary filtering; teardown includes local destruction and heap lease cleanup,
but excludes later returned-U destruction. Per-query ordinary allocation probes
include that destruction. Requested bytes are allocation traffic, not live memory.

Scope clocks, proxy operations and interception perturb execution. Their times
are diagnostic fractions of the instrumented run, never substituted for normal
query latency. Separate macOS stack sampling of ordinary bindings provides an
additional statistical view; sample counts are not exact exclusive CPU times.
The driver warms each source and checks distances against explicit native
reference Dijkstra outside the measurement scope.

## Incremental and final experiments

Build independent external source snapshots for heap-only and membership-only
changes; run targeted native tests, ordinary allocation probes and a two-trial,
three-variant replay. Then compare the combined change and a separate small
completed-vector reserve candidate. Preserve every stage's source/binary hashes
and all raw measurements, including mixed results and setup failures.

For acceptance reuse the unmodified counterbalanced controller:

```sh
"$PYTHON" tools/native_ab_benchmark.py --queries "$TASK8_EVIDENCE/after-compat" \
  --variant "baseline=$BASELINE_BUILD/python" \
  --variant "optimized=$CANDIDATE_BUILD/python" \
  --trials 4 --matrix-repeats 5 --output "$NEW_AB_DIRECTORY"
```

No build, allocation probe, sampling, oracle or correctness gate should overlap
these timed jobs. Other host activity is recorded, not killed or filtered out.
The harness launches fresh extension processes, reverses preparation/order,
warms identically, keeps all 100 sources, checks complete binary64 vectors,
selected path fingerprints and every deterministic work counter. Report all
400 samples per graph, trial medians, per-source regressions, matrix distributions
and preparation/RSS records. These are repeats of a fixed source distribution,
not 400 independent sources. Run a separate `--reference` replay for the current
Dijkstra gap. Do not infer a complexity improvement or production-default change.

## Lifetime and correctness argument

The reusable heap is private to a workspace. BaseCase is a leaf: its body calls
relaxation, never recursion or the observer. `run` invokes its observer only after
BaseCase returns. Thus active recursive parent frames cannot consume its scratch.
A lease clears on entry and all exits, releases every label owner, and retains
only vector capacity. Top is copied before pop. Standard push/pop heap primitives
use exactly Task 9's comparison; vector max_size checks/dynamic growth remain
unrestricted by k. A failed allocation unwinds the lease. Reset after an exception
remains the existing public workspace requirement.

Extracted marks are a **different instance** from validation marks. They are
allocated lazily on the first BaseCase, initialized with a fresh epoch each call,
and bounds-checked with vector::at. Wrap clears all marks before epoch reuse.
Their cost is four bytes per transformed vertex in a workspace that reaches
BaseCase; the next call ignores any marks left by an exception. No live parent
completed set or pivot set shares these marks. Independent workspaces own their
storage. Concurrent mutation/reentry into the same workspace remains unsupported.

Completed sets remain ordinary owning vectors moved into BoundedResult. A small
reserve, if accepted by measurement, is a growth hint, never a workload bound or
shared scratch. Saved results survive another BaseCase and workspace reset.

The exact Task 9 reference model in basecase_tests compares sequence, symbolic
boundary, ordered U, every finite/unreachable label, predecessor/edge refinement,
relaxation counts and equality-valid updates. Actual recursion leaves are compared
using their before/after snapshots. Independent full-vector Bellman-Ford and
bounded coverage observers separately check the contracts. Heap tests exercise
identical duplicate records beyond k, stale road/fixture candidates, allocation
failure and retained storage; forced uint8 epochs exercise the same wrap logic.
All CHECK assertions remain active in Release.

The full native Debug/Release, ASan/UBSan, supported TSan, Python/native/logistics,
frontend, Chrome/Leaflet and established 960,816-distance/643,571-path road gates
are mandatory. A compilation success or matching final distances alone does not
establish the bounded algorithm's correctness.
