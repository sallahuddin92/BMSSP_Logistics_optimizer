# Task 15 measurement harness — Phase 1 control plane

Version **0.1.0**. Standard-library Python 3.11+ package; no installation or network
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
| `artifacts.py` | Binary/input/index/source identities, Git metadata, read-only disk inspection |
| `planning.py` | Deterministic compact plan and lazy per-query records; no seed regeneration |
| `manifest.py` | Deterministic manifests, source/repository/identity locks, restricted states |
| `output.py` | Exclusive directory/file publication, completion integrity marker, interrupted audit |
| `simulation.py` | Synthetic visits/failures/interruptions, whole-cluster invalidation, no retry |
| `g8.py` | Conservative SYNTHETIC fixture comparison only; actual G8 remains pending |
| `testing.py`, `tests/` | Isolated static/synthetic test discovery, classified negative evidence |

## Frozen authority and schemas

Protocol identity is
`6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f`.
Both v1.0 originals and the v1.1 amendment are verified without edits. Normal loading
never imports the amendment generator or reconstructs any order from a seed.
`schemas/protocol-1.1.0.schema.json` is a closed structural schema for all approved
fields; canonical identity additionally freezes all scientific strings/values.
Independent semantic checks evaluate each stored execution index -> original
position -> source ID; source occurrence identities remain distinct. The schema
file is data, not an executable generator. `$schema` URLs are metadata only and are
never fetched. `manifest-1.schema.json` and semantic verification define manifests.
See [schema/state details](specs/control-plane-schema-v1.md).

The source identity is separate from the protocol: streaming SHA-256 over each
package `.py/.json/.md` file, sorted relative names, then canonical hash of that map.
Python bytecode/cache and mutable external outputs are excluded. Manifest provenance
records actual Git revision, dirty status, runtime trees and source hashes; a dirty
preparation is distinguishable from a committed one. Content hashes are integrity
locks, not cryptographic approval signatures. Modifying source or repository state
makes an earlier manifest stale; prepare a new exclusive bundle, never overwrite it.

## Exact plan semantics and incomplete ordering

Primary A/B phases follow the eight sessions' frozen cohort order and the embedded
base-row order filtered by session. P1 emits one whole variant batch per region;
P2 emits both variants at the same original position using the execution-indexed
order array. Warmups are the original eight positions, not shuffled replacements.
C filters the stored permutation to its historical 41-position subset. D includes
the fixed mode/condition order and represents both required untimed hot solves in
the CPU/cache mode. Every record identifies expected production identity; diagnostic
binary identity is **null/PENDING_DIAGNOSTIC_BUILD**, never invented.

The frozen protocol supplies main diagnostic and allocator-stack companion lists
but does not define their cross-list interleaving. The plan retains **two ordered
lanes**, preserving each list/session/reference. Main-then-companion serialization
is not an assertion of execution order. This ambiguity must be independently
clarified before a future executable runner; no scientific amendment is silently
applied here. Fixed calibration requirements are preserved as pending manifest
gates, not invented calibration query orders. No calibration planner/runner is enabled.

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
335,872,000,000 worst timed-C bytes and equal paired-buffer footprints. No buffers
or allocator probes are created. A failed storage/capacity gate blocks future C,
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

The cross-list issue is recorded separately as a [proposed clarification only](specs/proposed-ordering-clarification.md).
No proposal has been adopted into the frozen protocol or into an executable order.
