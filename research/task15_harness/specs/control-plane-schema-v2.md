# Static control-plane schemas — Phase 2

Harness 0.2.0 explicitly accepts only frozen protocol v1.2.0. Protocol, session,
plan and manifest schemas are closed structural contracts, supplemented by exact
pinned identities and semantic checks. No scientific configuration override exists.

- `protocol-1.2.0.schema.json`: extends the historical closed scientific shape with
  resolved-order entries/blocks, original lane/session provenance, query namespace
  and the scheduling-amendment chain. Loader canonical/file/Markdown/ledger locks
  and source-derived reconstruction reject altered values even after resealing.
- `session-2.schema.json`: unchanged session identity projection. PRIMARY and
  DIAGNOSTIC indices remain separate from schedule_ref_session.
- `plan-3.schema.json`: all 228 units appear exactly once in `units` and
  `unit_order`; original lane ID lists and four stack_companions are provenance
  views. Diagnostic units carry their joined frozen resolved_condition_block.
  These views are never additional jobs. Plan identity excludes only its own
  identity_sha256 field. Validation requires exact deterministic expansion.
- `manifest-2.schema.json`: active canonical/file/Markdown/ledger canonical+file
  identities, schedule/order/namespace bindings, plan schema/identity/unit-order
  digest/counts, source lock, current repository, artifacts, requirements and
  transition provenance. The identity report has the same explicit protocol binding.
- `completion-1.schema.json`: unchanged strict bundle schema and exact consumer
  payload inventories. Parse exactly the manifest bytes whose hash was verified.

Manifest schema 1 remains a historical file only; the active validator uses schema
2. Old envelopes fail schema validation. Updating an envelope/resealing cannot
bypass exact active protocol, plan, order, provenance or source locks. Historical
bundles are never rewritten. Prepare new exclusive outputs after source or Git
state changes.

DRAFT -> STATIC_VERIFIED -> AWAITING_APPROVAL is the entire implemented transition
set. AWAITING_APPROVAL is not approval. Calibration, execution, promotion and future
eligibility remain false and signatures empty. The returned structural validation
status explicitly states external verification. Point-in-time storage observations
reserve no space. Synthetic events remain ineligible as measurements.

Resolved SESSION_END order is design metadata. No native code, graph or profiler
is loaded or dispatched by validation, planning or simulation. Formal independent
scientific approval and all diagnostic/host/calibration/execution gates remain
pending. The old schema-v1 document and ordering proposal are historical context.
