# G8 ARM64/Mach-O comparison specification — control-plane version 1

Status: **specification for independent review; actual G8 classification PENDING**.
No diagnostic binaries, compiler invocations on engine sources, or profiler recordings
are produced by this package. `g8.py` accepts only explicitly synthetic fixtures. Its
small instruction subset is a test of conservative policy, not a Mach-O decoder.
Unsupported fixture policies/opcodes/targets fail closed. No command can classify a
real binary as acceptable at this stage.

## Inputs and tool lock

Compare baseline production to baseline diagnostic, and candidate production to
candidate diagnostic separately. Never substitute candidate-vs-baseline comparison
for the production-vs-corresponding-diagnostic gate. Require the protocol's exact
production SHA, a separately locked diagnostic SHA, source-only insertion diff,
compiler/SDK/link flags, Mach-O headers, section maps, symbol/function-start tables,
relocations/chained fixups, unwind information and per-function coverage inventory.
Capture full argv, tool paths, versions, exit codes and untruncated stdout/stderr.
Do not claim flags from disassembly alone: require archived compile/link command
manifests and resolved compiler/SDK identities (N5 remains a future host gate).

Future read-only command forms, **documented but not run on diagnostic artifacts**:

```sh
xcrun --find llvm-objdump
xcrun llvm-objdump --version
xcrun llvm-objdump --macho --universal-headers FILE
xcrun llvm-objdump --macho --arch=arm64 --syms --section-headers FILE
xcrun llvm-objdump --macho --arch=arm64 --function-starts=both FILE
xcrun llvm-objdump --macho --arch=arm64 --reloc --chained-fixups --dyld-info FILE
xcrun llvm-objdump --macho --arch=arm64 --disassemble --demangle FILE
```

These forms require validation against the locked local tool's help; unsupported
options or mixed-output ambiguities block extraction. During this task only local
`llvm-objdump --help` was consulted, without disassembling any binary. Future
extraction must save each table separately if combined output is ambiguous.
Required slice is **arm64**, matched Mach CPU/subtype. Do not silently use arm64e,
x86_64, a different universal slice, or translated execution. Multiple slices,
overlapping sections, unsupported formats, unrecognized chained fixups or unresolved
architecture selection are classification failures (Class M / blocked).

## Function and instruction coverage

1. Resolve mangled linkage names, demangled names, section and unslid VM address,
   file offset and exact extent. Demangled text alone is not a unique key. Detect
   overloads, duplicate/weak/coalesced symbols and thunks. Resolve aliases explicitly;
   never omit a symbol because it is inconvenient to compare.
2. Inventory `SymbolicLabel::compare_nodes`, its pure/profiled helpers where emitted,
   recursion, BaseCase, FindPivots, specialized frontier, graph/degree reduction,
   numeric checks, label ownership/allocation and top-level solve compute regions.
   Exact linkage names and transitive callees come from the locked artifacts and
   source map; no blanket wildcard removal. Mark insertion windows individually.
3. For inlining/LTO, use DWARF inline ranges/source correspondence plus full containing
   function instruction coverage. If a logical function has no standalone symbol,
   compare all containing regions; do not call it unchanged because it disappeared.
   Missing/stripped/ambiguous symbols, missing bounds, uncovered compute bytes or
   unavailable inline correspondence block classification. Rebuilding or adding
   symbols to production is not an automatic fallback; it changes the artifact.
4. Decode every relevant instruction using the locked Apple LLVM decoder. ARM64
   instruction boundaries are 4 bytes; verify ranges, executable sections and
   data-in-code markers. Do not decode literal pools as instructions. Preserve
   padding and report its placement; normalization cannot remove unknown bytes.
   Instruction aliases need exact decoded operand/encoding equivalence, not an
   unreviewed text substitution. Parse failure means M, never an empty function.

## Permitted address normalization

Normalize only proven relocation/address effects, with a record for every change:
source instruction index/address, original encoding/operand, relocation/fixup type,
resolved semantic target (mangled symbol + exact byte addend, section + offset, or
local block/instruction index), and corresponding target in the other artifact.
ASLR slide is not a linker-layout change; use original unslid Mach-O addresses.

- Local `b`, `bl`, conditional branches, `cbz/cbnz`, `tbz/tbnz`: map the destination
  to an exact local block/instruction boundary or unique external symbol+addend.
  Keep condition code, register, test bit, width, call-vs-branch and fallthrough.
  Preserve CFG edges, block order, back edges and call targets. A changed byte
  displacement can be normalized only when that semantic edge is proven identical.
  Displacement/branch-range changes remain in the layout-risk report.
- `adr/adrp`, literal loads and `add` page-offset materialization: normalize a full
  relocation-proven address sequence to exact symbol/section+addend, preserving
  destination/source registers and sequence length. Never erase an immediate simply
  because it resembles an address. An unmatched `adrp`, ambiguous data target,
  relaxation to a different instruction sequence, changed GOT/TLV access, or missing
  fixup provenance is M. Record raw page/offset and relocation kind before replacing.
- Indirect branches/calls, pointer authentication or stubs: preserve opcodes,
  authentication/key/modifier, registers, binding target and stub semantics. Missing
  unique resolution blocks comparison. Do not normalize an arbitrary `br/blr` to
  “call”. Changed pointer-authentication sequences or unsupported ISA features are M.

Never normalize away arithmetic constants, stack offsets, register allocation,
operand width, signedness, memory ordering, branch conditions, test bits, exception
edges, alignment instructions or profiling/TLS bookkeeping. Compare exact decoded
register operands. Any tolerated alias presentation difference must be backed by
identical decoded encoding/semantics and recorded; otherwise M.

## Frames, spills and control flow

Compare complete prologues/epilogues, stack-pointer deltas on every path, stack
alignment, unwind/exception regions, callee-saved register sets, spill/reload opcodes,
registers, offsets, pair load/store ordering, pre/post-index writeback, dynamic stack
adjustments, return/tail-call structure and paths through approved insertion windows.
Examples such as 16-byte to 96-byte frame changes are material even when outputs
match. Do not remove extra loads/stores as “instrumentation noise” unless they are
inside an approved insertion window and cannot change uninstrumented compute state.
Cross-window register liveness/frame changes require M, not automatic approval.

Construct a CFG from exact decoded boundaries including direct branch, fallthrough,
call/tail-call, return and exception edges. Compare block contents, ordered edges,
loop headers/back edges and semantic targets. Unresolved jump tables, indirect CFG
edges, EH edges or partial regions are M until a separately reviewed implementation
can account for them. No guessed one-to-one block matching.

## Layout and classification

Record section and symbol extents, unslid/file offsets, instruction counts/bytes,
entry and every loop-header alignment modulo 16 and 64, raw addresses and all code
page boundaries. Obtain the actual host page size in future preflight; also report
4 KiB boundaries as a labeled diagnostic grid, not as an assumed M4 OS page size.
Report block-to-block/call distances, literal pool placement and page crossings.
Address-equivalent code can still have different cache, TLB or branch behavior.

- **Class I:** complete normalized compute instructions, registers, values, CFG,
  frames/spills, required entry/loop alignment and placement comparison are identical;
  only approved marker-only differences outside compute windows are present. Every
  compared region has full coverage. This is necessary evidence, not collection
  authorization or proof of zero observer overhead.
- **Class L:** normalized instructions/CFG/frames are equivalent but any relevant
  address, alignment, section/block placement, page crossing or relocation distance
  differs. Produce quantitative per-region deltas and require explicit independent
  layout-risk approval *before* use. Never auto-upgrade L to I or acceptable.
- **Class M:** any material/unexplained uninstrumented instruction/register/value,
  target/CFG/frame/spill change, unsupported normalization, missing evidence or
  incomplete coverage. Block the affected diagnostic cohort. A new reviewed
  amendment is needed for a different comparison policy; a boolean cannot override.

Whole-binary byte identity is not required. All other G1–G10 semantic, ABI/layout,
input/output/work, compiler, artifact-lock and overhead gates remain mandatory.
Actual G8 remains PENDING until separately authorized diagnostic artifacts and a
reviewed real extraction/comparison implementation exist. The synthetic comparator
cannot grant that approval, regardless of its fixture class.
