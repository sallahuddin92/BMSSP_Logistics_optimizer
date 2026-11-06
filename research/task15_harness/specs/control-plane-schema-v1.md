# Control-plane configuration and manifest schema — v1

No runtime scientific configuration overrides exist. Protocol ID/version/canonical
hash, amendment hash and frozen file identities are pinned in the loader. Strict
JSON rejects duplicate keys, NaN/Infinity and overflowing exponents, non-UTF8, missing/unknown declared keys,
wrong primitive types and inputs larger than 8 MiB. The complete bundled structural
schema plus independent schedule validation runs before canonical acceptance.
Each immutable Protocol object owns bytes and returns defensive copies. Even direct
construction validates the document; no unvalidated mutable protocol object is used.

Manifest schema version1 has exact top-level keys: schema_version, kind, state,
protocol, repository, harness, plan, identities, requirements, authorization,
provenance, transitions, identity_sha256. Closed nested structures and semantic
checks bind the current plan, source, repository and artifacts. Requirements must
exactly match the approved protocol's pending clocks/build/preflight/approval rules.
Changing a plan or pending requirement and repairing its hash still fails validation.
A manifest hash is canonical SHA-256 after removing only identity_sha256. No current
time/random ID is inserted: identical observation inputs serialize identically.
An identity or free-space observation is not guaranteed stable across later checks.

State transitions implemented now:

```text
DRAFT -> STATIC_VERIFIED -> AWAITING_APPROVAL
```

Both transitions require live static artifact/runtime checks. Every state keeps
calibration/execution/promotion/future eligibility false and signatures empty.
STATIC_VERIFIED means static control-plane checks, not successful preflight/G8 or
measurement readiness. The schema names future states for documentation only:
APPROVED_FOR_CALIBRATION, CALIBRATION_COMPLETE, APPROVED_FOR_COLLECTION,
COLLECTION_COMPLETE, INVALID. The semantic validator and transition API reject all
of them in Phase1. Failure reports and synthetic INVALID cluster verdicts are not
manifest states or approval transitions. No CLI flag/environment override exists.

Provenance describes actual static generation/revision and the user's report of
conditional harness preparation approval; no reviewer signature or calibration/
collection approval is manufactured. Prepare a new bundle after source/repository
changes; prior manifests are never edited. The bundle marker detects file mutation
and incomplete creation independently from the manifest's semantic identity.

A future measurement implementation, actual approvals, instrument schemas and any
necessary protocol clarification require separate authorization/review. Frozen
scientific values cannot be changed through manifest fields, fixture input or JSON
schema configuration. Synthetic data carry SYNTHETIC_CONTROL_PLANE_TEST and cannot
be accepted as future performance evidence.

Phase-1.1 uses plan schema version 2 and the closed session identity projection in
`../schemas/session-2.schema.json`. Reference sessions and diagnostic domain
sessions are independent. Query/cluster identities include the session namespace.
Manifest envelope schema version 1 remains compatible structurally; harness version
0.1.1, source and plan identities intentionally invalidate older observations.
Validation returns VALID_STATIC_MANIFEST_STRUCTURE and explicit current external
identity verification; an unchecked DRAFT has NOT_CHECKED external verification.
Completion marker schema version 1 is now enforced together with an exact consumer
payload contract and classified semantic filename/hash/reference checks.
