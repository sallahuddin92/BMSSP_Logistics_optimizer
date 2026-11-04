# Task 4 validation evidence — 2026-11-04

Status: PASS for the standalone native foundation. Genuine BMSSP is not implemented.
Baseline: `94f54b5206b46541dc12f5c7d8cb7fa019e4f877`, branch
`codex/genuine-bmssp-engine`. Existing backend/frontend/benchmark/workflow files
were unchanged. No new package installation or geographic download was needed.

## Environment and exact commands

macOS 26.5.1 (25F80), Apple Silicon arm64. CMake 4.3.3.
Debug/Release: Apple Clang 17.0.0 (clang-1700.6.3.2), `/usr/bin/c++`.
ASan/UBSan: installed CLT Apple Clang 21.0.0 (clang-2100.1.1.101).
No compiler was installed or system compiler selection changed.

Commands ran from `/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer`:

```sh
cmake --preset debug -B /private/tmp/bmssp-task4.EyJSzW/build/debug
cmake --build /private/tmp/bmssp-task4.EyJSzW/build/debug --parallel 4
ctest --test-dir /private/tmp/bmssp-task4.EyJSzW/build/debug -V
cmake --preset release -B /private/tmp/bmssp-task4.EyJSzW/build/release
cmake --build /private/tmp/bmssp-task4.EyJSzW/build/release --parallel 4
ctest --test-dir /private/tmp/bmssp-task4.EyJSzW/build/release -V
cmake --preset sanitizers -B /private/tmp/bmssp-task4.EyJSzW/build/sanitizers-clt \
  -DCMAKE_CXX_COMPILER=/Library/Developer/CommandLineTools/usr/bin/clang++
cmake --build /private/tmp/bmssp-task4.EyJSzW/build/sanitizers-clt --parallel 4
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  ctest --test-dir /private/tmp/bmssp-task4.EyJSzW/build/sanitizers-clt -V
```

Actual compile flags include `-std=c++20 -Wall -Wextra -Wpedantic -Wconversion
-Wsign-conversion -Wshadow -Werror`; Debug uses `-g`, Release `-O3 -DNDEBUG`.
Sanitizers add `-fsanitize=address,undefined -fno-omit-frame-pointer` and matching
link flags. CMake selected arm64 and the local SDK automatically. Complete compile
commands and command/cwd/exit/duration metadata are retained outside the repository
in `/private/tmp/bmssp-task4.EyJSzW/` with `EVIDENCE.md` as index. These temporary
artifacts may be removed by the OS; portable reproduction is in `native_build.md`.

| Configuration | Configure seconds | Full-source rebuild seconds | Final CLI rebuild seconds | Final CTest seconds | Result |
|---|---:|---:|---:|---:|---|
| Debug | 2.273 | 6.365 | 0.566 | 4.054 | 5/5 passed, exit 0 |
| Release | 1.853 | 5.980 | 0.699 | 0.775 | 5/5 passed, exit 0 |
| ASan/UBSan, Clang 21 | 0.592 | 5.939 | 1.190 | 21.168 | 5/5 passed, exit 0 |

Full-source rebuild and final CLI parser rebuild are separate measured invocations,
not a single clean-build timing. These are verification timings, not algorithm
benchmarks. Formatting was checked with installed clang-format 21.

## Correctness results

Each configuration executed 17 graph, 16 shortest-path, 14 reconstruction, and
3 oracle cases (50 named cases across four executables), plus CTest CLI smoke.
Checks are active in Release. All passed. No sanitizer errors were reported by
the completed Clang 21 ASan/UBSan run. Leak detection was not validated.

Independent raw-edge Bellman-Ford verification: 74 graphs, 1,400 source queries,
63,562 source/target path checks, zero mismatches. Seeds: 2025, 17033, 45141.
Random sizes: 1,2,5,12,32,64; densities: 0%,5%,25%,100%, with parallel edges.
Maximum randomized fixture: 64 vertices, 4,505 edges. A separate 10,000-vertex,
9,999-edge chain passed. Quarter-unit random sums are exact at these sizes;
reachability, distances and path sums were compared without tolerance.

Ten extra CLI checks passed, including large IDs, unreachable target, invalid
input, negative edge ID, usage status, and the minimum positive binary64 subnormal.
Exact stdin/stdout/exit assertions are retained in `cli_checks.py` and
`delivery_cli.log` in the external evidence directory. The demo outputs:

```text
algorithm=reference_dijkstra reachable=true distance=7
vertices 0 2 1 3
edges 11 12 13
```

`/usr/bin/time -l .../build/release/oracle_tests` observed maximum RSS 2,965,504
bytes and peak footprint 2,523,472 bytes. These are one whole-process observation
for the small oracle workload, not a memory scalability claim.

## Toolchain failure retained and resolved

Apple Clang 17 with `ASAN_OPTIONS=detect_leaks=1` aborted all five processes before
testing because leak detection is unsupported. With `detect_leaks=0`, runtime
initialization hung before main. A minimal `int main(){return 0;}` ASan executable
also timed out after eight seconds; a sampled stack showed sanitizer initialization
re-entering a malloc spin lock. This identifies a toolchain/runtime failure,
not an observed foundation algorithm defect. Audit-only hung processes were stopped.
Two overlapping retries in that older build directory were excluded from acceptance
evidence; their timeout/termination logs remain preserved. The fresh Clang 21 build
passed both the minimal probe and the complete final suite. No source workaround
or sanitizer suppression was introduced.

## Application regression

From the backend directory, reused the isolated Task 3 Python 3.11.15 environment:

```sh
PYTHONDONTWRITEBYTECODE=1 \
GRAPH_CACHE_DIR=/private/tmp/bmssp-task4.EyJSzW/cache \
MPLCONFIGDIR=/private/tmp/bmssp-task4.EyJSzW/mpl \
PYTHONPATH=/private/tmp/bmssp-task3.reiD2h/guard:/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer/backend \
/private/tmp/bmssp-task3.reiD2h/venv/bin/python -m pytest tests/ -vv --tb=long \
  -p no:cacheprovider --junitxml=/private/tmp/bmssp-task4.EyJSzW/backend-regression.xml
```

Result: 34 passed, zero failed/skipped/errors, 16 pre-existing deprecation warnings.
Pytest reported 135.45 seconds; measured command duration 136.971 seconds, exit 0.
The guard blocked outbound socket connections; no existing expectations/mocks
were changed. Pre-existing logistics/native-integration defects from Task 3 remain
outside this task and are not certified correct by the passing regression suite.

Linux build configuration is provided but Linux execution was not performed.
No comparative speedup, real-road result, Python binding, deployment, or genuine
BMSSP correctness claim follows from this foundation validation.
