# Task 13 symbolic-label execution workflow

Baseline: `71ddb767437df3df602d1ba81471c13540199996`. Verify clean branch
`codex/genuine-bmssp-engine` and unchanged origin. Archive that commit outside the
checkout, hash/extract read-only, and build a separate Release library, extension
and allocation probe with the established Task 12 toolchain. Never rebuild the
baseline from edited sources. Existing road fixtures, snapshot identities, Task 8
100-source query lists and Task 9 text exports remain unchanged. No new download.

## Selected change and lifetime argument

Candidate A constructs a local `LabelNode` value, checks the same symbolic bound
and destination order, and publishes arena storage only for a strict improvement.
It uses the original full comparator, factored into `compare_nodes`; this is not a
scalar-only shortcut. Scalar distance, hops, reversed vertices and parallel-edge
refinement retain their order, including pointer-distinct equivalent chains.

`extension_node` first validates source/edge endpoints, then performs checked
binary64 addition and checked hop addition in that order. Both calculations occur
even when a cheap scalar bound could reject. No epsilon, changed weights or
changed numeric-environment requirement is introduced. FindPivots still calls
unbounded relaxations, including its required updates above its membership bound.

The local node borrows its immutable parent. During both comparisons, the source
label in the workspace owns the parent's arena. No mutation/publication occurs
before comparisons finish. On strict improvement `materialize` copies the complete
node into the same locked, stable arena before destination assignment. The local
node's address is never stored in a label, frontier, returned result or arena node;
the copied parent pointer already names arena-owned storage. A self-edge with
nonnegative weights cannot strictly improve its own source label because hops
increase, so destination assignment cannot invalidate a borrowed source first.
Saved labels/boundaries keep shared arena ownership across workspace reset/destruction.
The public `extend()` still always materializes and shares its original arena.

No arena/slab policy, mutex, shared-label public lifetime, FindPivots, BaseCase,
recursive run body, frontier, degree reduction, k/t, Dijkstra or routing default
changes. Candidate B/C were not automatically bundled. Road chain walks and lack
of observed try-lock misses did not justify caching or a synchronization redesign.

## Diagnostics and exceptions

`label_nodes_created` preserves the legacy logical root/finite-source extension
candidate count, including now-transient candidates. Every such attempt still
constructs a full checked `LabelNode` value. `label_nodes_materialized` separately
counts stable arena publications by root/reset/relax; successful queries satisfy
`materialized = label_updates + 1` and `materialized <= created`. Public `extend`
outside a workspace is not part of that workspace's diagnostics.

The legacy algorithm-work counters are unchanged and compared exactly with old
binaries. The new materialization field is retained independently per A/B sample,
with explicit correspondence assertions; it alone is excluded from cross-version
algorithm-work equality. Old binaries use their eager created count as their
materialization count. No work/outlier/query is filtered out.

The existing opt-in `profile.label_creation` clocks arena allocation, so its call
count matches **materialized**, not the legacy eager-equivalent candidate count.
The Python profile contract test asserts this new explicit correspondence, strict
publication counts and identical before/profile/after algorithm counters; no
correctness expectation is removed. Allocation failure during accepted publication
rolls back the legacy creation count to its original eager failure behavior and
leaves the destination unchanged. Rejected/equality-only candidates no longer need
arena allocation and therefore no longer fail just because an unused slab would
have needed memory. Accepted/public-extend allocation failures remain tested.

## Separate diagnostic engine

```sh
python3 tools/symbolic_probe_build.py --source "$PRISTINE_SOURCE" \
  --output "$NEW_DIAGNOSTIC_DIRECTORY" --compiler "$CXX"
"$NEW_DIAGNOSTIC_DIRECTORY/build/symbolic_probe" \
  "$TASK9_INPUTS/seremban-port-dickson.txt" \
  "$TASK9_INPUTS/seremban-port-dickson-sources.txt"
```

The output refuses overwrite and must be outside the source tree. All native
sources compile against the same copied/instrumented headers, avoiding mixed
instrumented/uninstrumented class definitions. Generated sources, headers, builder,
CMake flags and source hashes remain in the output. Unsupported source shapes fail
instead of silently omitting the principal comparison/relaxation hooks. Repeat
against the candidate. This executable is never linked into timing or application
binaries.

Comparison categories: pointer identity; finite/infinite; different distance;
different hops after a distance tie; equal distance/hops (overlapping subtotal);
vertex-path difference; vertex-equivalent edge pass (overlapping subtotal);
parallel-edge difference; full equivalence. Report terminal categories separately
from overlapping subtotals. Walk steps count visited node pairs in the vertex and
edge passes; maximum walk sums both passes within a comparison.

Creation counters classify attempts, strict updates, equality-valid relaxations,
bound rejections and destination rejections. Arena publication calls, slab count,
total slab slots and final current-label ancestry census distinguish published
nodes from the subset reachable through final labels. The arena retains every
published node until its last owner dies, including obsolete versions. Current
label roots/ancestry are measured at final solve, not as a peak of all saved frontier
snapshots. The census disables ordinary allocation counting for its own temporary
set. Slab utilization is published nodes / allocated slots, excluding allocator
rounding and block-handle overhead.

Instrumented SymbolicLabel copies/assignments/moves/destructions and explicit
arena-owner copies count high-level ownership operations, not every library-internal
atomic instruction. Allocation clocks include lock waiting. Diagnostic try_lock
misses are observed separately; a miss would not alone prove sustained contention.
Arena teardown clears blocks under a separate clock; timed label destruction also
includes shared-owner release and can overlap arena teardown. These clocks include
instrumentation overhead and must not be summed as disjoint CPU percentages.
No leak/race guarantee follows from a zero observed count.

Use uninstrumented `allocation_probe` for ordinary C++ requests/bytes/native RSS,
separate ordinary binding sampling for CPU evidence, and normal A/B query times
for latency. Record diagnostic elapsed/overhead separately. Profile-registry/census
RSS is not a normal memory comparison. Warmup and reference checks stay outside
allocation tallying.

## Frozen tests and performance acceptance

The added tests freeze Task 12 public symbolic code in a separate type namespace
and Task 12 bounded-workspace code in another test namespace. They check independent
vector-based ordering, Bellman-Ford bounded contracts and native Dijkstra, full
selected edge/vertex paths, exact bounded traces and all legacy deterministic work.
Existing Task 10/11 frozen BaseCase/FindPivots/recursive-membership tests remain intact.
Long distinct parent chains exercise both borrowed comparisons and public snapshots.
Adversarial test-only seeding/arithmetic-limit mutations use allocated nonconst
objects with defined access and restore them before further queries; no dangling
pointer or undefined-memory fault injection is used.

Run two exploratory paired trials, then four fresh final counterbalanced process
trials using `tools/native_ab_benchmark.py`: identical 100 sources, eight warmups,
AB/BA/BA/AB, reversed graph/preparation orders, all 400 samples per variant/graph,
20 matrices at each 1/4/8 size, exact fingerprints and work. Keep thermal/load/VM
samples, every source regression, tail and failure. Do not overlap timing with
builds, tests, sampling or allocation interception. Run native Dijkstra comparison
as a separate interleaved reference replay.

After performance runs, execute fresh Release/Debug, ASan/UBSan and supported TSan,
Python/API/logistics/VRP, frontend, actual Chrome/Leaflet and all three road gates.
Retain 960,816 distances, 643,571 original directed paths and 317,245 unreachable
comparisons. The established macOS ASan helper disables LeakSanitizer explicitly;
ASan success must not be described as leak-detection coverage. Preserve evidence
outside Git and push only a verified development-branch PASS; main is unchanged.
