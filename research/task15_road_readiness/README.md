# Phase 7 — fixed real-road correctness readiness

ENGINEERING_ROAD_CORRECTNESS_ONLY · NOT_TASK15_COLLECTION · MEASUREMENT_ELIGIBLE_FALSE

This standalone engineering executable does not alter the protocol, original native
binaries, BMSSP algorithm, production adapter, experimental controller or execution
gates. It never calls the Phase 6 native smoke campaign. It reuses its read-only host
preflight, exact-path import transaction, mapped dependency checks and weakref helpers,
plus the Phase 5 strict frozen export loader. No native dispatch through the dormant
production worker is enabled.

## Single bounded campaign

```sh
/Users/sallahuddin/Projects/BMSSP-task15-offline-reconstruction-jgt6c3vy/environment/bin/python -I -B research/task15_road_readiness/run.py run-fixed --output /FRESH/EXTERNAL/EVIDENCE
```

There are no graph, source, target, binary, executable, benchmark, profiling or
collection overrides. The only road regions are small, medium and corridor in that
order. The only selected source is original position zero, occurrence one, in the
frozen v1.3 protocol array. Original source-list canonical SHA, snapshot, GraphML,
native text, fixture manifest and original query-capture hashes are checked. The
parser preserves original vertex order, every directed parallel edge and the parsed
binary64 weights; no application/OSM graph rebuild is used.

The parent computes exactly one heapq Dijkstra SSSP per original graph (three total),
before starting either native child. The independent implementation is in
`roadcheck/oracle.py`: ordinary directed adjacency, duplicate queue entries with
stale-entry rejection, checked finite nonnegative weights and binary64 sums. No
BMSSP output participates in oracle construction. Unreachable distances remain
positive infinity, serialized as exact little-endian bytes, never invalid JSON.
Oracle files include original vertex IDs, all distance bits and full vector SHA.
Their exact file identities are pinned in the campaign record consumed by children.
Tiny fake unit tests may exercise this oracle; they do not query original road data.

Each original variant runs in its own fresh isolated CPython 3.11 arm64 process,
using the fixed existing local interpreter and protocol-derived extension path.
Original SHA is checked before/after import, mapped extension UUID must match,
and actual loaded dependency path/install name/arm64/UUID is verified. Baseline and
candidate never share an interpreter. The source and region budget is fixed to
three attempts in each child. Durable launch/child claims prevent retry/reuse within
this campaign. No automatic retries or source replacements exist. Output directory
reuse is rejected. A later campaign requires separate authorization.

A child constructs each exact NativeGraph and BMSSP2025Engine, calls
`solve(source, profile=False)` exactly once, validates, and releases it before
proceeding. There is no warmup. A failing result stops that child; the parent stops
the campaign without launching the next variant. Earlier observations and complete
error/exit evidence are retained, with BLOCKED status rather than partial PASS.
A fixed process timeout contains hangs; no process/query durations are recorded.

## Exact correctness and evidence

Every original-order native distance is compared bit-for-bit to the independent
oracle. All mismatching vertices and expected/actual bits, full vector SHA and first
difference are retained. Reachability, source/storage identity and the four original
protocol path targets are checked. Paths must have original directed edge IDs and
orientation, no cycles, exact predecessor-distance consistency, exact path sum, and
oracle-shortest cost. Equal-cost alternative edge sequences are accepted. Both
variants must agree with the oracle and each other; non-timing work counters are
also reconciled. No tolerance-based or display-rounded pass exists.

Native timing fields are dropped immediately from returned diagnostic dictionaries
before retained copies or serialization; profile duration fields are dropped too.
Required counters, materialization and zero profile call counts remain. No external
T0/T5, performance clock, distribution, speed comparison, calibration or scientific
session is implemented. Ordinary subprocess deadline machinery is containment only.

DistanceResult remains owned during inspection, then native result and Python vector
copies are released before the next region. Weakref death is checked where supported;
unsupported weakrefs are explicitly reported. Graph and engine references are also
released and process exits/reaping retained. These observations are not a proof of
complete native-memory reclamation or general leak freedom.

Each JSON event/receipt is labeled engineering-only and nonmeasurement. Journals
append with fsync; completion markers hash the exact payloads. Original loader errors,
traceback text, source/region/binary identity, oracle/native fingerprints and mismatch
path/counter evidence survive failure. The parent's boundary is whole-campaign stop,
not a best-effort loop through invalid results.

## Regression closure and negative controls

`regressions.py` executes the three original deferred methods unchanged, with native
imports denied. Full existing adapter35, runner32, harness107 and Phase6 fake22 suites
then execute through their original entry points. They are not replaced by subsets
or altered expectations. Only Phase6 `self-test` is invoked, never its `run-fixed`.

`run.py self-test` runs the new tiny fake-fixture controls: independent directed and
parallel-edge oracle behavior, unreachable vertices, equal-cost paths, exact-bit
mismatches without tolerance, reversed edges, source/storage mismatch, profiles,
missing counters, mutated oracle/source identity, invalid binary64 values, bounded
source/region ordering, forbidden command overrides and the unchanged production gate.
No original native solve is part of these tests. Temporary fixture mutations never
change an original artifact.

Passing this fixed source on three roads is bounded correctness evidence only. It
does not establish all-source correctness, complete algorithm proof, performance,
Task15 scientific acceptance or approval for production routing.
