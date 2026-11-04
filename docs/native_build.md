# Standalone native build and tests

Requires CMake >=3.20 (>=3.21 for presets), a C++20 compiler/standard library,
and a native build tool. There are no external native dependencies or downloads.
Apple Clang and modern Linux Clang/GCC are intended targets; Linux validation is
reported separately from macOS execution. Python and Docker are not required.

Run from the repository root. Presets default to sibling `../bmssp-native-build/`
directories. For an isolated build, explicitly select a fresh external directory:

```sh
BMSSP_BUILD=$(mktemp -d "${TMPDIR:-/tmp}/bmssp-native.XXXXXX")
cmake --preset debug -B "$BMSSP_BUILD/debug"
cmake --build "$BMSSP_BUILD/debug" --parallel 4
ctest --test-dir "$BMSSP_BUILD/debug" -V
cmake --preset release -B "$BMSSP_BUILD/release"
cmake --build "$BMSSP_BUILD/release" --parallel 4
ctest --test-dir "$BMSSP_BUILD/release" -V
cmake --preset sanitizers -B "$BMSSP_BUILD/sanitizers"
cmake --build "$BMSSP_BUILD/sanitizers" --parallel 4
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  ctest --test-dir "$BMSSP_BUILD/sanitizers" -V
"$BMSSP_BUILD/release/shortest_path_cli" --demo
```

Without `-B` overrides, `cmake --build --preset debug` and `ctest --preset debug`
use the default sibling directory. Source-tree builds are rejected. For Linux,
use the same commands; select GCC/Clang through `CXX` in a fresh build directory.
No Linux success is implied by these instructions. Unsupported sanitizer/compiler
combinations fail configuration explicitly. Apple's sanitizer runtime does not support
`ASAN_OPTIONS=detect_leaks=1`; use its default or explicitly set `detect_leaks=0`
on macOS. This does not validate leak detection. If an older sanitizer runtime
hangs before main, first test a minimal instrumented program and select a newer
installed compiler using `-DCMAKE_CXX_COMPILER=/path/to/clang++` in a fresh build
directory. Do not classify runtime-startup failure as an algorithm failure.

Warnings are errors: GCC/Clang use `-Wall -Wextra -Wpedantic -Wconversion
-Wsign-conversion -Wshadow -Werror`; MSVC uses `/W4 /WX /permissive-`. Build type
controls optimization/debug flags. Sanitizers add address/undefined instrumentation
and frame pointers. Compile commands are exported. Do not enable fast-math.

CTest runs the foundation groups plus degree_reduction, symbolic_label, frontier,
bounded, bmssp, numerical, and separate Dijkstra/BMSSP CLI smoke checks. Native
case assertions remain active with NDEBUG. The differential test prints graph,
source-query, and path-check totals; any failure prints its seed and full raw
fixture. Seeds are 2025, 17033, and 45141 (0xB055); sizes 1,2,5,12,32,64 and edge
probabilities 0%,5%,25%,100%, with parallel edges and quarter-unit weights. A
10,000-vertex sparse chain and manually computed fixtures are separate tests.

## CLI format

`--demo` reports the known seven-unit directed path. Otherwise:

```sh
printf '3 2\n5000000000 5000000001 5000000002\n10 5000000000 5000000001 2\n20 5000000001 5000000002 3\n' \
  | "$BMSSP_BUILD/release/shortest_path_cli" 5000000000 5000000002
```

Input is whitespace-delimited: vertex count, edge count, all external vertex IDs,
then `edge_id from_id to_id weight` per edge. IDs/counts use decimal integer tokens.
Duplicate IDs, missing endpoints, truncated/trailing input, invalid weights and
sources are errors. Output explicitly names `reference_dijkstra`; unreachable is
`reachable=false distance=inf` with empty path lists. Exit 0 means a completed
query (including unreachable), 1 means input/query error, and 2 means usage error.
Distances have no assumed geographic unit. Output includes original edge IDs.

The native target never builds/imports the legacy extension or changes the API,
VRP, frontend, Dockerfiles, or GitHub workflow. Existing regression tests can be
run in the isolated Task 3 environment with its outbound-network guard, a fresh
external GRAPH_CACHE_DIR, PYTHONDONTWRITEBYTECODE=1, and pytest's cache disabled.
Do not use `run.sh clean` or download road datasets for native verification.

## Explicit BMSSP selection and bounded exploration

```sh
"$BMSSP_BUILD/release/shortest_path_cli" --bmssp-demo
"$BMSSP_BUILD/release/shortest_path_cli" --algorithm bmssp SOURCE TARGET < graph.txt
"$BMSSP_BUILD/release/shortest_path_cli" --algorithm dijkstra SOURCE TARGET < graph.txt
"$BMSSP_BUILD/release/bmssp_benchmark"
```

The original no-option CLI remains Dijkstra. BMSSP output identifies the algorithm
and emits recursive/pivot/frontier diagnostics. The comparison tool uses identical
original graphs, seed 2025, one untimed warmup per source and three timed repeats;
preprocessing is reported separately and correctness gates run for every result.
It is a bounded exploratory measurement, not evidence of an asymptotic speedup.
See bmssp_2025.md for arithmetic/complexity limits and bmssp_validation.md for
measured results and precise commands. No Python/API integration occurs.
