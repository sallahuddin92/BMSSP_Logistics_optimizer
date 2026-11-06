# Task 15 measurement harness — Phase 2 static integration

Version **0.2.0**. Standard-library Python 3.11+ package; no installation or network
is required. Production BMSSP, bindings, API, existing tools and all frozen protocol
files are untouched. This package has **no execution adapter**: no native binding
import, solver dispatch, worker launcher, calibration or profiler path exists.

The user supplied conditional independent approval for harness preparation only.
This is not calibration, collection or promotion approval. Actual G8, diagnostics,
permissions, clocks, compiler flags, allocation and storage gates remain pending.

## Command reference

Run from the repository root, using an explicit **new external output directory**:

```sh
PYTHONPATH=research/task15_harness python3 -m task15_harness verify-protocol --output /NEW/EXTERNAL/protocol
PYTHONPATH=research/task15_harness python3 -m task15_harness validate-schedule --output /NEW/EXTERNAL/schedule
PYTHONPATH=research/task15_harness python3 -m task15_harness inspect-identities --output /NEW/EXTERNAL/identities
PYTHONPATH=research/task15_harness python3 -m task15_harness plan --with-queries --output /NEW/EXTERNAL/plan
PYTHONPATH=research/task15_harness python3 -m task15_harness prepare-manifest --state DRAFT --output /NEW/EXTERNAL/draft
PYTHONPATH=research/task15_harness python3 -m task15_harness prepare-manifest --state AWAITING_APPROVAL --output /NEW/EXTERNAL/awaiting
PYTHONPATH=research/task15_harness python3 -m task15_harness validate-manifest --manifest /EXISTING/EXTERNAL/awaiting --output /NEW/EXTERNAL/validation
PYTHONPATH=research/task15_harness python3 -m task15_harness inspect-storage --destination /EXISTING/EVIDENCE/VOLUME --output /NEW/EXTERNAL/storage
PYTHONPATH=research/task15_harness python3 -m task15_harness simulate --interrupt-after 20 --output /NEW/EXTERNAL/simulation
PYTHONPATH=research/task15_harness python3 -m task15_harness self-test --output /NEW/EXTERNAL/tests
```

Output parents must exist; the final directory must not. Paths above are examples,
not created by documentation. `--repo` selects an existing checkout with the pinned
frozen files; it cannot select another protocol/version/hash. `--skip-external`
records NOT_CHECKED and cannot reach STATIC_VERIFIED. Omitting `--output` prints
small reports; `simulate` always requires an exclusive output bundle. `plan` without
`--with-queries` writes the complete compact plan plus exact counts; adding it
streams every structural query record. `simulate` consumes that schedule using
structural events only; `--fail-query` selects a synthetic failure ID obtained from
the plan. Every simulation event says SYNTHETIC_CONTROL_PLANE_TEST and contains no
measured latency/CPU/allocator values. No experiment retry/resume interface exists.

`collect`, `calibrate`, `run-benchmark`, `trace`, `profile`, `optimize` and `promote`
are rejected as UNSUPPORTED_OPERATION. No option or environment variable enables
them. Even valid STATIC_VERIFIED/AWAITING_APPROVAL manifests always say calibration,
execution, promotion and future_execution_eligible **false**, with no approval
signatures. The state machine cannot create any later state in this implementation.

## Modules

| Module | Responsibility |
| --- | --- |
| `protocol.py` | Strict immutable frozen loader, canonical/file/parent/ledger hashes |
| `integrity.py` | Duplicate/nonfinite JSON rejection, closed schema checks, streaming SHA |
| `schedule.py` | Independent stored-order validation and actual per-position/session counts |
| `artifacts.py` | Binary/input/index/source identities, Git metadata, disk observation and optional private hard-link probe |
| `planning.py` | Deterministic compact plan and lazy per-query records; no seed regeneration |
| `manifest.py` | Deterministic manifests, source/repository/identity locks, restricted states |
| `output.py` | Exclusive directory/file publication, completion integrity marker, interrupted audit |
| `simulation.py` | Synthetic visits/failures/interruptions, whole-cluster invalidation, no retry |
| `g8.py` | Conservative SYNTHETIC fixture comparison only; actual G8 remains pending |
| `testing.py`, `tests/` | Isolated static/synthetic test discovery, classified negative evidence |

## Frozen authority and schemas

Protocol identity is
`c41e45bccb68abdf03bab40ea793837a7f508fde17634c1aa8b358a3d82fceb0`.
The complete v1.0 -> v1.1 -> v1.2 document chain is verified without edits. Normal loading
never imports the amendment generator or reconstructs any order from a seed.
`schemas/protocol-1.2.0.schema.json` is a closed structural schema for all approved
fields; canonical identity additionally freezes all scientific strings/values.
Independent semantic checks evaluate each stored execution index -> original
position -> source ID; source occurrence identities remain distinct. The schema
file is data, not an executable generator. `$schema` URLs are metadata only and are
never fetched. `manifest-2.schema.json` and semantic verification define manifests.
See [schema/state details](specs/control-plane-schema-v2.md).

The source identity is separate from the protocol: streaming SHA-256 over each
package `.py/.json/.md/.toml` file, sorted relative names, then canonical hash of that map.
Python bytecode/cache and mutable external outputs are excluded. Manifest provenance
records actual Git revision, dirty status, runtime trees and source hashes; a dirty
preparation is distinguishable from a committed one. Content hashes are integrity
locks, not cryptographic approval signatures. Modifying source or repository state
makes an earlier manifest stale; prepare a new exclusive bundle, never overwrite it.

## Exact plan semantics and resolved ordering

Primary A/B phases follow the eight sessions' frozen cohort order and the embedded
base-row order filtered by session. P1 emits one whole variant batch per region;
P2 emits both variants at the same original position using the execution-indexed
order array. Warmups are the original eight positions, not shuffled replacements.
C filters the stored permutation to its historical 41-position subset. D includes
the fixed mode/condition order and represents both required untimed hot solves in
the CPU/cache mode. Every record identifies expected production identity; diagnostic
binary identity is **null/PENDING_DIAGNOSTIC_BUILD**, never invented.

Protocol v1.2.0 freezes SESSION_END ordering. The authoritative `units` array
contains all 228 units: the unchanged 128 primary A/B units, then 100 diagnostic
condition blocks ordered exactly by the resolved protocol sequence. Sessions 0/2
have 26 blocks each; sessions 1/3 have 24. Each session's companions follow its
main diagnostics. No companion is globally appended after session 3.

Original main and companion lane IDs remain in `diagnostic_source_lanes` for
provenance. `stack_companions` remains a four-unit provenance view, **not additional
work**; consumers must enumerate `units` only. Each diagnostic unit includes its
exact `resolved_condition_block`, source-lane indices and session reference.
Plan schema **3** is closed and includes explicit `unit_order`, active protocol,
resolved-order and stable source hashes, namespace, false dispatchability, pending
scientific approval and a canonical plan identity. Resolving design order does not
approve scientific execution. No dispatcher exists.

## Identity, storage and observations

Hashing `.so` files reads bytes only; it never loads them. Identity results are
VERIFIED/MISMATCH/MISSING/UNREADABLE/NOT_CHECKED. File changes during hashing cannot
be certified. `inspect-identities` exits nonzero if any required file is not verified.
Standalone byte equality does not prove compiler flags or original experiment
execution. Those require future host checks (N5). Harness source hashes are recorded
for review, not treated as already independently approved.

`inspect-storage` requires an explicit existing evidence destination for an actual
check; absent destination is NOT_CHECKED. It reports destination/device/free bytes
and STORAGE_CAPACITY_VERIFIED or INSUFFICIENT_CAPACITY against **512 GiB**. It does
not assume the root volume or reserve space. Static calculations preserve 4M
operation-events/query, 128 bytes/event maximum, 41 selected positions,
335,872,000,000 worst timed-C bytes and equal paired-buffer footprints. No buffers or allocator probes are created. The optional `--check-hardlinks`
flag creates a tiny private temporary directory in the explicit destination,
links a small private file, verifies it and removes only its own probe files.
Protected repository/evidence roots cannot be probed. Failure is reported as
UNSUPPORTED_OR_DENIED; this is a point-in-time capability check, not a guarantee. A failed storage/capacity gate blocks future C,
not documentation or control-plane static verification. Instantaneous disk space
can change; a future authorized stage must recheck it.

## G8 and N1

[The detailed ARM64/Mach-O specification](specs/G8-ARM64-v1.md) defines extraction,
relocation normalization, register/immediate/frame preservation, CFG and inline
coverage, alignment/page reporting and conservative I/L/M rules. Actual G8 remains
PENDING. Class L needs independent risk approval; Class M blocks the cohort.
The synthetic helper cannot certify real code generation.

[The N1 note](specs/N1-event-frequency-note.md) is expressly non-confirmatory. Event
counts alone do not establish unusual frequency or causation. It changes no frozen
threshold, scheduler evidence requirement, control or acceptance rule.

## Tests, durability and limits

`self-test` discovers only this directory's tests. It requires the complete mandatory
case set and rejects missing tests/skips as a reduction in scope. Tests include all
25 requested negative categories, actual error-code/status comparisons, full plan
ID/position enumeration and synthetic I/L/M fixtures. No native test suite/build or
binding executes. Mutable logs, counts and expected/observed negative controls go
outside Git. Static tests cannot certify BMSSP correctness or measurement accuracy.

Files publish atomically by exclusive creation + hard link after fsync. The directory
is exclusively reserved first; COMPLETED.json publishes last with file hashes and
a final directory fsync. Consumers require that marker and reject INTERRUPTED.json.
A crash can leave an incomplete directory, which is retained and cannot be reused.
This is a completion-marker transaction, not a claim of whole-directory rename
atomicity. Same-user malicious file edits are not prevented by unsigned hashes;
validation detects stale content. No automatic cleanup removes prior evidence.

The old [proposed clarification](specs/proposed-ordering-clarification.md) is historical.
The separate frozen [v1.2.0 amendment](../../docs/task15_tail_attribution_preregistration_v1.2.0.md)
now resolves the design order, with scientific approval still pending.

## Preserved Phase-1.1 integrity controls

Session identity schema remains **2**, while the complete plan is schema **3**. Every unit, companion, query and per-cluster
synthetic event carries `session_kind` (PRIMARY or DIAGNOSTIC), `session_id`
(within that domain), `schedule_ref_session` (the frozen referenced row's primary
session), and `session_key` (`PRIMARY/0` versus `DIAGNOSTIC/0`). Diagnostic indices
are preserved even when they differ from their reference sessions. Cluster IDs
include the namespace; query and plan hashes consequently change. The session
projection is validated by `schemas/session-2.schema.json` and exact frozen plan
reconciliation. The summary event reports its observed `session_keys` inventory.

`expected_binary.planned_binary_sha256` replaces the misleading loaded-hash field.
Every record says `load_status: NOT_LOADED`; the production plan status is
PLANNED_PRODUCTION_IDENTITY. Diagnostic planned hashes remain null pending builds.
`validate-manifest` returns VALID_STATIC_MANIFEST_STRUCTURE plus
`external_identity_verification`: NOT_CHECKED, ALL_VERIFIED, or FAILED. An unchecked
DRAFT can be structurally valid; it cannot transition to STATIC_VERIFIED.
STORAGE_CAPACITY_VERIFIED is retained for compatibility and always accompanied by
`verification_scope: POINT_IN_TIME_FREE_SPACE_ONLY` and `space_reserved: false`.
No status grants execution authorization.

Completion markers follow the closed `schemas/completion-1.schema.json` plus
semantic checks for safe lowercase basenames, lowercase 64-digit hashes, exact
payload inventory, regular non-symlink files and distinct payload inodes. Supported
sets are manifest-only, report-only, report+plan (optionally queries),
report+synthetic-events, and tests.json+tests.log. Explicit fixture consumers may
supply their own exact inventory. Manifest consumers require manifest-only and
parse the exact bytes whose digest they verify. Missing, unlisted, aliased,
interrupted or modified payloads fail closed with classified errors. Unsigned
hashes remain integrity checks, never authentication or approval signatures.

Strict JSON rejects overflow exponents such as 1e999 as JSON_NONFINITE. Fixed
read-only Git queries use absolute repository roots and a controlled environment,
ignoring inherited GIT_* overrides and global/system Git configuration with a
stable C locale. This does not protect against every same-user local attack.

The complete independent P2 target oracle reconciles all 19,200 Cohort A targets
and all 41,352 diagnostic targets, retaining execution-indexed subset mapping.
It independently counts 50/50 per trial, 16/16 per original position, and 2/2 per
position/session for each region. Mutated emitted pairs, positions, variants,
orders, source occurrences, missing and duplicate records must be detected.
The advisory AST lint checks simple aliases and attributes with a narrow exception
for the controlled Git metadata call. It is not a proof of absence of execution
facilities or dynamic Python behavior. Neither test serialization nor companion
placement grants cross-lane execution order.

Old 0.1.0/0.1.1 manifests are stale under this upgraded harness; do not edit historical
bundles. Manifest schema **2**, harness version **0.2.0**, source, active protocol,
resolved-order and plan identities enforce the new contract. All frozen documents
remain byte-identical; v1.2.0 is the explicitly selected active protocol.

## Phase 2 loader, identities and validation

Only exact protocol v1.2.0 is active. The loader verifies canonical identity,
file-byte SHA, preregistration bytes, ledger canonical identity and file bytes,
all eight historical/current files, parent canonical identities, ledger changed
paths, resolved order reconstruction/hash and false authorization. No `--repo`
override can substitute another version or alter scientific values. Protocol
objects remain immutable and return defensive copies. The production harness
imports neither the amendment generator nor its validator/tests.

Manifest schema **2** binds active canonical/file/Markdown/ledger identities,
resolved order, stable source schedules, query namespace, revised plan/unit-order
hashes and current source/repository/artifact identities. State transitions remain
DRAFT -> STATIC_VERIFIED -> AWAITING_APPROVAL; no scientific approval is inferred.
Identity inspection now covers **24 artifacts**, because all eight protocol-chain
files are included alongside the original binaries, graph inputs and evidence
indices. VERIFIED remains byte identity only, never binary loading or calibration.

Query IDs retain namespace
`6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f`.
Their ordered key is namespace, session_key, unit ID, phase, region, execution
index, original position, variant. Active `protocol_sha256` is separately v1.2.0;
records also expose `protocol_version`, `query_identity_namespace_sha256` and
`resolved_diagnostic_order_sha256`. Every other scientific record field remains
identical to v1.1.0. The complete pre-edit ledger is archived outside Git. The
immutable fixture `tests/fixtures/v1.1-query-oracle.json` stores ordered per-unit
scientific payload and ID fingerprints, full primary descriptors, population hash,
source revision/version/hash and normalization, captured before any loader edit.
It is a frozen test oracle, not generated mutable test-run evidence.

Tests independently compare all 138,696 records and their payloads against that
fixture; they do not derive expected results from the upgraded planner. Mutation
controls for emitted occurrence/provenance are checked by the independent ledger
verifier; namespace/order/manifest/duplicate controls also exercise production
validation. Full simulation checks every unit, active provenance and whole-cluster
invalidation. All original F-01 through F-11 controls remain, with only version and
explicitly authorized ordering expectations adapted.

The frozen amendment validator's semantic `verify_order` function is used as an
independent test oracle only. Its original full CLI pins the old harness tree and
therefore is historical evidence rather than a validator for the upgraded harness;
it is unchanged. New current harness tests verify runtime preservation separately.
Independent scientific approval, diagnostic builds, G1-G10/G8, compiler/SDK/Mach-O,
host permissions, clocks/overhead/observer effects/event capacity, >=512 GiB storage
and separate calibration/collection authorization all remain pending.
