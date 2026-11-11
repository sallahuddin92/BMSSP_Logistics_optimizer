"""Review content: proposals only, never an authorization or execution recipe."""
STRATEGY='''# Controlled Option B strategy — proposal, not authorization

The frozen original baseline and candidate binaries remain the production anchors. Current hashes establish a new current build-input identity only. No historical byte continuity is inferred. Construction is prohibited until independent review, a versioned amendment and separate authorization.

1. **Source snapshots:** authenticate each archived original source snapshot against its own frozen commit and Phase 10 source manifests; materialize future diagnostic copies outside production. Preserve all copyright/license notices. Never use current HEAD as a substitute for either source commit.
2. **Build inputs:** first close missing pybind11 and runtime inputs through a separately scoped, explicitly reviewed dependency decision. This task installs nothing. Revalidate every current root identity immediately before any authorized construction. Preserve exact per-variant compile/link records in the build comparison JSONs; future substitutions must be listed individually, not rewritten into those historical records. Use a clean environment with explicit CLT/SDK/Python/CMake selections and archive actual expanded argv, environment, dependency files and linker map. Disallow ambient CPATH/LIBRARY_PATH/DYLD injection and implicit SDK/target selection.
3. **Compiler/SDK differences:** current AppleClang/version matches are observations, not historical byte equality. Require a reviewed current input lock for each variant. G4 requires an explicit alternative provenance amendment; G7 must lock both originals and new artifacts before calibration. A current unmarked control twin may isolate instrumentation effects, but cannot replace original-versus-diagnostic G8.
4. **Numeric/ABI:** retain binary64 checks, symbolic ordering, exception/RTTI/LTO/target behavior, -O3 -DNDEBUG -std=c++20 -arch arm64 -fPIC and all actual archived flags. Absence of an explicit flag is a default, not proof of its value. Future compiler verbose expansion must reconcile implicit CPU/features, FP contraction/rounding, exceptions, deployment and ABI defaults. Check exported signatures, Python CPython311 contracts, sizeof/alignof and legal offsetof; no fast-math or unchecked arithmetic changes.
5. **Graphs:** compare frozen GraphML bytes, graph/source/snapshot and position occurrence identities, CSR/degree-reduction mapping, edge order, original directed-edge IDs, transform fingerprints and k/t. Duplicate source occurrences remain distinct positions; no deduplication of the frozen workload.
6. **Distances:** outside all timing, compare every complete binary64 vector against its own frozen production variant for all 100 positions on each of three graphs (600 paired comparisons across two variants). If complete trusted original vectors are absent, a separately authorized campaign requires 600 original and 600 diagnostic solves. No solves occur here. Phase 7's six queries are insufficient. Existing reference/correctness gates remain required, without replacing them with fingerprints alone.
7. **Paths:** validate directed edge continuity, source/target endpoints, edge IDs and exact selected four path fingerprints in frozen target order; include unreachable and zero-distance behavior. Preserve all existing broader directed-path gates.
8. **Work:** compare full canonical deterministic work/materialization objects, query status and disabled profiling state per occurrence, not elapsed time counters. Any mismatch fails G2; no tolerance or retry to erase failures.
9. **Lifetime:** destroy prior Query and Python copies before T0, retain current native result through T5, fingerprint outside timing, observe T6 destruction separately. Test native ownership, exception cleanup and no aliasing/dangling views in applicable existing gates.
10. **Machine code:** implement a separately reviewed original-versus-diagnostic comparison per variant for all frozen hot families and top-level solve compute regions. Preserve opcode/register/CFG/frame/spill differences; normalize only frozen-allowed addresses/relocations/debug metadata. Record symbol and loop offsets, lengths, alignment modulo64 and page crossings. Unknown attribution is Class M, not an ignored range.
11. **Mapping:** originals lack complete verified source/inline mapping. Source/symbol/disassembly triangulation would require independently verified coverage including inlined clones, cold splits and stripped/unknown regions; a fresh diagnostic DWARF file cannot supply original attribution. Phase 9's 147 selected symbol records per variant and seven unknown slots outside that selected set are partial evidence, not full G8 acceptance. Marker-window subtraction is unsupported; implement and independently test exact insertion-window attribution before it can be considered. If mapping remains unresolved, unchanged G8 cannot pass. Changing G8 requires a new reviewed amendment with explicitly restricted claims, never a silent Class I/L assignment.
12. **Layout:** record complete layout manifests, symbol/loop placement and relevant object alignment; same sizeof alone is insufficient. Class L requires independent layout-risk approval and is not assumed performance-equivalent. Compute/frame/spill changes remain Class M.
13. **Perturbation:** isolate markers/preallocated buffers in whitelisted external-copy diffs; compare original, current unmarked control and marked diagnostics separately. A two-current-build comparison explains instrumentation but cannot erase compiler-origin changes relative to originals. Keep A originals unmodified and isolated; no diagnostic timing pooled into A.
14. **Calibration:** after G1–G8 and separate authorization, preserve frozen G9 clock/aperture/differential-overhead/count-capacity/loss/timebase gates before any measurement; G10 signatures required before collection. C/D storage remains 512 GiB. No clock reads for calibration, recording or collection here.
15. **Limits:** current input lock is partial; historical toolchain reconstruction remains unrecoverable. Semantic equality does not establish performance equivalence or causal attribution. Preserve failed artifacts, fixed schedule/counts/exclusions/statistical estimands and all original stopping rules. No speedup is asserted.

Only two routes exist after this submission:

- Route 1: independent review plus required amendments completed, then separately authorized diagnostic construction.
- Route 2: comparability remains blocked; keep original Task 15 confirmatory work blocked and separately scope exploratory optimization using a freshly declared baseline. Never pool or label exploratory results as confirmatory Task 15 evidence.

Neither route starts automatically.
'''
REVIEWER='''# Independent reviewer decision template — intentionally unfilled

Decision (ACCEPTABLE FOR FURTHER REVIEW / CONDITIONAL, AMENDMENT REQUIRED / BLOCKED):

Reviewer name and relevant compiler/scientific expertise:

Independence/conflict declaration:

Evidence bundle receipt SHA-256 reviewed:

Finding on incomplete dependency closure:

Finding on G4/G7 alternative provenance amendment:

Finding on original-versus-diagnostic G8 coverage and I/L/M classification:

Class L layout-risk approval, if applicable (separate explicit rationale):

Required additional evidence and restrictions:

Protocol amendment identity/decision (if separately reviewed):

Signature:

Date:

This blank template grants no authorization. A completed review is external evidence that must be authenticated in a future manifest. Construction, calibration and collection each require their own authorization.
'''

def amendment(gates,protocol):
    lines=['# Proposed amendment impact — UNAPPROVED\n', 'Frozen protocol identity: '+protocol['identity']['sha256']+'. Do not modify v1.3.0.\n', 'The alternative current-toolchain provenance strategy requires a versioned pre-data amendment before construction. This document proposes no schedule, estimand or G8 relaxation.\n']
    for g in gates:
        lines += ['## calibration.diagnostic_build_equivalence.gates[id='+g['id']+'].pass\n','Existing exact requirement: '+g['pass']+'\n']
        if g['id']=='G4_flags':alt='Replace only the unproven historical byte-continuity premise with explicit current-byte identities, exhaustive differences and independent equivalence evidence. Historical identities remain unproven. This is REQUIRED AMENDMENT, not present compliance.'
        elif g['id']=='G7_identity_lock':alt='Retain immutable original and new diagnostic identity locks; add current-tree manifests, missing-closure resolution and reviewed alternative provenance. Construction decision must precede any new artifact; calibration still awaits all original locks/approvals.'
        else:alt='No proposed change. Requirement retained exactly. Current status and missing evidence are in g1-g10-impact-matrix.json.'
        lines+=['Proposed alternative: '+alt+'\n']
    for path,value in [('acceptance.diagnostic_equivalence_gate',protocol['acceptance']['diagnostic_equivalence_gate']),('acceptance.E_equivalence',protocol['acceptance']['E_equivalence']),('acceptance.F_instrumentation',protocol['acceptance']['F_instrumentation']),('correctness_protection.before_execution',protocol['correctness_protection']['before_execution']),('amendment_policy',protocol['amendment_policy'])]:
        lines+=['## '+path+'\n','Existing exact requirement: '+value+'\n','No relaxation proposed. Add cross-reference to a separately approved alternative-provenance amendment only after independent review.\n']
    lines+=['## Scientific impact and decision\n','Technical reason: Phase 10 cannot recover historical compiler/linker/SDK/Python/pybind byte identities. Matching current versions cannot satisfy that premise. Independent evidence must establish closed current dependencies, source/build/numeric/ABI compatibility and valid original-versus-diagnostic G1–G10, including complete G2 and G8.\n','A retains frozen original binaries, timing boundaries and exclusion rules. B diagnostic timing validity remains blocked by G4/G7/G8/G9/G10; C allocation attribution and D Instruments attribution also remain blocked and retain 512 GiB storage. No diagnostic evidence substitutes for A. No A/B/C/D validity is granted here.\n','Statistical estimands, all session/cluster counts, source order, warmups, P1/P2, ratios, bootstrap intervals, thresholds and missing-cluster rules remain unchanged. An amendment that alters G8 acceptance or uses a new production baseline cannot claim the original confirmatory design unchanged; it must state changed causal scope and review any new estimands before data. Route 2 is separately scoped exploratory work, with no pooling.\n','Unchanged conditions: all frozen source protections, graph identities, original binary hashes, full-position exactness, lifetime policy, gate failures, Class I/L/M rules, calibration, independent approvals and prohibitions. No currently available evidence meets unchanged G8. There is no approved amendment in this package.\n']
    return '\n'.join(lines)

def packet(items):
    lock=items['current-toolchain-lock'];lines=['# Independent Option B technical submission\n','## Executive decision\n','Author recommendation: BLOCKED. The technical submission can be reviewed; it does not approve Option B. External decision: can the proposed alternative current-toolchain provenance, after dependency closure and an explicit G4/G7 amendment, support valid original-versus-diagnostic G1–G10 evidence under unchanged G8?\n','## Established facts\n','Phase 10 outputs authenticated against the pinned completion receipt establish original source/output anchors and final unrecoverable historical toolchain provenance. Original per-variant records are reproduced in baseline-build-comparison.json and candidate-build-comparison.json. Full current selected SDK and compiler/Python/CMake trees were physically inventoried; exact paths, SHA identities, failures and aliases are in the machine-readable lock.\n']
    for key,t in lock['trees'].items():lines.append(f"- {key}: {t['status']}; entries {t.get('entry_count',0)}; tree SHA `{t['tree_sha256']}`; errors {len(t['errors'])}.")
    lines+=['\n## Historical limitations\n','Current compiler/linker/SDK/Python hashes must never fill missing historical SHA fields. Original pybind inputs are unavailable per Phase 10; old temporary paths were not reopened. Selected current pybind11 headers/CMake package are missing. Shared-cache and dynamic-loader closure remains incomplete.\n','## Proposed Option B strategy\n','Read controlled-equivalence-strategy.md steps 1–15. Exact frozen requirements accompany this submission in the gate matrix JSON; this is an executable staged engineering specification whose build/solve stages require future authorization. No diagnostic artifact exists from this task.\n','## Equivalence evidence\n','Existing: authenticated original output/source/build records and full current physical inventories. Missing: complete dependency closure, independently approved provenance amendment, actual diagnostic comparisons, full-position G2, ABI/layout measurements, complete original inline attribution, reviewed insertion-window tooling and G9 calibration. Phase 7 six queries do not satisfy G2.\n','## G1–G10 decision table\n','|Gate|Current status|Required work|','|---|---|---|']
    for g in items['g1-g10-impact-matrix']['gates']:lines.append('|'+g['id']+'|'+g['status']+'|'+g['required_work']+'|')
    lines+=['\n## Risks\n','Compiler/SDK defaults can change numerical behavior, inlining, register allocation, ABI and placement. Matching distances/counters cannot rule out latency changes. Instrumentation can alter code/layout/cache behavior and result lifetime. Missing original source/inline mapping and unsupported marker subtraction preclude reliable Class I/L attribution. Selection of only decodable functions biases acceptance. Preserve all unknowns as Class M/blocking; no selected-set PASS.\n','## Required protocol decision\n','G4 alternative provenance and G7 lock workflow require a versioned amendment before construction. G8 remains unchanged and currently BLOCKED. Relaxing its criteria would require separate explicit scientific review and restricted claims, never automatic equivalence. See proposed-amendment-impact.md for exact clause texts, A/B/C/D and estimand impact.\n','## Reviewer outcome\n','No independent decision exists. Use reviewer-decision-template.md; all signature/date/decision fields are blank.\n','## Conditions for proceeding\n','Resolve dependency closure without calling current bytes historical; independent specialist reviews this receipt, G4/G7 amendment and G8 feasibility; obtain explicit construction authorization. Subsequent actual G1–G10 and Class L approvals, separate calibration authorization and collection authorization remain required.\n','Route 1: after independent review and required amendments, separately authorize diagnostic construction.\n','Route 2: keep confirmatory Task 15 blocked and separately scope exploratory optimization with a fresh baseline; never relabel or pool exploratory evidence. Neither route is initiated.\n']
    return '\n'.join(lines)
