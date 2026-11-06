# Task 15 — Diagnostic Ordering Amendment v1.2.0

## Status and authority

**FROZEN PRE-DATA DESIGN; NOT INDEPENDENTLY APPROVED.** Execution and promotion
remain false. This amendment authorizes no harness adaptation, diagnostic build,
calibration, collection or dispatcher. The current 0.1.1 harness remains pinned
to v1.1.0. The old proposed clarification remains a historical proposal; this new
version explicitly chooses the scheduling rule without editing that proposal.

Parent commit: `367bbdefd279c8dc6673ed03e5bdc9f57031a08f`. Parent canonical SHA-256: `6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f`.
New canonical SHA-256: `c41e45bccb68abdf03bab40ea793837a7f508fde17634c1aa8b358a3d82fceb0`.
Resolved cross-lane SHA-256: `3e22c8ebfbdb23af04059bece54734844ee58664a3c43abd9170625922cf20ba`.

The complete [v1.2.0 JSON](task15_tail_attribution_protocol_v1.2.0.json) inherits
v1.1.0 verbatim except the precise paths in the [ledger](task15_tail_attribution_amendment_v1.2.0.json).
The retained `amendment` object documents the historical v1.1.0 amendment;
`ordering_amendment` identifies this v1.2.0 change. No historical file is superseded
in place. The versioned document is frozen for review, not execution approval.

## Scientific decision and alternatives

This comparison is a pre-data design inference from the frozen process lifecycle,
non-overlap rules, source lists and supplementary role of stacks. No new latency,
CPU, allocator or profiling observations were inspected to choose placement.
No quantitative performance or bias reduction is claimed.

| Alternative | Temporal confounding and comparability | Cache/memory and profiler interference | Fresh-worker isolation, frozen constraints and complexity |
| --- | --- | --- | --- |
| A: session-end (chosen) | Makes stacks systematically late; not contemporaneous with count/timed blocks. Suitable for supplementary stack context, not causal timing comparison. | Stack profiler activity is placed after that session's main work, avoiding its placement before later main blocks in the same session. Existing main diagnostics and host drift can still affect late stacks; effects can persist across sessions. | Retains all main order/condition constraints, assigned sessions and original companion order; existing fresh pairs remain required. Simplest deterministic merge. |
| B: adjacent to related allocator-count entry | Reduces temporal distance to a related entry, but does not establish a matched contemporaneous contrast; does not justify pooling. | Inserts stack-profiler work between existing main blocks and may perturb subsequent main work. | Still needs fresh pairs. Requires an additional choice of anchor mode and position relative to both frozen conditions; higher complexity without evidence of superior stack interpretation. |
| C: isolated within-session blocks | Fixed internal blocks make position explicit, but block placement remains confounded with time. Isolation is not proven by naming a block. | Internal blocks may perturb later main work; fresh workers do not reset host state. A real cooldown/washout would add an uncalibrated condition. | Requires more placement decisions; no existing evidence justifies changing conditions or adding a washout. An isolated final block reduces to A. |

Choose **SESSION_END**. For diagnostic sessions 0, 1, 2, 3 in order: filter the
original main source list by assigned session, retain its stored relative order,
expand each entry's frozen conditions contiguously, then complete that session's
assigned companions in their original source-list order before the next session.
All operations/regions/variants within a condition retain the frozen P2 mapping.
No random draws, runtime options or observation-dependent selection enter this rule.

Late-session placement could materially affect stack frequencies or which paths
are observed. Fresh process pairs limit reuse of worker-local state; they do not
reset thermal, OS cache, memory pressure, background work or profiler state.
Session-end placement is defensible specifically because stack evidence is
supplementary, not a confirmatory or timed allocator contrast. A stack supports
location/context for observed allocator activity; it cannot establish temporal
causation, quantify ordinary A/B latency, or be pooled with C timed requests.
Retain existing host/profiler records, attribution uncertainty, stop/failure and
no-retry rules. Do not delete inconvenient late stacks, move them earlier after
observations, or add a cooldown. Any later placement/condition change requires
another versioned, pre-data amendment and review.

No data are collected by this task. No new Task 15 observations inform the design.
The supplied task declares pre-data intent; repository metadata cannot prove no
Task 15 collection occurred anywhere. That global absence remains UNVERIFIED.
No independent approval signature is supplied or manufactured.

## Complete diagnostic entry order

Indices below are zero-based within each diagnostic session. Main condition order
is contiguous within each entry. `source_lane_index` in JSON preserves the original
global source-array index; `source_lane_session_index` preserves its filtered lane
index. Across sessions the inherited main rule is session filtering, so global
source-array order is not itself a chronological constraint.

| Session | Entry index | Lane | Original entry | Cohort / mode | Frozen P2 reference | Ordered conditions |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | MAIN | D-cpu_counters_cache-00 | D / cpu_counters_cache | S00-P2-T00 | control, treatment |
| 0 | 1 | MAIN | D-processor_trace-00 | D / processor_trace | S00-P2-T00 | control, treatment |
| 0 | 2 | MAIN | C-timed_requests-00 | C / timed_requests | S00-P2-T00 | control, treatment |
| 0 | 3 | MAIN | D-powermetrics-01 | D / powermetrics | S00-P2-T01 | treatment, control |
| 0 | 4 | MAIN | C-timed_requests-01 | C / timed_requests | S00-P2-T01 | treatment, control |
| 0 | 5 | MAIN | D-system_trace_background-01 | D / system_trace_background | S00-P2-T01 | treatment, control |
| 0 | 6 | MAIN | D-system_trace_background-00 | D / system_trace_background | S00-P2-T00 | control, treatment |
| 0 | 7 | MAIN | D-powermetrics-00 | D / powermetrics | S00-P2-T00 | control, treatment |
| 0 | 8 | MAIN | D-processor_trace-01 | D / processor_trace | S00-P2-T01 | treatment, control |
| 0 | 9 | MAIN | D-cpu_counters_cache-01 | D / cpu_counters_cache | S00-P2-T01 | treatment, control |
| 0 | 10 | MAIN | C-request_counts-01 | C / request_counts | S00-P2-T01 | treatment, control |
| 0 | 11 | MAIN | C-request_counts-00 | C / request_counts | S00-P2-T00 | control, treatment |
| 0 | 12 | COMPANION | C-stack-0 | C / allocation_stacks | S00-P2-T00 | trace_on_count_only |
| 0 | 13 | COMPANION | C-stack-1 | C / allocation_stacks | S00-P2-T01 | trace_on_count_only |
| 1 | 0 | MAIN | C-request_counts-02 | C / request_counts | S00-P2-T02 | control, treatment |
| 1 | 1 | MAIN | D-system_trace_background-03 | D / system_trace_background | S00-P2-T03 | treatment, control |
| 1 | 2 | MAIN | D-cpu_counters_cache-02 | D / cpu_counters_cache | S00-P2-T02 | control, treatment |
| 1 | 3 | MAIN | C-timed_requests-03 | C / timed_requests | S00-P2-T03 | treatment, control |
| 1 | 4 | MAIN | C-request_counts-03 | C / request_counts | S00-P2-T03 | treatment, control |
| 1 | 5 | MAIN | D-processor_trace-02 | D / processor_trace | S00-P2-T02 | control, treatment |
| 1 | 6 | MAIN | D-processor_trace-03 | D / processor_trace | S00-P2-T03 | treatment, control |
| 1 | 7 | MAIN | D-system_trace_background-02 | D / system_trace_background | S00-P2-T02 | control, treatment |
| 1 | 8 | MAIN | D-cpu_counters_cache-03 | D / cpu_counters_cache | S00-P2-T03 | treatment, control |
| 1 | 9 | MAIN | D-powermetrics-02 | D / powermetrics | S00-P2-T02 | control, treatment |
| 1 | 10 | MAIN | C-timed_requests-02 | C / timed_requests | S00-P2-T02 | control, treatment |
| 1 | 11 | MAIN | D-powermetrics-03 | D / powermetrics | S00-P2-T03 | treatment, control |
| 2 | 0 | MAIN | D-powermetrics-04 | D / powermetrics | S01-P2-T04 | control, treatment |
| 2 | 1 | MAIN | D-powermetrics-05 | D / powermetrics | S01-P2-T05 | treatment, control |
| 2 | 2 | MAIN | D-processor_trace-04 | D / processor_trace | S01-P2-T04 | control, treatment |
| 2 | 3 | MAIN | C-request_counts-04 | C / request_counts | S01-P2-T04 | control, treatment |
| 2 | 4 | MAIN | D-processor_trace-05 | D / processor_trace | S01-P2-T05 | treatment, control |
| 2 | 5 | MAIN | C-timed_requests-04 | C / timed_requests | S01-P2-T04 | control, treatment |
| 2 | 6 | MAIN | C-timed_requests-05 | C / timed_requests | S01-P2-T05 | treatment, control |
| 2 | 7 | MAIN | C-request_counts-05 | C / request_counts | S01-P2-T05 | treatment, control |
| 2 | 8 | MAIN | D-system_trace_background-04 | D / system_trace_background | S01-P2-T04 | control, treatment |
| 2 | 9 | MAIN | D-system_trace_background-05 | D / system_trace_background | S01-P2-T05 | treatment, control |
| 2 | 10 | MAIN | D-cpu_counters_cache-04 | D / cpu_counters_cache | S01-P2-T04 | control, treatment |
| 2 | 11 | MAIN | D-cpu_counters_cache-05 | D / cpu_counters_cache | S01-P2-T05 | treatment, control |
| 2 | 12 | COMPANION | C-stack-4 | C / allocation_stacks | S01-P2-T04 | trace_on_count_only |
| 2 | 13 | COMPANION | C-stack-5 | C / allocation_stacks | S01-P2-T05 | trace_on_count_only |
| 3 | 0 | MAIN | D-cpu_counters_cache-07 | D / cpu_counters_cache | S01-P2-T07 | treatment, control |
| 3 | 1 | MAIN | C-request_counts-06 | C / request_counts | S01-P2-T06 | control, treatment |
| 3 | 2 | MAIN | C-request_counts-07 | C / request_counts | S01-P2-T07 | treatment, control |
| 3 | 3 | MAIN | D-processor_trace-07 | D / processor_trace | S01-P2-T07 | treatment, control |
| 3 | 4 | MAIN | D-processor_trace-06 | D / processor_trace | S01-P2-T06 | control, treatment |
| 3 | 5 | MAIN | D-cpu_counters_cache-06 | D / cpu_counters_cache | S01-P2-T06 | control, treatment |
| 3 | 6 | MAIN | D-system_trace_background-07 | D / system_trace_background | S01-P2-T07 | treatment, control |
| 3 | 7 | MAIN | D-system_trace_background-06 | D / system_trace_background | S01-P2-T06 | control, treatment |
| 3 | 8 | MAIN | D-powermetrics-07 | D / powermetrics | S01-P2-T07 | treatment, control |
| 3 | 9 | MAIN | C-timed_requests-07 | C / timed_requests | S01-P2-T07 | treatment, control |
| 3 | 10 | MAIN | C-timed_requests-06 | C / timed_requests | S01-P2-T06 | control, treatment |
| 3 | 11 | MAIN | D-powermetrics-06 | D / powermetrics | S01-P2-T06 | control, treatment |

## Counts, provenance and stable identities

| Diagnostic session | Main entries | Main condition blocks | Companions | Total blocks |
| --- | --- | --- | --- | --- |
| 0 | 12 | 24 | C-stack-0, C-stack-1 | 26 |
| 1 | 12 | 24 | none | 24 |
| 2 | 12 | 24 | C-stack-4, C-stack-5 | 26 |
| 3 | 12 | 24 | none | 24 |
| Total | 48 | 96 | 4 | 100 |

The two original arrays remain byte-identical as canonical values and retain their
original digests. They remain authoritative provenance for entry contents.
`design.resolved_diagnostic_order.entries` contains 52 distinct entries;
`condition_blocks` contains the complete 100-unit order. The separate resolved-order
hash covers all ordering metadata, including both arrays, rule and identity policy.
No latency, timing sample or other scientific measurement is stored in this object.
128 primary A/B units are unchanged; total remains 228 units and 138,696 structural
records, including all warmups and untimed hot preparation records. All 64 base
rows, eight primary sessions, four diagnostic sessions, P1/P2 assignments,
permutations, original position/source/occurrence identities and variant orders
remain unchanged. C retains 41 selected positions. P2 remains 50/50 per trial,
16/16 per original position, 2/2 per original position/session, in each region.
Clock/CPU boundaries, H1, bootstrap, multiplicity, strict p99, G1-G10, binary/graph
identities, no adaptive retry/exclusion, and stop rules remain verbatim.

The new protocol hash changes provenance, not the logical workload/query IDs.
For continuity, structural query IDs retain the exact 0.1.1 derivation with the
v1.1.0 canonical hash as their **identity namespace**, along with namespaced session,
unit ID, phase, region, execution index, original position and variant. Record the
active v1.2.0 protocol hash separately. This explicit namespace is not permission
to validate v1.2.0 with a v1.1.0 manifest. Future adaptation must verify the unchanged
ID set and each unit's internal query order while adopting the new cross-unit order.

## Hash and validation contract

Canonical protocol hash: remove only `identity.sha256`; sorted-key compact
ASCII-escaped UTF-8 JSON; SHA-256. Resolved-order hash: same canonical serialization
of `design.resolved_diagnostic_order`. The JSON file-byte hash includes its pretty
printing/trailing LF and is distinct. The ledger has its own canonical
`identity_sha256`, computed after removing only that field; its final file-byte
hash is recorded by external evidence, avoiding circular self-hashes.

The separate static generator and validator share no imports or order constructor.
The validator independently checks source membership, within-session lane order,
conditions, sessions, references, contiguous indices, exact metadata, parent-only
projection, counts, source occurrences, P2 balances, workload/query identities,
all parent file hashes and protected Git objects. Negative fixtures test missing,
duplicate and moved companions; reordered main entries; reversed conditions;
wrong reference; altered P2 mapping; stale order and canonical hashes. Invalid
fixtures have classified reasons even when their outer digests are repaired.
All mutable test logs/results and generation comparisons are outside Git.

## Required future harness adaptation — separately authorized

Do not change the existing package in this task. Future work must:

1. Update `protocol.py` PROTOCOL_HASH, PARENT_HASH, LEDGER_HASH, AMENDMENT_MD_HASH,
   explicit accepted version/file paths, parent-chain validation and the closed
   protocol schema. Retain the entire v1.0 -> v1.1 -> v1.2 historical chain.
2. Retain original two-lane entry structures for provenance; introduce a separate
   resolved condition-block sequence. Do not append all companions after all four
   sessions. Resolve by session-local sequence index exactly as frozen here.
3. Preserve primary unit IDs and all per-unit jobs; preserve query IDs with the
   declared stable namespace while recording active v1.2.0 provenance separately.
   Recompute plan identity and version/source locks; do not reuse a v1.1 plan hash.
4. Adapt tests for pinned hashes/version/schema, resolved ordering and deliberately
   unchanged query IDs/occurrences/counts, while preserving all F-01 through F-11
   controls, partial-lane provenance tests and no-execution restrictions.
5. Create new exclusive manifests locking v1.2 canonical and file-byte hashes,
   new ledger/Markdown/order hashes and future adapted harness source/version,
   plan, dependency, runtime and artifact identities. Old v1.1 manifests remain
   historical and cannot authorize v1.2 execution. They remain valid only under
   their unchanged v1.1 harness/repository observation constraints.

A future dispatcher must consume the reviewed 100-block sequence exactly after
all primary A/B work, with inherited lifecycle/failure gates. This amendment
implements no dispatcher. Loader adaptation itself grants no calibration or
collection authorization. G8, diagnostic builds, host capabilities, sufficient
storage, capacity/clock/instrument calibration and separate signed authorization
remain pending. Independent review status remains NOT_INDEPENDENTLY_APPROVED.
