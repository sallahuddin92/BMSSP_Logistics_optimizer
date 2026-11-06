# Task 15 — Protocol v1.1.0 Amendment Report

## 1. Verdict

**READY FOR INDEPENDENT RE-REVIEW.** This is a pre-data design amendment, not independent approval, harness preparation or execution authorization. The original two v1.0.0 documents remain byte-for-byte unchanged. v1.0.0 was **not approved** and must not be used for preparation. v1.1.0 keeps execution and promotion authorization false.

The active complete machine-readable specification is [protocol v1.1.0](task15_tail_attribution_protocol_v1.1.0.json). Its inherited provisions remain binding unless an explicit changed JSON path in the [amendment ledger](task15_tail_attribution_amendment_v1.1.0.json) changes them. The original Markdown/JSON are historical records, not active guarantees. No engine, comparator, API, native Dijkstra or benchmark runner is changed or implemented. Only static calculations, schema checks and synthetic arithmetic/RNG fixtures were executed.

## 2. Repository Baseline

Repository `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer`, branch `codex/genuine-bmssp-engine`, origin unchanged at `https://github.com/sallahuddin92/BMSSP_Logistics_optimizer.git`. Parent documentation commit `afc1867f57f663ac56104521474c582e72461882`; Task 14 runtime `cb5e1b6dd1c7ac52755a29d6b7f411f9b68ee80e`; Task 13 reference `cafea0f36091396dff6ebd5efd88d59cd1e97f77`. Startup tree was clean. Preservation began `2026-11-06T05:59:15.322425+00:00`; external preservation manifest: `/Users/sallahuddin/Projects/BMSSP-task15-amendment-v1.1.0-d0k_r0o3/preservation_manifest.json`.

Parent canonical SHA-256: `590838e4fdde2dcd86228fe0c521845e479fcc6372fa39d3745cb21270ce8247`.
Parent JSON file bytes: `081b6f2cb06e59c9a0578b78f9a007be505fef11f2302ae834d4c62dd209ed17`.
Parent Markdown file bytes: `c9ae85657fd94c1d51485f06a2ea6e022d848473e79969354a36ae13cc5330c5`.

The supplied review, results and validator were located in `/Users/sallahuddin/Downloads/files/`, read in full and hashed in the protocol/ledger. The actual stored parent schedule reproduces the review's original-position AB ranges 7–22, 8–24 and 10–21. No new Task 15 observations were used. A global claim that nobody has collected any Task 15 data is **UNVERIFIED**: available local v1.0 delivery/review records report no collection, but repository metadata cannot prove absence everywhere. This amendment itself generates no performance data.

## 3. Amendment Rationale

| Finding | Disposition | Evidence/correction |
| --- | --- | --- |
| F1 | CORRECTED_STATICALLY_VERIFIED | 50/50 each trial,16/16 each original position,2/2 each original position/session, execution arrays mapped through unchanged permutations |
| F2 | CORRECTED_STATICALLY_VERIFIED | 8/8/8/8 overall,one each/session; four minimal P1 variant-order flips, startup unchanged |
| F3 | RETAINED_LIMITATION_CLARIFIED | same counts/estimator plus explicit finite-sample undercoverage warning and n8 descriptive session table |
| F4 | RETAINED_LIMITATION_CLARIFIED | unchanged; frequent INCONCLUSIVE is an expected possible outcome,~9%illustrative width not power |
| F5 | CORRECTED_FROM_HISTORICAL_RAW | medium 0..9 union both variants historical NRp99-inclusive positions,23 medium / 41 total C positions |
| F6 | DESIGN_CORRECTED_FUTURE_CALIBRATION_PENDING | ten-query scope verified,max 1,886,462 operations/query in measured cohort; bounded 4M operation-events/query at 128 bytes max,512 GiB storage preflight |
| F7 | DESIGN_CORRECTED_CAUSATION_UNRESOLVED | separate moderate/severe current matched deltas with frozen-position reference and precision floor; all distribution shifts continuous |
| F8 | GATES_DEFINED_NOT_EXECUTED | G1..G10 semantic/ABI/flag/input/codegen/overhead/identity gates; Class M blocks, Class L explicit prereview |
| F9 | SPECIFIED_SYNTHETIC_STATIC_VERIFIED | exact RNG call order/fresh repeated-session draws/version/NRendpoints/faileddata/serialization, four draw and12ratio synthetic vectors |
| F10 | CORRECTED_SCHEMA_VERIFIED | P1-only batch-order and P2-only execution-order fields; unknown/cross fields rejected; diagnostic startup separate |
| F11 | HOST_STATIC_HASHES_VERIFIED_RUNTIME_PENDING | local original inputs/reviews rehashed; API/template audit remains documentary; runtime clock/permission/overhead/storage gates pending |

F1's root cause was an indexing error in construction and validation: an order array was checked directly by array index, without applying each trial's source permutation. Exact iteration-index balance was incorrectly reported as original-position balance. The new validator independently walks execution index → original position → original source ID before accumulating either balance, and reconstructs the expected seeded assignment without importing the generator. Explanatory text alone does not close a mathematical finding.

## 4. Corrected P2 Schedule

Amendment seed: `BMSSP-T15-AMENDMENT-v1.1.0-20261106-P2`. The source permutations, row order, region order, startup order, source IDs, repeated positions, trial IDs and session structure are preserved. In each region, hash-sort the original positions with SHA-256 over canonical `[seed,"position_pairs",region,position]`, ties by numeric position; pair adjacent positions. For each pair/session, hash-sort slots 0–3 under domain `AB_slots,region,session,pair_index,slot`, ties numeric slot, and select the first two. The first position gets AB in those slots; its partner gets the complement. Store each trial's labels by evaluating these original-position assignments at its unchanged execution permutation.

Proof: each of 50 pairs supplies one AB in each trial, hence exactly 50 AB/50 BA. Each original position receives two AB/two BA per four-trial session; eight sessions give 16/16. This construction uses only declared positions and seed, never source latency. The JSON includes the pair/slot witness; the validator recomputes it independently.

| Region | P2 trials | Positions/trial | AB/BA per trial | AB/BA per original position | AB/BA per position/session |
| --- | --- | --- | --- | --- | --- |
| seremban-small | 32 | 100 | 50/50 | 16/16 | 2/2 |
| seremban-medium | 32 | 100 | 50/50 | 16/16 | 2/2 |
| seremban-port-dickson | 32 | 100 | 50/50 | 16/16 | 2/2 |

Small retains 100 positions/96 distinct sources, including every occurrence of 4881016931, 4882418061 and 4884533214 in its original position. Source occurrence identity is never replaced by source ID alone. Both variants consume the same permutation.

Exact global iteration-index 16/16 balance is **not claimed**. Observed iteration-index AB ranges are 9–22, 11–26 and 9–25. Bounded static joint-constraint searches did not establish a solution preserving that optional property; they do not prove mathematical infeasibility. The adopted recommended construction guarantees the mandatory original-position and stronger within-session invariants. Neither guarantee is inferred from metadata.

P1 rows now contain only `P1_variant_order`; P2 rows contain only `P2_pair_orders_by_region`. Both require ID, zero-based session/trial, startup, region order and position permutation. Unknown or cross-protocol fields are rejected. P2 order at execution index e means the label for original position `positions_by_region[g][e]`, not position e. Diagnostic references consume the P2 mapping; their `variant_order` specifies worker startup only, while `condition_order` specifies diagnostic condition blocks.

## 5. P1 Orthogonality

| Startup / variant order | v1.0.0 | v1.1.0 |
| --- | --- | --- |
| AB / AB | 10 | 8 |
| AB / BA | 6 | 8 |
| BA / AB | 6 | 8 |
| BA / BA | 10 | 8 |

Each of the four combinations occurs once per session. Startup orders stay unchanged. Only four P1 variant-order entries change, the minimum: in each nonorthogonal session (0/1), flip one entry in each startup subgroup, chosen by domain-separated hash order. Already orthogonal sessions stay unchanged. No source or region permutation changes.

## 6. Statistical Corrections

Keep eight primary sessions, four paired trials per protocol/session, 32 trials/protocol, all 100 positions, all three regions, nearest-rank quantiles and the hierarchical session/process percentile bootstrap. Counts, the ten-cell Bonferroni family, the separate six-cell CPU family, strict zero-regression target, no adaptive stopping and no favorable replacement are unchanged. Existing 100,000 repetitions, PCG64/seeds and 99.5% sensitivity bounds were already present in v1.0; the amendment makes their execution exact rather than falsely calling them absent.

For each cohort initialize `Generator(PCG64(15062026))` once. Each replicate draws eight sessions with one `integers(0,8,size=8,dtype=int64,endpoint=False)` call. In sampled occurrence order, draw four local slots for P1, then four for P2, each in a distinct call. Sort actual trial membership by `trial_within_protocol`; a repeated sampled session gets fresh process draws each occurrence. Reuse these exact draws across all three regions, both variants, all positions and metrics. Do not make any other RNG calls or resample rows/sources. Sensitivity uses a new generator/seed 15062027, fixed sessions 0–7 and the same P1-then-P2 local calls, with no session RNG call. Diagnostic descriptive resampling uses seed 15062028, four diagnostic sessions/two local clusters, separately by mode, both conditions paired.

NumPy 1.24.4 and the existing CPython 3.11.15 JSON environment are locked; no package upgrade is authorized. Exact NR index is `ceil(n*p)-1`; interval indices use rational integer arithmetic. At 100,000 replicates, ordinary 95% endpoints are indices 2499/97499, primary 99.5% indices 249/99749, and secondary CPU indices 416/99583. Candidate quantile is numerator, baseline denominator; binary64 division, original near-zero denominator rule, no average-of-trial-quantiles substitution. Missing required A clusters block confirmatory inference; undefined bootstrap ratios make the entire cell interval undefined/INCONCLUSIVE rather than silently discarding replicates. Sorted-key compact ASCII-escaped UTF-8 JSON, finite Python scalars and trailing LF give deterministic serialization; no decision rounding.

Add an explicitly **descriptive n=8 session** table: each session's pooled 400-position p50/p95/p99 per variant, ratios/differences, eight-session range/NR median/direction counts and leave-one-session-out. It cannot replace the confirmatory estimator. Four synthetic draw fixtures (two primary/two stratified), 12 dimensionless quantile-ratio fixtures and six endpoint-index fixtures test the implementation contract; they are not performance observations.

An observed ratio is a sample description. Its approximate interval is conditional on the fixed sources/session model. Eight sessions cannot give a highly reliable 99.5% coverage guarantee, and Bonferroni does not repair bootstrap undercoverage. Neither an interval nor an observed tail increase establishes a robust production-wide claim or causal software regression. The historical approximately ±9% simultaneous-width illustration is not a power calculation or acceptance tolerance. INCONCLUSIVE remains possible, even after successful full collection and even if there is no true regression. No threshold is relaxed.

## 7. H1 Attribution Criteria

Let H(g,p) be the frozen historical Task 14 baseline NR median for the **same original position**, in seconds. Let signed current paired delta be candidate wall minus baseline wall at that position within the same trial/protocol/condition. Retain both signs. Define a future precision floor epsilon as the maximum of ten wall-clock quanta, ten thread-CPU quanta, twice the sum of apertures over the four variant endpoints, and twice calibrated endpoint-group p99. These are formulae, not invented measured resolutions.

| Phenomenon | Frozen rule | Interpretation |
| --- | --- | --- |
| Moderate paired event | abs(deltaW) ≥ max(0.000250 s, 0.01×H, epsilon), below severe threshold | Investigates smaller matched shifts; sign identifies slower variant |
| Severe paired event | abs(deltaW) ≥ max(0.010 s, 0.25×H, epsilon) | Large matched excess, threshold-inclusive |
| Historical extreme flag | Wvariant > max(1.5×H, H+0.010 s) | Parent flag kept separately; not an H1 entry requirement |
| Distribution shift | All signed differences and full p50/p95/p99, without event filtering | Continuous aggregate shifts need not cross either threshold |

Orient CPU/gap differences slow minus fast using the sign of wall difference. Keep negative components and fractions exceeding 100%; they can reflect CPU savings offset by elapsed delay. Require positive excess above epsilon and conservative endpoint-error accounting. Runnable off-CPU intervals linked to the exact PID/TID/query are still necessary for descheduling attribution. Blocked waits remain separate; memory stalls and frequency changes can increase on-CPU duration. Wall-minus-thread-CPU alone is never called a measured context switch or descheduling duration.

The 80% accounting and 50% controlled-response thresholds are **engineering heuristics** meaning dominant explained excess and a large reversible intervention response, not confidence guarantees. At least three events over two sessions, direct time-aligned scheduler evidence, uncertainty-valid accounting and alternatives addressed remain required. One-session spikes can remain UNRESOLVED. Changing thresholds does not resolve Task 14 F2.

## 8. Allocator Diagnostic Coverage

Original medium positions were 0–9. The new rule retains them and adds the union of positions at or above the combined 800-observation nearest-rank p99 boundary **separately for baseline and candidate**. Thus it includes both ninth-largest boundary observations and every more extreme value. Selection uses only preserved Task 14 raw data and deduplicates original positions, not identities. A/B/D workloads are unchanged; small/corridor C positions stay unchanged.

New medium positions: `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 39, 55, 56, 57, 58, 60, 63, 66, 71, 78, 89, 90]`. Added positions: `[12, 39, 55, 56, 57, 58, 60, 63, 66, 71, 78, 89, 90]`. C expands from 28 to **41 positions** (10 small,23 medium,8 corridor). The JSON lists every selected source ID and precise raw filename/zero-based sample index; no source is invented.

| Variant | Position | Source ID | Wall ms | Batch / local trial |
| --- | --- | --- | --- | --- |
| baseline | 63 | 5748423175 | 57.111416 | final-ab / 1 |
| baseline | 89 | 4882559635 | 49.259916 | final-ab / 1 |
| baseline | 90 | 5750471304 | 56.487417 | final-ab / 1 |
| baseline | 55 | 5742772329 | 50.136000 | final-ab / 2 |
| baseline | 58 | 2670639484 | 49.720708 | final-ab / 2 |
| baseline | 60 | 4876353886 | 50.465833 | final-ab / 2 |
| baseline | 71 | 4197197858 | 52.334250 | final-ab / 2 |
| baseline | 56 | 2864454014 | 79.831750 | final-ab / 3 |
| baseline | 9 | 5748272917 | 55.029958 | replication-ab / 0 |
| candidate | 57 | 4354704920 | 55.059500 | final-ab / 0 |
| candidate | 39 | 7603734379 | 56.190209 | final-ab / 1 |
| candidate | 78 | 4957287996 | 63.714209 | final-ab / 1 |
| candidate | 3 | 3250604903 | 54.952958 | final-ab / 2 |
| candidate | 5 | 7483121715 | 80.709292 | final-ab / 2 |
| candidate | 6 | 7415805249 | 81.124958 | final-ab / 2 |
| candidate | 7 | 7525749618 | 67.787541 | final-ab / 2 |
| candidate | 12 | 3782899156 | 54.550750 | final-ab / 2 |
| candidate | 66 | 9252053156 | 56.546500 | final-ab / 2 |

Each historical allocation file has ten **per-query** records. New-call totals 150,561 /5,481,670 /9,292,376 are ten-query sums for one graph/variant, not single-query counts. Maximum single-query new-plus-delete counts are 53,068 small,1,107,092 medium,1,886,462 corridor. Records include successful C++ requests plus result destruction, excluding arbitrary C malloc/metadata/OS allocation; most targeted tail sources were not measured by that probe.

The old 2M cap has only approximately 6.02% headroom over the observed largest operation count. A bounded **4,000,000 outermost operation-events per query** provides approximately 2.12× that observed maximum, not a guarantee for unmeasured sources. One event stores both endpoints of one request/free/failure operation, at most 128 bytes. It is not one event per nanosecond or a ten-query buffer. Two preallocated/prefaulted worker buffers use 1,024,000,000 bytes; controls reserve the same memory. Preflight must verify available buffers plus actual prepared worker/graph footprint plus 1 GiB safety.

Worst uncompressed timed C events: 8 clusters ×2variants ×41positions ×4M ×128bytes =335,872,000,000 bytes (312.805 GiB), plus reserved profiler/metadata space. Require 512 GiB free before C/D; stop before the next whole block below 16 GiB. No compression benefit is assumed. Future fixed count-only preflight must cover all 41 positions/both variants/conditions with the exact intended operation scope and verify cap/record size/coverage. Any cap overflow, dropped event, failed allocation/calibration or storage gate blocks affected C attribution; preserve raw attempts, mark complete paired diagnostic block INCOMPLETE, never grow the buffer, omit sources, retry favorably or infer per-query stalls from aggregate counts. Capacity calibration was not executed.

## 9. Diagnostic Build Equivalence

All ten future gates are mandatory, and none was run here:

| Gate | Objective acceptance |
| --- | --- |
| G1_source | audited diff permits only documented T0..T6 measurement/support in external copies, C operators in diagnostic executable, preallocated recording/signposts. No edits to comparator, graph/degree, recursion, BaseCase, FindPivots, frontier, k/t, reference Dijkstra, numeric checks or ownership. Exact whitelist line/symbol manifest locked before measurement. |
| G2_semantics | all existing applicable correctness/frozen-trace gates pass unchanged; for EVERY 100 original position / 3 graphs each diagnostic binary vs its own frozen production variant: exactly equal required full distance-vector bits, four original directed-path fingerprints/edge validation, all deterministic counters/materializations/status. Nonzero mismatches=FAIL. C subset is NOT enough for this equivalence gate. |
| G3_ABI | same exported public API signatures and symbol types, graph/label/edge/result relevant sizeof/alignof and permitted offsetof for standard-layout fields, same headers/definitions and Python contracts; diagnostic-only symbols isolated. Any relevant mismatch=FAIL. |
| G4_flags | same pinned compiler/SDK/dependency identities and -std=c++20 -O3 -DNDEBUG -arch arm64 -fPIC, same numeric/exception/RTTI/LTO/target flags as corresponding production. Only approved diagnostic support/link flags explicitly recorded, no unreviewed optimization/fast-math changes. |
| G5_inputs | exact graph/source/snapshot/input positions and occurrence identities as protocol, exact production SHA; any mismatch=FAIL. |
| G6_A_isolation | Cohort A loaded binary SHA equals frozen archived file, no preloads/interception/MallocStackLogging/profiler/signpost hooks/diagnostic library; zero query ProfileScope calls. Any violation invalidates whole paired A cluster. |
| G7_identity_lock | production and diagnostic SHA/source diffs/build commands/symbol+layout manifests immutable and approved before ANY calibration, all loads recheck hashes; stale/missing identity=FAIL. |
| G8_codegen | compare production vs diagnostic per variant; normalize only addresses/relocation targets and debug metadata, preserving opcode/register/control-flow/frame/spill differences. Enumerate comparator, recursion/BaseCase/FindPivots/frontier/graph/degree hot functions and top-level solve compute regions outside approved insertion windows. Class I: unchanged normalized compute instructions,CFG,frame,spills and hot entry alignment modulo64; approved marker-only deltas localized outside compute. Class L: address/alignment/page placement only, normalized code unchanged; record all symbol/loop offsets, lengths, alignment mod64/page crossing changes and require explicit independent layout-risk approval BEFORE measurement; no assumption that L is performance-equivalent. Class M: changed non-whitelisted compute instructions/CFG/frames/spills or unknown attribution =>FAIL/block affected cohort until new reviewed amendment. Whole-binary byte identity is NOT required. Missing disassembly/symbol coverage =>FAIL. |
| G9_overhead | original numerical B clock/aperture/endpoint and differential-overhead gates pass; C count coverage/capacity and D instrument loss/synchronization gates pass for used metric. Calibration values unavailable now, gate PENDING. |
| G10_approval | all G1..G9 outcomes and any Class L approval signed/hashed in future manifest before collection. No independent approval currently claimed; semantically equal diagnostics never replace A. |

Whole-binary byte identity is not required because instrumentation changes code. Exact algorithm semantics, ABI/layout contracts, frozen input/output/work identities and pinned production flags are required. Codegen Class I has unchanged normalized uninstrumented compute code/CFG/frame/spills/alignment; Class L is layout/address-only and requires quantified offsets/alignment/page changes plus explicit independent risk approval before measurement; Class M is material or unexplained non-whitelisted compute change and blocks the affected cohort pending a new reviewed amendment. No diagnostic binary can replace ordinary A or establish A latency by substitution. Future calibration/approval outcomes remain PENDING.

## 10. Reproducibility

| Identity | SHA-256 |
| --- | --- |
| Parent canonical | 590838e4fdde2dcd86228fe0c521845e479fcc6372fa39d3745cb21270ce8247 |
| New canonical | 6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f |
| New JSON file bytes | c4debb684c6bf534f9942c3776d994938577270d5c2d9cbee3224cf8be242dfe |
| Primary schedule | 46559c673c7427dd3ab70138efd2299a0db354bc0d9e0a3f35ccd2fda4ac4996 |
| Diagnostic schedule | 41cabb4e16f5ad0fb99c2a9f352833ff1c5daa2be1915e57283399271dad32be |
| Stack companions | 906dbe7951eee1a9257d98e9fb854b5e26ad2bb1eb22634a84dfeb5ccc60839e |
| Amendment ledger file bytes | 8dde76dcb9669148ae47e8b9192c986d5a06821b2fdc5f2bb54914489613910f |
| Independent static validator | 4228ac56b3ea6d6d0f6b4aa0b2acb252f232c96ee63f3a8ff406dd77ffe65580 |

Canonicalization is unchanged: remove only `identity.sha256`, sort object keys, compact separators, ASCII escape, UTF-8 and SHA-256. The ledger enumerates exact changed JSON pointers, before/after behavior/value identities, finding IDs, justification and comparability. Index-change groups explicitly expand to each exact pointer/index. Diagnostic IDs and references are unchanged, but their resolved order/subset identities change; new `resolved_workload_sha256` fields therefore change the diagnostic and stack-companion digests. Old hashes are historical parent references only.

Generator and validator are separate implementations with no shared imports or balance helper. Generation uses only standard-library hashing and preserved historical inputs; the validator checks stored schedules by mapped original position and independently recomputes seed assignments. Regeneration into a fresh external directory was byte-identical. The bounded optional joint-balance solver investigations are not part of the adopted deterministic generator and do not select favorable performance data.

## 11. Static Validation Results

Strict Mac-local validation: **PASS_STATIC_HOST**, **15,461 checks, 0 failures**, no unverified external hash checks in that run. All required A–U invariant groups pass, including original bytes/runtime trees, counts, IDs, permutations, source occurrences, P1 combinations, mapped P2 balances, derived diagnostic references, raw medium-tail cohort, capacities, retained statistical thresholds and false execution/promotion authorization. This is not a pass of future diagnostic equivalence or measurement gates.

| Synthetic negative control | Required failure | Result |
| --- | --- | --- |
| flip_one_P2_order | P2_TRIAL_BALANCE | REJECTED |
| wrong_execution_to_original_mapping | P2_MAPPING | REJECTED |
| duplicate_position | PERMUTATION | REJECTED |
| remove_trial | TRIAL_COUNT | REJECTED |
| corrupt_diagnostic_reference | DIAG_REFERENCE | REJECTED |
| corrupt_canonical_hash | CANONICAL_HASH | REJECTED |
| break_repeated_source_position | INPUT_IDS | REJECTED |
| add_cross_protocol_field | ROW_SCHEMA | REJECTED |
| relax_tail_gate | ACCEPTANCE_UNCHANGED | REJECTED |
| stale_derived_workload_hash | DIAG_WORKLOAD | REJECTED |

Ten corrupted copies were rejected, including all seven requested mutations plus cross-protocol fields, weakened p99 acceptance and stale derived workload identities. Each copy's ordinary hashes were repaired before validation except the deliberate hash-corruption test, so failures test semantic invariants rather than merely hashing. Test copies never overwrite the frozen file. Four RNG draws, 12 toy quantile ratios and 6 interval endpoint fixtures pass under existing NumPy 1.24.4. Fixtures are dimensionless and explicitly SYNTHETIC, never measured engine observations.

Static reproduction commands (from repository root; output paths must be new):

```sh
python3 docs/task15_static_v1_1_0/validate_protocol.py docs/task15_tail_attribution_protocol_v1.1.0.json --output /NEW/EXTERNAL/static-result.json
# With the already installed NumPy 1.24.4 environment, add --self-test.
# On a host without Mac-local evidence use --portable; external identities remain explicitly UNVERIFIED.
python3 docs/task15_static_v1_1_0/generate_amendment.py --parent docs/task15_tail_attribution_protocol.json --evidence /PRESERVED/TASK14 --reviews /SUPPLIED/REVIEW --output-dir /NEW/EXTERNAL/regeneration
```

These are static tools, not the planned experiment runner. Full local validation output and initiation manifest stay in the external amendment directory; a compact static result snapshot and synthetic fixtures are committed under `docs/task15_static_v1_1_0/`. No CTest, Python integration suite, benchmark, clock calibration or profiler ran.

## 12. Runtime Integrity

| Runtime tree/blob | Unchanged Git object |
| --- | --- |
| native | 138c63b487e56f420cb4549a5584a89656530fe8 |
| backend | 6216e4b0e94c2269b35b8bca94c44b13537331a7 |
| frontend | b02030ebc937c0ba5e371923c75ad7465e643dee |
| tools | b9de05af61a90a141bb9811fa37ee3441687b228 |
| CMakeLists.txt | e8d3d61e7284d3138090f9bfacb1912d14e4f6f3 |

These equal both Task 14 and the parent documentation commit. Static tooling resides under docs, preserving the tools runtime tree as well. The original v1.0 JSON/Markdown byte hashes match the preserved initiation manifest. All original evidence reads are immutable; no original raw files were rewritten. Native comparator/graph/algorithm/API/build configuration remain untouched.

## 13. Remaining Limitations

Eight sessions and extreme percentile-bootstrap endpoints remain limited; v1.1 cannot promise robust population-wide production-tail assurance. The strict zero-regression gate may remain INCONCLUSIVE. Optional per-iteration-index balance is not guaranteed. Targeted C coverage and larger buffers affect diagnostic conditions but not A/B/D workloads. Future preflight must verify external binaries/graphs/source files, compiler/SDK selection, permissions, effective clocks, overhead, trace completeness, memory capacity and storage on the actual collection host. SDK declarations/template listings are documentary capability evidence, not proof that instruments worked. Portable verification cannot certify Mac-local bytes.

Task 14 F2's tail cause remains unresolved, along with possible frequency/core/cache/allocator interactions that current tools cannot isolate. No new causal attribution is claimed. Global absence of prior Task15 collection remains UNVERIFIED beyond available records; no new observations were used by this amendment. Independent re-review is still required before separately authorized preparation.

## 14. Git Delivery

Commit only these versioned documents, amendment metadata and docs-scoped static tooling to `codex/genuine-bmssp-engine`; no raw measurements/binaries are committed and main remains unchanged. The actual post-delivery commit SHA, remote match, clean-tree check, new Markdown hash and ledger/tool hashes are recorded in the final handoff and external delivery JSON, avoiding a self-referential commit hash. Original v1.0 files stay frozen. Review the complete documentation/static-tooling diff before committing.

## 15. Next Single Task

**Independent review of protocol v1.1.0.** No harness implementation, calibration, benchmark collection, optimizer work, BMSSP2026 work or Task16 is authorized.

Task 15 protocol v1.1.0 is ready for independent
re-review. Experiment execution remains unauthorized.
