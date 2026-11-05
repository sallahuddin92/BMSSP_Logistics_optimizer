# Task 12 recursive completed-membership workflow

Baseline is Task 11 commit `6019d2752345d977f568635e344fd8c959fbd328`.
Verify clean branch/origin, archive that commit outside the checkout, hash it,
extract read-only, and build a separate Release binary. Use the same compiler,
SDK, flags, dependencies, three snapshots and exact Task 8 100-source lists from
[the existing workflow](pivot_performance_workflow.md). Task 11's published
small-road p99 and source regressions remain historical baseline observations.
Never rebuild baseline from edited current sources; no new road download is needed.

## Allocation and frame attribution

```sh
"$PYTHON" tools/frame_probe_build.py --source "$BASELINE_SOURCE" \
  --library "$BASELINE_BUILD/libbmssp_foundation.a" \
  --compiler /Library/Developer/CommandLineTools/usr/bin/clang++ \
  --output "$NEW_FRAME_PROFILE"
"$NEW_FRAME_PROFILE/build/frame_probe" \
  "$TASK9_INPUTS/seremban-port-dickson.txt" \
  "$TASK9_INPUTS/seremban-port-dickson-sources.txt"
```

Repeat against matching independent dense/adaptive builds. The generator verifies
resolved CMake source identity, freezes executable-only support/source and hashes
its inputs/library. Directory identity is not a cryptographic proof of an arbitrary
library's provenance; retain matching source/build hashes. Outputs refuse overwrite.

Categories are completed membership, run-owned complete vectors, child frontier
vectors, BatchPrepend temporaries, other run bookkeeping, BaseCase, and FindPivots.
The existing executable-only allocation observer records successful ordinary and
aligned C++ requests/bytes/frees, live requested bytes and retention by allocating
frame/category. Recording the profiler's own registry/records disables interception
and observation. Errors in observation fail the probe. No replacement allocator or
probe hook is linked into production libraries/bindings or timing processes.

Every run entry is counted, including level zero. Detailed records cover non-base
frames (and a standalone root base frame); ordinary base calls contribute a separate
category to their parent without allocating a trace record for every leaf. Parent
record IDs/category state restore on child exit. Raw frame records contain depth,
level, frontier/returned sizes, completed cardinality, rehash/bucket activity,
creation-through-membership setup, inclusive elapsed time, direct-child elapsed,
local teardown after finish, and bytes still alive after local destruction.
Membership operation scopes and rehash observations are exact counters; their clocks
include observation overhead and exclude later container destruction. Frame setup
also includes FindPivots/frontier initialization; teardown includes all locals,
not just membership. Inclusive recursive times overlap; subtract direct-child time
for a diagnostic exclusive frame total. Never substitute these times for latency.

Peak active membership sums live frame cardinalities, excluding returned inactive
child sets; peak live call depth also counts base frames. Per-frame retained bytes
can belong to workspace caches/results/arenas and must not be summed as a simultaneous
memory snapshot. Explicit pool getters report retained cache and active-slot payload/
metadata separately. Requested bytes exclude allocator rounding, C malloc and OS data.
All tagged allocations must disappear by the end of the complete public solve.

Use ordinary allocation_probe processes for total-query requests/bytes/native RSS,
and separate normal-binding stack sampling for CPU evidence. Instrumented-registry
RSS is unsuitable for comparison. Warmup is unobserved; explicit Dijkstra checks
occur outside measurement. Extra tiny-component probes reuse unchanged exported
graphs and selected source IDs; they do not replace primary query distributions.

## Slot ownership and alternatives

Candidate A uses lazy dense epochs in separately owned slots. Candidate B starts
with eight exact inline keys, then lazily allocates a directory of 512-index epoch
blocks. Eight keys occupy 64 bytes of key storage on this platform and cover measured
tiny states; this is an engineering choice, not a universal optimum. Blocks have
2 KiB uint32 marker payloads and deterministic index mapping, independent of key
order/timing. There is no graph-size cap or truncation. Every access checks the
vertex domain; directories and handles use checked/standard vector growth.

One slot is leased per active non-base depth. Slots live behind unique_ptr handles;
growing the handle vector moves handles, never Slot objects or live leases. An
already active slot cannot be acquired again. Lease moves transfer responsibility;
normal/partial/error exits release the active flag. Parents retain their independent
markers across child calls, while sequential siblings begin fresh epochs in a
released slot. A failed slot creation or marker promotion leaves the pool valid;
reset after an algorithm exception remains the existing workspace contract.

Inline promotion checks all old keys into current-epoch pages before switching mode.
Allocation failure leaves inline answers intact; abandoned page writes are ignored
by the next epoch. uint8 tests force the same wrap logic used by uint32 production
marks. Paged wrap clears only allocated blocks. Workspace copies start with empty
frame caches, matching the prior frame-local state semantics; public signatures
remain unchanged. Concurrent mutation/moving of one active workspace remains
unsupported; independent workspaces share no membership state.

Caches survive low-level workspace reset and can retain pages from a previous large
query, even when a later frame stays inline. Public engine solve owns a fresh workspace
and destroys its caches before returning; allocator RSS can still retain freed memory.
Returned completed vectors/boundary snapshots own their data and never refer into slots.
BaseCase, FindPivots, validation marks, k/t, frontier, comparison and Dijkstra are unchanged.

## Differential and negative tests

Frozen Task 11 workspace code is compiled in a separate test namespace. CMake derives
actual/frozen run test translation units with test-only state/fault hooks; standalone
native tests require no Python. Existing bounded observers record before/after labels,
frontiers, B' and ordered U. Extra hooks exhaustively snapshot membership before/after
children and at return, proving parent preservation and exact key sets. Compare full
symbolic vertex/edge paths and deterministic diagnostics against identical initial
states, including pre-seeded equality-valid states, with independent Bellman-Ford
and bounded-contract oracles.

Defined fault injection duplicates an existing child completion, substitutes an
already-completed pulled key, empties a child result, or regresses a boundary. Each
must trigger its intended existing error message, not incidental undefined behavior.
Pool tests force slot/handle growth, nested ownership, sibling reuse, move/copy,
epoch wrap and allocation failures. All CHECKs remain active in Release.

## Controlled performance and gates

Measure both candidates independently before final selection: build, native tests,
frozen behavior, allocation/live-frame probes and two fresh paired trials. Preserve
all stages and rejected choices. Leave other vectors unchanged unless independently
justified. Final acceptance uses the unmodified controller:

```sh
"$PYTHON" tools/native_ab_benchmark.py --queries "$TASK8_EVIDENCE/after-compat" \
  --variant "baseline=$BASELINE_BUILD/python" \
  --variant "adaptive=$CANDIDATE_BUILD/python" \
  --trials 4 --matrix-repeats 5 --output "$NEW_FINAL_AB_DIRECTORY"
```

Use fresh processes, AB/BA/BA/AB plus reversed graph/preparation orders, eight equal
warmups, all 400 source observations/variant/graph and 20 matrices at each 1/4/8 size.
Verify complete vector, selected path and matrix fingerprints plus deterministic
work counters. Preserve every failure/outlier and host load/memory/thermal sample.
No heavy jobs, sampling, interception or profiling overlap timings. Report small-road
p99 and each source regression individually, not only pooled medians; record preprocessing
and native versus Python RSS separately. Use a separate interleaved --reference replay.

Run full Debug/Release, ASan/UBSan, supported TSan, Python/API/native/logistics,
frontend and actual Chrome/Leaflet gates, plus all established 960,816 distances,
643,571 original paths and unreachable comparisons. Road-gate incidental timings
may overlap correctness builds and are excluded from primary A/B. Do not modify
expectations or call a skipped/blocked gate a pass. No production-default promotion,
complexity theorem, universal latency or race/leak guarantee follows from these results.
