# Phase 10 — one bounded historical provenance recovery

This small standard-library collector examines only a fixed, evidence-led source
allowlist. It never builds, loads or executes original/diagnostic BMSSP, benchmarks,
calibrates, records instruments, installs packages, accesses a network/cloud backup,
changes developer settings or deletes evidence/caches. Existing gates/protocol and
G1–G10/G8 remain unchanged.

```sh
/Users/sallahuddin/Projects/BMSSP-task15-offline-reconstruction-jgt6c3vy/environment/bin/python -I -B research/task15_provenance_recovery/run.py recover --output /FRESH/EXTERNAL/OUTPUT
```

Only `recover --output ABSOLUTE` and deterministic `self-test` are supported. Output
reuse is rejected. One actual collection is authorized; there is no retry/resume,
configurable search path, broader search, native query, build or approval operation.

## Finite evidence sources

The frozen protocol authenticates the pre-existing Task14 evidence-index SHA. The
collector verifies a fixed set of original baseline/candidate files against that
index: toolchain/initial/binary/source records, original compile databases, CMake
cache/compiler/configure metadata, build logs, link commands, binding object and
header dependencies, compiler-ID/ABI output objects, original extensions and the two
identified source archives. It inspects archive member names/claimed timestamps and
five exact source files without extracting arbitrary members. Sources are checked
against the original Git commits and archived source hashes. Historical versions,
paths and source/output artifacts are not promoted to tool executable hashes.

Only the original Task14 build-stage paths named by its initial/configure records
are checked for eight retained metadata/object files. The original Task6 venv paths
are used solely because original CMake/binding records reference them. The exact
Python launcher, pyvenv.cfg, pybind11 header/metadata/RECORD/CMake version file and
three Python headers are inspected without launching that interpreter or importing
packages. No reconstructed or unrelated package is substituted for missing originals.

Current CLT compiler/linker are hashed from complete file bytes. The exact original
SDK alias must resolve to the already identified CLT26.5 directory; ten named SDK
metadata/header/library files are hashed. This is an explicitly partial current SDK
inventory, not a fabricated complete SDK hash. The existing Phase9 reconciliation
file is a recent current observation only, never a Task14 historical anchor.
No Phase9 disassembly or broad toolchain discovery is repeated.

Four matching CLT package IDs are queried using pkgutil metadata and file listings;
only relevant listed paths plus listing hashes/counts are retained. Corresponding
.plist/.bom files are checked at three explicitly named standard receipt locations,
without traversing those directories. Package installation claims/versions and raw
receipt identities are current observations. A receipt alone cannot prove its
payload remained unchanged at the original build. No package/cache/download search
or installer verification is expanded beyond this finite set.

## Identity rules and trust

Every component record has closed fields for role/original path, historical version,
historical/current SHA, resolved current path, status, source artifact identities,
timestamp evidence, chain, limitations, continuity and contradictions. Statuses are
HISTORICALLY_VERIFIED, CURRENT_IDENTITY_VERIFIED, VERSION_ONLY, UNVERIFIED or
UNAVAILABLE. Absence of a hash is not an actual compiler mismatch or FAILED result.

Only exact pre-existing archive-backed production/source objects can receive
historical byte SHA in this collector. Their bytes/index/protocol/role are checked;
a boolean or a newly produced manifest's own hash cannot create an anchor. Compiler,
linker, SDK and dependency metadata hashes are labeled as hashes of the metadata,
not hashes of the components described. Current tool/header hashes are never copied
into historical_sha256. Matching version/path/mtime/package/RECORD does not establish
past byte continuity. A current SDK subset does not verify a whole SDK.

Original extension LC_BUILD_VERSION is read from authenticated bytes to reconcile
SDK, linker-tool and deployment-version declarations. This is version/interface
metadata, not an exact linker/SDK payload identity. Original source/command/binary
records are reconciled per variant. A shared historical toolchain is stated only
at the supported path/version/argument level, never as proven common past bytes.
Actual contradictory observations are retained with exact source/hash context.

Archive timestamps and package install times are claims recorded in their respective
sources. Current filesystem mtimes do not become independent historical witnesses.
The pre-existing unsigned protocol/archive chain establishes supported archive bytes,
not a notarized build-time attestation or protection against a same-user code editor.

## Durable stop and scientific decision

A STARTED receipt reserves the fresh output. An append/fsync journal preserves every
archive check before subsequent steps. A completed closed manifest includes exact
output hashes/source lock and all required component/reconciliation/negative-control
files. Publication is exclusive; failure retains FAILED.json and earlier journal
entries. The collector stops after this allowlist. A 16MiB payload cap and 64MiB free
minimum bound the small evidence output; the frozen C/D512GiB requirement is untouched.

If required tool/dependency historical hashes are unavailable, the exact verdict is
HISTORICAL_PROVENANCE_UNRECOVERABLE_WITH_AVAILABLE_EVIDENCE. Preserved original
binary/source hashes can still be historically verified; they do not recover missing
tool bytes. Do not run another search under broader paths/different filenames without
new independently identified evidence and authorization.

The concrete decision document separates Option A (hold until stronger original
anchors arrive) from Option B (independent review of a separately identified, fully
locked current toolchain plus a justified controlled equivalence/reproducibility
strategy). Option B may require an explicit protocol amendment and new approval
BEFORE diagnostic construction. This task makes no amendment/approval and does not
claim reproducible builds prove exact historical compiler identity. Current selected
SDK/header hashes alone are not a complete current-toolchain lock for Option B.

Run static negative controls with the same interpreter and `-I -B .../run.py self-test`.
Tests use disposable fixtures and static validation, not another recovery campaign.
All original fake/static regressions run unchanged; no native campaign is rerun.
