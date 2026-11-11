# Phase 8 — fail-closed static preflight

This standard-library package verifies engineering evidence and produces a separate
preflight extension receipt. It cannot import original BMSSP extensions, invoke a
native query, read timing endpoints, run calibration, grant approvals or dispatch a
scientific session. Existing harness/runner/algorithm/protocol/gates are unchanged.

```sh
/Users/sallahuddin/Projects/BMSSP-task15-offline-reconstruction-jgt6c3vy/environment/bin/python -I -B research/task15_preflight/run.py verify --phase7 /Users/sallahuddin/Projects/BMSSP-task15-phase7-road-6dgxya2t --output /ABSOLUTE/NEW/EXTERNAL/OUTPUT
```

Only `verify --phase7 ABSOLUTE --output ABSOLUTE` and static `self-test` exist.
There are no executable/binary/graph/source/profiler/approval/environment overrides.
`collect`, `calibrate`, `benchmark`, `profile`, `run-real`, `analyze-confirmatory`,
`approve`, `promote` and `resume` are rejected. Meta-path and Python audit guards
reject native imports/dlopen and unapproved subprocess dispatch before execution.
Subprocesses are restricted to fixed read-only host commands and existing read-only
Git metadata queries. Subprocess deadline machinery is containment, not a query
clock. No timing endpoint, native graph construction, solve, Dijkstra rerun or
Phase6/7 native campaign is invoked. Self-tests mutate disposable receipts only.

## Evidence trust and reconciliation

The original Phase7 audit-index, campaign completion and regression completion
marker SHA values are pinned from delivered Phase7 evidence. These are immutable
integrity anchors bound to the Phase7 Git delivery, not scientific signatures or
protection against a same-user attacker who edits this verifier's source. A changed
PASS string or rehashed marker cannot replace anchored historical evidence.

Validation also independently reconciles semantic contents: strict duplicate-key /
nonfinite JSON rejection, closed campaign inventory, per-file hashes, distinct
payload inodes, protocol/binary hashes, original extension UUIDs, recorded actual
loaded dependency UUIDs, oracle attempts/files/vector hashes, graph dimensions,
snapshots, original-position-zero selections and occurrences, journal order, six
native attempts, 80,068 recorded distance comparisons, reachability, 24 selected
paths, work/profile/materialization counters, releases, separate PIDs, exit zero,
no retry/replacement and engineering-only measurement exclusion. Stored selected
paths are revalidated against exact frozen directed edges and full independent
oracle costs, accepting equal-cost alternatives. No shortest-path query is rerun.
Phase7 did not retain native full vectors; this verifier checks the anchored native
comparison receipts/hashes against stored complete oracle vectors. It does not
pretend to recompute absent native vectors or establish all-source correctness.

All original Phase7 regression logs/counts and completed structured runner/harness
test bundles are verified. Source inventories are checked against the live checkout;
stale source, altered/redirected input, missing environment and forged approvals
fail closed. Original Phase7 files remain in place, read-only. Historical Phase6
negative evidence and all completed research reviews are not rewritten/reopened.

## Existing manifest integration

The actual frozen v1.3 loader, identities/environment/source/repository inspectors,
plan compiler/validator, storage inspector and manifest preparer/validator are
reused. Exact graph paths and symlink redirections are independently checked.
The scientific `manifest.json` uses unchanged schema3 and original allowed
DRAFT -> STATIC_VERIFIED -> AWAITING_APPROVAL transitions. No APPROVED_FOR_CALIBRATION
state exists. The extension is separate and never inserts fields into that manifest.
A receipt is stale when repository/worktree/source identity changes; use a new
exclusive output, never migrate or overwrite a historical manifest.

## Host scope and readiness

Commands and exact return codes/stdout/stderr/errors record hardware/CPU/memory,
macOS/build, CPython ABI, compiler/version/hash, developer selection/SDK, vm_stat and
memory_pressure query, power/low-power settings, thermal warnings, filesystem,
process inventory and tracing tool discovery/version. No sudo, recording, power
sampling, settings change, app termination, build or instrument permission probe.
AC/low-power values are point-in-time observations. Memory statistics do not prove
C buffer/worker-footprint gates. Installed tools do not prove runtime permissions,
export units, event completeness or synchronization. Those remain PENDING.
Recorded loaded dependency identities are from Phase7, not a new extension load.

The prerequisite matrix copies the complete actual calibration specification and
adds cohort-specific rows for A external endpoints; B wall/thread CPU/mapping,
resolution, aperture, negative deltas and overhead; every instrument/permission/
export/loss requirement; G1–G10/G8 and independent Class L approval; count-only full
41-position coverage, four-million-event capacity, <=128-byte records, reservation/
prefault of two 512,000,000-byte buffers plus prepared-worker footprint/safety;
>=512GiB storage and 16GiB stop threshold; all independent acceptances and separate
calibration/collection authorization. Literal historical design thresholds remain
requirements, never newly collected metrics. Explicit unsupported interpretations
are retained as UNSUPPORTED, not passed or silently replaced.

Cohort A's baseline/candidate are two original A variants, not Cohorts A and B.
Missing diagnostic identities/G8 evidence blocks affected B/C/D diagnostics, not
original A artifact validity. Original-road evidence does not establish diagnostic
G2 equivalence for all 100 original positions. The full frozen eight-session A/B
and diagnostic plan is preserved; no A-only scientific schedule is manufactured.

## Closed outputs and failure semantics

Every extension uses `schema=preflight-extension-1`, an exact kind/data-field
inventory, static-only scope, measurement_eligible=false, calibration_authorized=false,
collection_authorized=false and scientific_acceptance=pending. `extension-1.schema.json` and `outputs.py` supply the
closed machine-readable schema and executable semantic validator. Each prerequisite has exact fields
and status in VERIFIED/PENDING/BLOCKED/UNSUPPORTED/NOT_APPLICABLE. The scientific
manifest remains its original separately validated schema.

Outputs include preflight-summary, Phase7 validation, protocol/plan/source identity,
original artifacts, environment, host/storage, cohort matrix, calibration matrix,
blockers/actions, scientific manifest plus reference/validation, hashes and the
existing harness COMPLETED marker. Hashes exclude themselves; the completion marker
covers hashes.json too. Exclusive creation, fsync, atomic no-overwrite publication
and exact inventory checks use the existing harness bundle writer. Completion means
static verification completed, not permission to execute. A BLOCKED technical result
retains error type, traceback and completed/untested stages; output failures retain
the harness INTERRUPTED marker. No missing requirement becomes a pass.

TECHNICAL_STATIC_PREFLIGHT_PASS means static foundations/host observations passed;
PARTIAL preserves observed host/storage limitations; BLOCKED means required evidence,
artifact, environment or identity validation failed. Calibration prerequisites and
scientific approvals remain separate even on static PASS. Implementation acceptance
does not require approvals for scientific collection or a calibrated host.

Run fake/static negative controls with the same interpreter and `-I -B .../run.py
self-test`. Existing 35/32/107 and Phase6/7 fake suites remain unchanged and run
separately; no native campaign is part of these regressions.
