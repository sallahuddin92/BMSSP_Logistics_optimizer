# Original production adapter (inactive)

Task 15 Phase 5. This is a separate standard-library package inside the Phase 4
runner directory. It has no CLI entry point and the original synthetic controller,
worker, schemas and tests are unchanged. No operation, JSON field, flag or
environment variable enables execution. `production_gate()` unconditionally raises
`PRODUCTION_EXECUTION_DISABLED`. No scientific approval is granted.

## Implementation

| Module | Responsibility |
| --- | --- |
| `artifacts.py` | Exact frozen variant/path/SHA, CPython 3.11/arm64, thin Mach-O commands, UUID and declared dylibs; no dynamic loading |
| `loading.py` | Exact-path import transaction with isolated injected operations; reject existing global module/variant alias, post-import verification, rollback registry on error |
| `native.py` | Actual ExtensionFileLoader, NativeGraph/engine preparation, solve and perf_counter_ns implementation, each behind an unconditional gate; loaded dyld dependency UUID recovery also gated |
| `graphs.py` | Hash original GraphML, manifest, query capture and native text; reconcile snapshot and first four oracle targets; strict export parser retaining input order and binary64 weights |
| `fingerprints.py` | Distance/path bytes, directed-path structure and predecessor checks, disabled-profile/counter validation, full deterministic work and historical P1/P2 projections |
| `worker.py` | Region graph/engine lifetime, source-position mapping, timed solve, post-timing evidence, result release, one complete framed response |
| `ipc.py` | Separate bounded strict JSON framing, response identity/evidence validation, serial parent/worker contracts and whole-cluster failure propagation |

The archived binding sources at baseline
`cafea0f36091396dff6ebd5efd88d59cd1e97f77` and candidate
`cb5e1b6dd1c7ac52755a29d6b7f411f9b68ee80e` have identical
`native/python/bindings.cpp` SHA-256
`743348ea0145b5e1e3a91f6efcb81abbb60abf735c09dd94d04b538a10ce2271`.
The adjacent `historical-interface.json` records Git-source hashes reconciled to
the Task 14 evidence index/source inventories. The baseline has no
`paired_source_probe.py`; its P2 convention is established from the candidate
archive. No research implementation or third-party algorithm was copied; repository
Apache-2.0 licensing and existing notices remain unchanged.

Actual API: `NativeGraph(vertices, edges)`, `BMSSP2025Engine(graph)`,
`engine.solve(source, profile=False)`, `DistanceResult.source`, `.algorithm`,
`.distances`, `.diagnostics`, `.belongs_to(graph)` and `.path(target)`.
`NativeReferenceDijkstra` is never accessed. Actual native objects are constructed
only after the future production gates. Fake construction accepts only synthetic
graph fixtures and API-shaped fake modules, never the original road exports.

Graphs retain sorted original vertices and original exported edge order, directed
endpoints, unsigned edge IDs and parsed double values. Signed zero is preserved by
the parser; the historical native Graph constructor itself normalizes zero to +0.
The original exports contain 834/1,776 (small), 14,464/35,530 (medium), and
24,736/60,214 (corridor) vertices/edges. Parsing/hash verification does not solve or
construct a native graph.

## Query and ownership contract

A worker retains all three region graph/engine pairs for its cluster. Separate
worker processes use `Cluster.frozen(workload, unit_id, variant)`; its local cursor
maps to the frozen global sequence. The parent `Coordinator` consumes the original
complete query order, including P1 batches and P2 execution-index pair order, one
outstanding request at a time. It never retries. A timeout/EOF/error/mismatched
fingerprint invalidates both variants and all regions; the peer invalidation
callback must terminate/invalidate the owned channels. Caller-owned raw evidence
storage and process spawning remain future integration work, with no activation
path introduced here. Parent receipts retain returned errors before validation.

After complete request validation and prior-result release, bind the solve method,
then read T0, call solve exactly once with profile=False, and read T5 immediately
on return. Retain the DistanceResult through T5. There are no property reads,
hashes, serialization, observer callbacks or writes between those endpoints.
After T5, copy diagnostics, read the distance vector once, reconstruct the four
paths, validate/fingerprint, drop every native/Python result copy, and only then
construct/serialize/write one response. The emitted evidence contains detached
primitive dictionaries and hashes, not a native result or distance vector.
Weakrefs check destruction where the binding supports them; ownership release
itself uses ordinary Python reference removal, not a binding-specific release API.
Exceptions retain formatted traceback text, while exception frames/contexts are
cleared to release results. A solve exception has T0 but no invented T5. There are
no FINGERPRINT or RELEASE RPCs. There is no fallback algorithm.

Cohort A's prescribed clock is external `perf_counter_ns`. The dormant native
clock retains ns ticks and a representation ratio of 1/1. This is not measured
resolution. Clock mapping, effective quantum and calibration remain null/PENDING;
T1–T4 remain null. Original `query_seconds` is preserved separately without
subtracting it to attribute overhead. Tests use only deterministic fake ticks.

## Exact correctness bytes

Distances: SHA-256 of every little-endian binary64 double in the original sorted
vertex order. +Infinity means unreachable; reject NaN, -Infinity and negatives;
preserve the sign bit of zero. No display rounding.

Paths: exactly `sha256(json.dumps(paths, sort_keys=True).encode())`, using original
default spaces/ASCII/Infinity encoding, in the four original oracle-target order.
Individual target hashes apply the same JSON convention to each original path
object. IPC summaries encode distance as little-endian hex, so IPC itself has no
nonfinite JSON values. Historical aggregate hashes are computed before that IPC
conversion. Targets:

| Region | Original first four oracle targets |
| --- | --- |
| small | 4882417790, 4884113463, 12920916868, 1745247877 |
| medium | 7201534508, 614039683, 9234315058, 711435368 |
| corridor | 2031420000, 6138559542, 587612283, 711435368 |

Full deterministic work excludes only query_seconds, preprocessing_seconds and
profile; retains implementation string, frontier counters and materialization.
Its SHA uses sorted keys and compact separators. The separate historical P1
projection also excludes label_nodes_materialized, as native_ab_benchmark.py did;
the P2 projection retains it, as paired_source_probe.py did. Never silently discard
a missing counter. Profiles must be disabled; materialized == label_updates+1 <=
created. Parent validation verifies work/path hashes and cross-variant equality
for each frozen position/occurrence/phase. These structural and differential checks
are not an independent shortest-path proof. Historical correctness gates and future
independent runtime validation remain required.

## Execution and acceptance limits

All current responses are measurement_eligible=false and
confirmatory_target_eligible=false; fake outputs are synthetic=true. Warmups have
warmup_excluded=true. No approval comes from a response field. Actual native import,
dyld queries, constructor calls, solves and clock reads remain unreachable from
all supported CLI operations. The loader rejects profiler/tracer and DYLD/preload
environment injection before import (also behind the execution gate).

The original binary UUID/SHA and declared dependency names are verifiable without
loading. Loaded dependency UUIDs, actual import/runtime behavior and clock mapping
are deliberately untested. Shared-cache system libraries use loaded Mach-O UUID
identities, not fabricated standalone-file hashes. An import failure invalidates
the process; removing sys.modules is not a claim that dlopen can be undone.

Run only the fake adapter tests:

```sh
/Users/sallahuddin/Projects/BMSSP-task15-offline-reconstruction-jgt6c3vy/environment/bin/python -I -B research/task15_cohort_a_runner/test_adapter.py
```

The test launcher rejects bmssp_native imports via a meta-path guard. It tests
read-only binary/export identity checks, synthetic API construction and programmed
results (no shortest-path algorithm), fake timing/destruction, serial order,
import transaction failures, IPC failures and cluster invalidation. No performance
claim follows from these tests. Existing 32 runner and 107 harness tests remain
separate and unchanged.

Adding files extends the runner source closure used by new bundles. Historical
Phase 4 bundles remain immutable and must be checked with their exact archived
Phase 4 source; the validator's source check is not weakened or migrated. The
Phase 5 audit directory records that successful full lifecycle reference check.
