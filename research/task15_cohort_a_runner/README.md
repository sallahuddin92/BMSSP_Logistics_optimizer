# Task15 Cohort A synthetic controller/worker

This is functioning **synthetic lifecycle software**, not an enabled BMSSP
measurement runner. Production dispatch is absent. It never imports NumPy,
bmssp_native, graph-solving libraries or profilers, and never opens road graphs.
Every event is `synthetic: true`, `measurement_eligible: false`. Synthetic
fingerprints describe artificial objects, not distances or BMSSP correctness.

## Run

Use Python3.11, preferably the verified external interpreter. Outputs must have
an existing external parent and a fresh exclusive destination outside protected
source/evidence/cache/environment roots.

```sh
PY=/Users/sallahuddin/Projects/BMSSP-task15-offline-reconstruction-jgt6c3vy/environment/bin/python
"$PY" -I -B research/task15_cohort_a_runner/run.py plan
"$PY" -I -B research/task15_cohort_a_runner/run.py self-test --output /absolute/new/external/tests
"$PY" -I -B research/task15_cohort_a_runner/run.py synthetic-run --output /absolute/new/external/full
"$PY" -I -B research/task15_cohort_a_runner/run.py validate-bundle --bundle /absolute/new/external/full
```

Only `plan`, `self-test`, `synthetic-run` and `validate-bundle` exist. There is
no real/native/calibrate/collect/profile/analyze/promote/resume operation or
backend/environment-variable override. `production_backend()` always rejects.
`--unit` selects one existing A unit for a **subset synthetic test**, not a new
scientific schedule. Arbitrary executables, import paths and shell commands are
not accepted. The child argv is the controller's Python, `-I -B`, the fixed
worker source path, and `serve-synthetic`; no shell. Child Python/loader
redirection variables are removed with an environment allowlist.

## Frozen semantics

The unchanged harness0.3.0 validates protocol1.3, compiles the complete228-unit
plan and enumerates its existing queries. The controller extracts A by cohort
identity, not baseline/candidate names, and reconciles all64A units and41472
records against the committed v1.1 payload/query oracle preserved through v1.2
and v1.3. No seeds, permutations, source occurrences or query IDs are regenerated
as a new acceptance oracle. Worker-side per-variant identities are independently
computed from the frozen original-position/occurrence rows and stable namespace.

All16 primary phase slots remain in `session-slots.json`. Eight B slots are
explicitly NOT_EXECUTED / SCIENTIFIC_GATE_PENDING. Relative calendar windows,
minimum separations and idle requirements are retained as **not waited** metadata.
A fast synthetic run is never a completed eight-session scientific experiment.

Each cluster creates a fresh pair in its startup order. Both workers prepare
three structural placeholder graphs in the fixed preparation order before jobs.
They reuse those placeholders only within this cluster. P1 has a separate driver:
8warmups immediately followed by100targets for the first frozen variant, then
that batch for the second. P2 warms both in startup order, then sends and awaits
one request at a time in each position's frozen AB/BA order. No concurrent query
exists across the pair. Real graph loading is unavailable.

## Lifetime and IPC

`wire.py` implements version1 closed request/response objects, canonical UTF-8
JSON and four-byte network-order lengths, maximum65536body bytes. Duplicate
keys/nonfinite numbers/alternate encodings/unknown fields/invalid types are
rejected. Protocol/session/unit/variant/query/phase/region/execution/original
source occurrence/requestID/request and response sequence are bound and checked.
Command-specific request data and response data are closed. The fixed operation
set is HELLO,PREPARE,QUERY,FINGERPRINT,RELEASE,SHUTDOWN. `--fault` only selects
predefined synthetic defects, never executable code or a real backend.

Workers model PREPARED,WARMED,READY,TARGET_ACTIVE,TARGET_RETURNED,
RESULT_RETAINED,POST_TARGET_FINGERPRINTED,RESULT_RELEASED,CLUSTER_COMPLETE.
Warmups also have explicit WARMUP_ACTIVE/WARMUP_RETURNED states. QUERY retains
its artificial result through the conceptual return; FINGERPRINT is a separate
request outside the conceptual active region; RELEASE clears both the result
and independent Python copy before another query. Weak references verify the
previous object is gone. No T0/T5 or CPU endpoint is sampled. `time.monotonic`
in the pipe supervisor is exclusively an operational timeout deadline; it is
not recorded or interpreted as query latency, clock precision or calibration.

The original production IPC/output overhead remains an unimplemented future
measurement contract: this development protocol uses separate synthetic
fingerprint/release commands to expose ownership for testing. It does **not**
claim to implement the frozen real one-response-per-query measurement path.
A future separately reviewed adapter must perform the same lifetime/fingerprint
work without these synthetic debug commands and cannot be enabled by an option.

## Failures and evidence

A failure invalidates the entire paired cluster: all regions, variants, targets
and warmups. No query is salvaged for measurement. Partial records, stdout wire
bytes, stderr diagnostics, requests/replies, states and original error codes are
retained. There are no retries, replacement trials or mid-cluster continuation.
The run stops after the first invalid cluster and lists all remaining units as
NOT_EXECUTED. A real SIGINT/SIGTERM follows the same cleanup/retention path.
Only owned children are terminated/reaped; repeated CLI interrupts do not skip
cleanup. Exit status is verified before any successful cluster seal.

Query records buffer per region as the frozen contract requires. Graceful
failure flushes the partial region for diagnosis. Streams are fsynced at region/
cluster boundaries. Every bundle starts with an IN_PROGRESS manifest; payloads
and final receipts use exclusive creation, fsync and an atomic no-replace link.
A COMPLETED marker is written last only after structural/worker completeness.
Failed/interrupted runs receive FAILED evidence, never a successful marker.
A hard controller/host crash may leave an unsealed directory (and lose buffered
current-region rows); it remains incomplete and cannot be resumed or accepted.

Validation checks the exact file inventory and hashes, immutable source locks,
query oracle, cluster markers/verdicts, blocked B slots and exit/cleanup records.
It also replays every request/reply and synthetic ownership transition serially,
checks raw stdout against replies, and rejects resealed but contradictory source
or lifetime records. It never executes a worker or any native backend.

`self-test --output` retains successful/failed subprocess execution bundles in
an adjacent `-executions` directory plus the test report. Disposable mutations
operate only on copies. Tests cover closed framing, actual subprocess faults,
P1/P2, output corruption, whole-cluster invalidation and actual signal cleanup.
Changing source changes its lock; run final acceptance with the final source.

## Future gates

The A/B schedule issue, scientific/environment acceptance, G8 diagnostics,
host/runtime verification, clock calibration and real collection permissions
remain separate. The unavailable production boundary is documented, not
implemented: no .so loader, real solve call, clock endpoints or enabled adapter
exists here. This task changes no frozen documents or existing harness files.
