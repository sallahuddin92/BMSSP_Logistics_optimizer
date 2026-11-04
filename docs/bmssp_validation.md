# Task 5 executable validation

Status: PASS for implemented 2025 mechanisms and the measured correctness gates.
This does not establish the paper's running-time bound or a universal binary64
correctness theorem. See [engine contracts and limitations](bmssp_2025.md) and
[paper traceability](research_traceability.md). Baseline commit:
`871186df9854728e9980d7a3736ba8faa9197e92`, branch
`codex/genuine-bmssp-engine`. Production Python/API integration is not part of this task.

## Environment and evidence

macOS 26.5.1 (25F80), Apple M4 arm64, 10 logical CPUs, 16 GiB RAM;
Apple Clang 21.0.0 (clang-2100.1.1.101), CMake 4.3.3, Python 3.11.15.
Compiler: `/Library/Developer/CommandLineTools/usr/bin/clang++`.
The CLT compiler deliberately avoids the previously documented Xcode Clang 17
sanitizer startup issue (Task 4). No dependency versions were upgraded.
Build flags include C++20 and `-Wall -Wextra -Wpedantic -Wconversion
-Wsign-conversion -Wshadow -Werror`. All three builds pass these checks.

Local raw command JSON, stdout/stderr logs, JUnit, CSV, source hashes and compile
commands are retained at `/private/tmp/bmssp-task5.cXBqr9`. Each command JSON records
argv, working directory, elapsed wall time, and exit code; `command-manifest.json`
consolidates them. Temporary evidence is outside Git and may disappear if macOS
cleans its temporary storage. This report and the small
[raw benchmark CSV](validation/task5-performance.csv) are versioned.

## Reproduce the gates

From `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer`:

```sh
export BMSSP_BUILD=/private/tmp/bmssp-task5.cXBqr9
cmake --preset debug -B "$BMSSP_BUILD/debug" -DCMAKE_CXX_COMPILER=/Library/Developer/CommandLineTools/usr/bin/clang++
cmake --build "$BMSSP_BUILD/debug" --parallel 4
ctest --test-dir "$BMSSP_BUILD/debug" -V
cmake --preset release -B "$BMSSP_BUILD/release" -DCMAKE_CXX_COMPILER=/Library/Developer/CommandLineTools/usr/bin/clang++
cmake --build "$BMSSP_BUILD/release" --parallel 4
ctest --test-dir "$BMSSP_BUILD/release" -V
cmake --preset sanitizers -B "$BMSSP_BUILD/sanitizers" -DCMAKE_CXX_COMPILER=/Library/Developer/CommandLineTools/usr/bin/clang++
cmake --build "$BMSSP_BUILD/sanitizers" --parallel 4
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --test-dir "$BMSSP_BUILD/sanitizers" -V
```

| Gate | Outcome | Recorded command wall seconds |
|---|---|---:|
| Debug configure | exit 0 | 0.419058 |
| Release configure | exit 0 | 0.467425 |
| Sanitizer configure | exit 0 | 0.407375 |
| Debug full CTest | 12/12 passed | 9.852169 |
| Release full CTest | 12/12 passed | 1.938427 |
| ASan + UBSan full CTest | 12/12 passed, no findings | 40.685467 |
| Final BMSSP-only rerun, Debug | passed | 5.212101 |
| Final BMSSP-only rerun, Release | passed | 1.549037 |
| Final BMSSP-only rerun, sanitizers | passed, no findings | 17.653037 |
| Existing backend pytest | 34 passed, 0 skipped/errors/failures | 132.701923 |

The final targeted rerun follows a test-only improvement adding exhaustive failure
fixtures and reconstruction checks. The only subsequent C++ edit improves CLI
usage text; it was rebuilt in all configurations and explicit/default selections
were checked in all three (9/9). ASan leak detection is disabled because the Apple
runtime does not support it; no leak-check claim is made. Timing differences among
configurations are observations, not controlled performance comparisons. Some
build/test commands overlapped across independent build directories.

Build command records distinguish complete and incremental compilation. For
example, the initial full Release build took 4.515212 s and sanitizer build
3.824485 s. Final incremental builds took Debug 1.210788 s, Release 2.505832 s,
and sanitizer 1.818380 s; later test-only/CLI rebuilds are separately recorded.
No failed test was stubbed or expectation weakened.

## Correctness scope

Ten test executables contain 79 named cases (the 50 existing foundation cases
remain intact), plus two CLI CTest entries. New component cases cover:

- Constant-degree transformation, directed path projection, loops, parallel IDs,
  isolates, disconnected vertices, high-degree hubs and mapping validation.
- Symbolic distance/hop/reversed-path ordering, parallel ties, equality-valid
  relaxation, zero cycles, workspace reuse, 20,000-edge snapshot destruction.
- Full and partial BaseCase, strict finite/symbolic bounds, pivot early return,
  and an adversarial 8-frontier fixture reduced to pivots {11,12}.
- Block splits, duplicate minima, finite bounds, empty/reinitialized frontiers,
  terminal-fence recreation, and 4,800 fixed mixed operation steps against an
  independent ordered model, including stale-key deletion.
- Intermediate recursive coverage and exact completed-set contracts using a
  full-vector Bellman-Ford oracle with its own symbolic comparator. Runtime checks
  enforce disjoint children, monotone bounds, cardinalities and forward progress.

The principal SSSP corpus uses seeds **2025, 17033, 45141**, graph sizes 2/4/8/16,
densities 0/10/40/100%, quarter-unit weights, self-loops and parallel edges.
Together with manual fixtures it reports 55 graphs, 386 source queries, 4,192
reconstructed paths, 6,848 bounded-contract checks, and 1,088 concrete BMSSP
transformed-label projections. Distances/reachability match both native Dijkstra
and independent Bellman-Ford exactly. Additional tests cover 2,048-vertex chain
and hub graphs, full signed 64-bit vertex limits, maximum edge ID, concurrent
queries, checked overflow and invalid inputs.

An independent integer simple-path enumeration exhausts all 729 three-vertex
loop-free directed graphs whose six possible edges are absent, zero or one:
2,187 source queries and 6,561 reconstructed targets. A separate numerical test
uses seed **250417033**, 2,000 six-vertex graphs, 6,000 source queries and 36,000
reconstructed targets, with weights 0, .1, .2, .3, 1, 1e-16, 1e16 and 1e16+2.
Binary64 distances agree exactly with reference Dijkstra. No epsilon is used.
These counts describe separate corpora rather than one combined graph count.

Failures during implementation were retained and corrected:

1. `component_tests.log`: randomized frontier operations exposed removal of the
   terminal B fence (`frontier fence not found`). Insert now recreates the terminal
   block when needed; `terminal_fence_recreation` permanently covers this case.
2. `fence_fix_tests.log` / `trace_tests.log`: seed 2025, n=8, m=74, source
   5000000000 exposed a backward recursive boundary. `stale_probe_tests.log`
   identified an already-completed parent record (key 95). Parent Delete after
   child completion retires it before outgoing reinsertion. The same unchanged
   seeded fixture now passes all independent contracts; 3,273 retirements occur
   across the principal corpus. The explicit representation refinement is
   documented in bmssp_2025.md.

There are no unresolved observed correctness mismatches. Empirical coverage does
not prove correctness on every graph or the exact-real research theorem.

## Bounded exploratory measurements

Command: `/usr/bin/time -l /private/tmp/bmssp-task5.cXBqr9/release/bmssp_benchmark`.
Release configuration, same machine/compiler above, seed 2025. Each original graph
is constructed once; degree reduction is timed once and retained. Sources are 0,
n/2 and n-1, each with one untimed BMSSP warmup and three measured repeats.
Dijkstra runs immediately after each BMSSP query on the identical original graph;
every timed result is checked for exact distance agreement. No expensive trace or
frontier validation is enabled. Twenty-seven rows are retained in the CSV. The
small samples and unequal warmup order cannot support broad comparative claims.

Source 0 observations (query columns are medians of three repeats; milliseconds):

| Family | Original n/m | Transformed n/m | Preprocess | BMSSP query | Dijkstra query |
|---|---|---|---:|---:|---:|
| Chain | 256/255 | 510/763 | 0.195208 | 0.719250 | 0.004750 |
| Hub | 256/255 | 510/510 | 0.097000 | 1.110709 | 0.020250 |
| Sparse | 96/436 | 872/1308 | 0.242291 | 2.660542 | 0.013375 |

All use k=2, t=4, root level=3 and actual maximum depth=3. Deterministic source-0
work counts demonstrate execution:

| Family | Recursive calls | Pivot scans / selected | Pulls | Splits | Retired keys | Relaxations | Completed transformed |
|---|---:|---|---:|---:|---:|---:|---:|
| Chain | 273 | 51 / 18 | 272 | 0 | 0 | 3,611 | 510 |
| Hub | 173 | 38 / 11 | 172 | 76 | 0 | 2,316 | 510 |
| Sparse | 551 | 1,098 / 466 | 550 | 568 | 69 | 6,750 | 865 |

Peak process RSS was 3,604,480 bytes, peak footprint 3,096,912 bytes, measured by
macOS time across the complete small comparison process (not a per-query allocator
measurement). Command wall time was 0.633233 s. BMSSP was slower on these fixtures.
No speedup or O(m log^(2/3)n) implementation bound is claimed.

## Existing application regression

From the unchanged `backend` directory, using the pinned Task 3 environment:

```sh
PYTHONDONTWRITEBYTECODE=1 \
GRAPH_CACHE_DIR=/private/tmp/bmssp-task5.cXBqr9/cache \
MPLCONFIGDIR=/private/tmp/bmssp-task5.cXBqr9/mpl \
PYTHONPATH=/private/tmp/bmssp-task3.reiD2h/guard:/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer/backend \
/private/tmp/bmssp-task3.reiD2h/venv/bin/python -m pytest tests/ -vv --tb=long -p no:cacheprovider --junitxml=/private/tmp/bmssp-task5.cXBqr9/backend-regression.xml
```

Result: **34 passed**, 16 pre-existing dependency warnings, pytest runtime 132.28 s.
The retained `guard/sitecustomize.py` blocks outbound sockets; graph and Matplotlib
caches are outside the checkout. No OSM download was permitted. Backend, frontend,
legacy extension, VRP, existing benchmarks and workflows are unchanged. The native
CLI still defaults to reference Dijkstra. No production endpoint invokes BMSSP.
