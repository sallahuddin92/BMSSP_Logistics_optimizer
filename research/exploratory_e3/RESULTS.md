# BMSSP Exploratory E3 — Hardware and Scheduler Attribution

Label: EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION.

## 1. Verdict

**BLOCKED.** Scientific attribution is **INCONCLUSIVE**; implementation status is
**PARTIAL**. The bounded workflow stopped correctly, but the campaign did not
complete. The first traced road recording crossed the frozen 256 MiB per-trace
abort threshold during save after worker exit. Termination left an unexportable
trace. No limits were raised after primary data, no replacements occurred, and
no further sessions were dispatched.

## 2. Baseline and Executable Identities

Checkout: /Users/sallahuddin/Projects/BMSSP_Logistics_optimizer.
Branch: research/bmssp-exploratory-scheduler-e3.
Parent: e6d562782a5d292b06d2db8e01acd1f2727e2932.
Origin: https://github.com/sallahuddin92/BMSSP_Logistics_optimizer.git.

A1/A2 share identical A executable bytes in separate processes. D uses that same
executable's native reference Dijkstra path. B links the exact E1 H1 source.
Off/on wrappers are distinguishable binaries sharing the native library per
variant. Trace support surrounds the solve timer and does not modify the engine.
These fresh wrappers are not historical E2 executable bytes.

| Build/mode | Executable SHA-256 |
|---|---|
| A/off (A1/A2/D) | 29bc6a09f2a2e1ab065654d49fc294d2fa14ad7951f62a8a44b97650ef44c8e6 |
| A/on (A1/A2/D) | 8d3f5784976734a0865070843f58f2d6d36b6c17c44a1e225aa83074fc160e6a |
| B/off | 11cf00b7ff0492590ae5d108930c81d4def8c6494b3c559f1a0388ef56eefc16 |
| B/on | 36792665dd04eeaf20fc603ba2d27aabf80034df128ab3cb93a38b36eee918a6 |

Native library A: 24585b4da1c6157fd92f0aa1d6e0f095d1fa339dcf77b580e521aae617aad93f.
Native library B: d001ded1c9e1369812726308f9b5d4f20502ad043900ce3c1572015dc1049e91.
H1 patch: 5a53e00c09ee298cd919d70b31bbb8e59d3a641fd5d77fb95f418a0e3035bb78.

External build-identities.json retains source hashes, compile/link commands,
CMake caches, Mach-O UUIDs, symbol dumps and executable/library hashes.
CLT AppleClang 21.0.0 (clang-2100.1.1.101), SDK 26.5, Release arm64,
deployment 26.0, strict C++20 and existing numeric flags. Xcode 26.2 (17C52)
runs Instruments via process-local DEVELOPER_DIR; it does not replace the compiler.

## 3. Selected Road Workload

Selection was frozen from E2 before primary execution: top two CPU-excursion
positions, largest remaining wall-minus-CPU-excursion position, plus one fixed
nonextreme control. Excursions are relative to each condition/source E2 median
over A1/A2/B; D does not select BMSSP sources. The manifest retains the rankings,
original raw events, policy and E2 hashes.

| Road | Extreme positions → original source IDs | Control |
|---|---|---|
| Medium | 8→4999010002; 9→5748272917; 3→3250604903 | 1→13651534081 |
| Seremban–Port Dickson | 4→7201398769; 2→14071843298; 1→14184492982 | 5→4883808659 |

Medium: 14,464 vertices/35,530 directed edges. Corridor: 24,736/60,214.
Native graph hashes, respectively:
3ba57b021e6ad142f166b46c7eb1cc948861dd65bcc150f92c779ada370d27ce;
13ec03c40bcf86a82f180436baf515f4367da24192d046fcfc4a470a72dda8f0.
Original occurrences, parallel edges and binary64 weights are preserved.

## 4. Instrument Availability

The initial three-second System Trace probe recorded successfully without
privilege changes. Actual exports include thread-state, context-switch,
os-signpost, os-signpost-arg and target-capability, with PID/TID/core fields.

An explicit **pre-primary** amendment increased the recording window to ten
seconds and total trace abort threshold from 2 to 4 GiB. It allowed one additional
three-second System Trace + CPU Counters availability attempt, leaving the
sources and 48-session schedule unchanged. That attempt reported **“No counting
mode selected”** / “Select a counting mode for CPU Bottlenecks”; target stdout
was empty and its TOC had no data tables. Its successful shell exit did not
establish usable hardware counters.

Processor Trace is listed and its service advertised; actual recording/export
permission was not tested. Listed tools/capabilities are not usable metrics.
System Trace alone was locked for primary execution. No further probes,
sudo/private kperf/kpc, SIP/TCC, power or scheduling changes.

## 5. Execution Design

Planned: three blocks × two roads × four conditions × separate on/off processes,
48 sessions maximum, four sources/process, five repetitions/source and one
warmup/source. Expected 960 measured queries. Four Williams condition orders
balance every condition across slots; on/off precedence balances 3/3 across six
graph-block pairs. Graph order rotates; odd three blocks prevents perfect
within-graph first/last balance.

Actual: first medium block A1-off, A2-off, D-off, B-off completed; then A2-on
worker completed but its recorder failed. **Five attempts, four fully successful
sessions, 80 off samples and 20 on worker samples; 43 sessions unattempted.**
No corridor primary data or complete three-block experiment. Native builds,
correctness tests and analysis did not overlap primary execution.

The primary trace reached 284,217,344 bytes versus its 268,435,456-byte abort
threshold. The 100 ms polled guard is not a filesystem quota: serialization and
termination can overshoot. Total retained traces remain below the locked 4 GiB
threshold; pre-recording free space exceeded 3 GiB. All attempts are retained.
The frozen failure policy preserves an incomplete campaign without replacements.

## 6. Scheduler Evidence

The **availability probe only** has observed Running, Runnable, Blocked,
Interrupted and Preempted intervals. It deliberately combines 30 ms busy work
and 30 ms usleep. Its blocking is not road-tail evidence. Numeric running-core
IDs/transitions are retained; no unsupported performance/efficiency-core mapping.

Primary TOC recovery failed, exit 10: **“Document Missing Template Error.”**
No road-query running, runnable, blocking, wakeup or migration attribution exists.
Interrupted/Preempted remain distinct from Runnable/Blocked. No explicit
lost-event counter was established; full probe state coverage does not establish
globally lossless capture.

## 7. Hardware Execution

No attributed cycles, retired instructions, IPC, cache/TLB events, bottleneck
categories or frequency measurements. hardware-metrics.json stores nulls and
the actual failed/untested reasons. CPU time alone cannot establish instruction
inflation, cache misses, core-type placement or hardware bottlenecks.

## 8. Query Trace Synchronization

Each worker query retains graph/condition/block/original-position/repetition ID,
PID/TID, six wall/CPU endpoint reads, rc/errno, signpost ID and independently
read RAW/Mach anchors before/after workload.

Probe PID 312/TID 6935332 joins six numbered signpost events to independent RAW
brackets. Feasible affine rate interval:
[0.9999990028830003, 1.000000670063741]. At feasible rate 1, offset relative to
first RAW origin lies in [2612371958, 2612372042] ns. The conservative full
rate/offset bounds are wider and retained per interval; 84 ns is not the whole
mapping uncertainty. All three probe intervals have full state coverage.
No UTC-only or assumed interchangeable-clock join.

Primary PID 4097/TID 6970875 has native endpoints/anchors but no exportable
events. **Zero primary query joins qualify.** Probe mapping is never transferred
to another recording.

## 9. Observer Perturbation

Only first-block medium A2 has both worker modes, 20 samples each.
Median wall: 39.401500→40.299917 ms (+2.28%).
Median thread CPU: 39.327271→40.181125 ms (+2.17%).
Peak process RSS: 31,113,216→32,456,704 bytes (+4.32%).
Per-source wall median ratios range 1.0046–1.0747.

This incomplete pair includes wrapper/host variation, not calibrated overhead.
Counts match only for this pair. A1/B/D and corridor observer pairs are missing.
Event loss is unknown; the sole primary TOC export failed. No overhead subtraction
or pooling of on/off samples. Traced timing is not production performance.

## 10. Tail Root Cause

The pre-primary diagnostic rule flags wall OR CPU above its own E2 graph/
condition/source nearest-rank p95. **15 of 100** retained queries qualify;
all are **INSUFFICIENT_EVIDENCE**. spike-classification.jsonl retains IDs,
endpoints, thresholds, available same-block controls and absent-event reasons.
No fabricated scheduler, blocking, work-inflation or hardware classifications.

Incomplete medium trace-off medians, milliseconds:

| Condition | n | Wall | Thread CPU |
|---|---:|---:|---:|
| A1 | 20 | 38.717480 | 38.703250 |
| A2 | 20 | 39.401500 | 39.327271 |
| B | 20 | 38.785605 | 38.696979 |
| D | 20 | 0.632209 | 0.632375 |

A2/A1 wall median differs 1.77% despite identical bytes. B retains a 53.136542 ms
wall /49.229958 ms CPU extreme, without synchronized events to explain it.
Small targeted comparisons establish neither candidate-specific causality nor
representative p99. Deterministic BMSSP work is identical by retained source
across A1/A2/B/on/off.

## 11. H1 Acceptance Assessment

**STILL_INCONCLUSIVE; unaccepted and not promoted.** Prior E2 median/allocation
reductions remain historical evidence. Incomplete E3 supplies neither a
candidate-specific mechanism nor enough matched controls for acceptance/rejection.
No post-data acceptance threshold.

The dedicated H1 tail investigation is **closed**. No E4 broad tracing or
replacement campaign follows from this result.

## 12. Correctness and Stability

Both A and B pass all 19 native tests (8.91 /8.37 seconds).
Both variants pass eight selected source/graph cases against native Dijkstra:
all-target exact distances and directed reachable/unreachable path validation.
A/B binary distance dumps match on both roads. Existing tests retain zero-weight
and parallel-edge cases. All 100 retained fingerprints are stable within
algorithm/source; BMSSP work agrees and profiling counters remain zero.
Finite tests are not a proof of universal BMSSP correctness.

All retained clock reads succeed. Twenty-seven signed negative wall-minus-CPU
estimates remain; no CPU duration exceeds its wider wall envelope. E2's 4,007 negative
estimates remain a limitation, not retrospective scheduler evidence.

Seven evidence tests pass: real XML references, every clock bracket, rejection
of missing anchors/PID mismatch, literal probe-state separation, refusal to
attribute incomplete primary traces, and native source/binary identities.
Initial wrapper compile failures remain logged; fixes preceded primary
execution. No stubs or weakened native expectations.

## 13. Scientific Separation

Native engine and H1 patch unchanged. E1 branch remains
04cf15c043e290c375155d7b0f2cd30c4c65d4f5; E2 remains
e6d562782a5d292b06d2db8e01acd1f2727e2932; original engine branch remains
5e8b11b4db8a0883969e7fe1405b048f419d7f07.
E2 receipt remains
1ba5441d570562bb914e32872f99e69207d95da48ec8382dac76778cd67706bc.

No existing tracked file outside E3 changes. Frozen Task15 protocol/harness/
archived binaries were not modified or executed. No Task15 scientific collection,
calibration, renewed provenance audit, StarNAV access/integration or Valhalla claim.

## 14. Source and Evidence Delivery

Source: research/exploratory_e3/ on research/bmssp-exploratory-scheduler-e3.
Final commit and matching pushed ref are recorded in Git and delivery response,
outside the immutable receipt to avoid self-reference.

External evidence: /Volumes/RAID1_PHOTOS/BMSSP-exploratory-E3-3qo_x183/.
completion-receipt.json lists every external file SHA-256 and delivered source
hash. commands.jsonl retains exact native build/test/record/export argv,
developer environment, durations, exits, guards and stream hashes. The receipt
covers failed traces, selection, schedule/amendment/locks, source/executable/
symbol identities, raw timings, probe exports, synchronization, observer/control
comparisons, classifications, failures and decisions.

executed-source retains the pre-dispatch helper version; README documents the
delivered blank-line parser/provisional-state corrections. Native binary bytes
and measurements are unchanged. No old evidence deleted. seal.py --verify
checks external and source file sets. The report itself is also archived.

## 15. Next Single Engineering Task

Reduce remaining allocation/ownership overhead in recursive bounded-frontier
operations, starting from the measured E1 allocation/frontier hotspot and
validating unchanged exact distances/work against native Dijkstra. E1 observed
22.9–24.4% exclusive allocation activity and 23.3–25.3% inclusive frontier insert
activity; these overlap and must not be added. Return to the substantially
larger BMSSP-versus-Dijkstra bottleneck. Keep H1 unaccepted and its tail
investigation closed.
