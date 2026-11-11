# Task 15 Phase 9 — static diagnostic build and G8 readiness

This separate standard-library package performs real read-only verification. It
never compiles, imports, dlopens or executes BMSSP or diagnostic binaries. Existing
engine, frozen artifacts, scientific protocol and production_gate() are unchanged.
Only `inspect --output /ABSOLUTE/FRESH/EXTERNAL` and synthetic `self-test` exist.
No build, workload, benchmark, profiler, calibration, collection or approval mode.

```sh
/Users/sallahuddin/Projects/BMSSP-task15-offline-reconstruction-jgt6c3vy/environment/bin/python -I -B research/task15_diagnostic_readiness/run.py inspect --output /FRESH/EXTERNAL/OUTPUT
```

## Toolchain and provenance

The frozen Task14 evidence index authenticates toolchain.json, both configure
command records, compile_commands.json, CMakeCache, CMake compiler metadata and
link.txt. Actual original flags/paths are retained verbatim. No build command is
executed. Historical build durations/package listings are not reused as new metrics.

Read-only queries compare default Xcode selection with explicit process-local
DEVELOPER_DIR=/Library/Developer/CommandLineTools and --sdk macosx. Exact current
compiler/linker paths, resolved paths and SHA are recorded. Compiler version/target,
SDKSettings JSON/plist, SDK SystemVersion, selected libc++ C++20 headers and library
stub identities are checked. Original compile records require -O3 -DNDEBUG
-std=c++20 -arch arm64 -fPIC and the actual original SDK root; unsafe numeric/ABI
flag substitutions are rejected. Header presence is not a compilation/ABI pass.

The CLT compiler and SDK26.5 can be selected process-locally without xcode-select
changes. The default Xcode context has a different compiler/SDK and the historical
default SDK-version lookup also failed. This is not evidence of a missing SDK.
Complete command/env/stdout/stderr/return codes are retained. No Xcode/CLT install,
upgrade, cache clearing or global selection occurs, and Xcode SDK26.2 is not
substituted for the archived CLT SDK. A deterministic nonexecuting invocation spec
uses the original CLT compiler path, explicit SDKROOT/DEVELOPER_DIR and original
per-file/link argv. Source/output/temporary Python/pybind mappings require review.

Current executable/metadata/header hashes do not retroactively prove original-build
byte identity. The authenticated historical records do not contain full compiler,
linker and SDK/header content locks. That exact historical continuity remains
BLOCKED until independently recovered/reconciled; matching version strings do not
remove it. The SDK identity explicitly describes its selected-file scope, not a
fabricated historical whole-SDK hash.

## Actual Mach-O inventory

Original binary SHA is checked before and after analysis. Tools are discovered
with explicit CLT selection and their exact paths/SHA/version results retained.
Read-only nm, otool, dwarfdump and llvm-objdump collect Mach-O/UUID/load commands,
dependency declarations/versions, symbol visibility/addresses, relocations,
LC_FUNCTION_STARTS, DWARF presence and ARM64 instructions. Atos help records its
availability only; no source lookup is invented without suitable debug information.
Dependency declarations are not a new runtime-loaded-library identity probe.

The initial Xcode LLVM17 decoder exposed unknown LSE instruction encodings. That
failed-coverage bundle is retained. CLT LLVM21 with explicit +lse disassembly
features is then used; this changes analysis decoding only, never compilation flags
or binary contents. All instruction addresses/words are tied to original __text
file bytes. Disassembly stdout identity/size is retained; unnecessary full text
copies are not. Critical-function raw instruction records are retained.

Coverage explicitly includes symbolic comparisons, recursive BMSSPWorkspace::run,
BaseCase, FindPivots, frontier, graph, degree reduction, engine solve and wrapper /
workspace families, with frozen source file hashes and declaration candidates.
Records include conservative machine ranges, counts, byte/normalized fingerprints,
control flow, registers, stack-touch/frame/spill evidence, aliases, entry mod64 and
16KiB page placement. Raw addresses remain for other layout analyses. There is no
claim that heuristic register/stack evidence replaces a full liveness/unwind proof.

LC_FUNCTION_STARTS proves starts and allocation upper bounds, not exact source
function/compute ends, inline coverage or approved marker windows. Missing embedded
DWARF and missing independently pinned external source/inline/window mapping remain
BLOCKED even after successful disassembly. Source declaration candidates and symbol
name matching are inventories, not a proof that every inline hot region is covered.
No missing family is silently designated not applicable. Original self-comparisons
must return CLASS_M/BLOCKED because this complete G8 coverage is not established.
They are negative checks, not production-vs-diagnostic comparisons.

## Comparator API and trust boundary

`codegen.compare` accepts only canonical VerifiedEvidence created by byte/tool
attestors, never JSON PASS/verified flags. Actual extraction reads/verifies the
original Mach-O and tool results; test attestation independently decodes a restricted
set of deterministic ARM64 words in explicitly synthetic non-Mach-O fixture files.
Synthetic records never mix with real records or become measurement eligible.

`mapping.attest_mapping(report, path, independently_expected_sha256, build_context)` is the future
entry for fresh byte/tool extraction plus a separately reviewed, hash-locked source /
compute mapping. It covers all located critical symbols and all required families,
checks source/binary/symbol inventories and complete instruction coverage, and
rejects missing/ambiguous mapping. A VerifiedBuildContext must first pass source, exact build-argument, compiler/SDK and
artifact checks through manifest.attest_build, including a separately supplied
independently expected canonical manifest SHA. No self-declared verified flag or
hash inside that manifest creates a verified build context. The expected mapping hash must come from an
independent review lock, not a self-declared hash/approval in artifact JSON. This
API does not create or authenticate a scientific approval signature.

Normalization permits independently resolved branch/relocation addresses and
separate debug metadata only. Internal targets use instruction indices; external
symbol identities must resolve. Encoding signatures mask only appropriate address
bits. Opcode, register, condition/branch destination, numeric offset, stack frame,
spill and instruction order survive. Unresolved address attribution, absent hot
functions, ambiguous boundaries or incomplete decode fail closed as CLASS_M.
Changed computation is CLASS_M/BLOCKED. Unchanged computation with address,
alignment/page layout changes is CLASS_L/PENDING independent layout-risk approval.
Equivalent computation/layout is CLASS_I/VERIFIED structurally, not scientific
permission. All outputs keep calibration/collection false and scientific pending.

This conservative version rejects marker-window subtraction rather than hiding
instructions. Future reviewed full compute regions outside insertion windows may
be supplied through mapping, but arbitrary exclusion windows are not supported.
Original source mapping and actual diagnostic artifacts are unavailable here;
actual production-vs-diagnostic G8 equivalence is BLOCKED with no classification.
No byte identity of entire production/diagnostic files is required by the comparator.

## Future Cohort B manifest

The closed manifest schema and two draft instances bind variant/source commit,
original source hashes/binary SHA, exact compiler/SDK/linker/dependencies and full
build records, permitted source insertions, forbidden compute changes, exact source
diff, diagnostic identity, coverage/evidence and missing prerequisites. Scientific
approval is pending; Class L approval and execution flags must be false; a claimed
G8 PASS in input is rejected and must be independently computed.

Source edits are insert-only at exact frozen line/hash anchors: T1 after BMSSP
source conversion, T2 before its original native start after source lookup, T3 at
its original end, T4 after native return. Reference Dijkstra is excluded. Existing
lines cannot be replaced, deleted or reordered. Only exact marker statements are
accepted. This whitelist is not a machine insertion-window approval. External
T0/T5/T6 worker/support identities and support-header definitions require separate
review; no arbitrary new support source is silently accepted. Comparator, recursion,
BaseCase, FindPivots, frontier, graph, degree, validation, k/t and semantics edits
are forbidden. No original source is patched by this tool.

## Bounds, outputs and tests

Minimum256MiB free is checked before work; total evidence is capped at64MiB. This
small static analysis does not satisfy or reduce the frozen C/D >=512GiB requirement.
No scientific evidence is deleted. Existing durable exclusive harness publication
and full inventory hashes are used; completion-receipt and hashes are revalidated.
Implementation, toolchain availability, production analyzability and actual G8
comparison readiness are distinct outcomes. Missing diagnostics never produce PASS.

32 deterministic tests cover all24 required cases, source-anchor acceptance, wrong
flags, unresolved attribution and forged verified objects. Build arguments are compared to independently supplied
complete reference records; additional flags cannot be silently introduced. Relevant existing static /
fake suites run unchanged; no Phase6/7 native campaign is part of regression testing.
