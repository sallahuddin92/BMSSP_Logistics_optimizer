# Exploratory native BMSSP optimization E1

**EXPLORATORY_BMSSP_PERFORMANCE. Nonconfirmatory.** Task15 stays blocked. This directory does not execute its protocol, production adapters, approval mechanisms or statistical estimands. No Valhalla or StarNAV claim is made.

See PLAN.md for the measurement design and HYPOTHESIS.md for the single selected C++ hypothesis. `native_driver.cpp` is a native-only driver with separate correctness, ordinary latency, enabled-profile and sampling-spin modes. Its `check` mode compares every binary64 distance bit to native reference Dijkstra, saves both vectors and validates directed reconstructed paths to every vertex, including unreachable vertices. Ordinary timings include solver return and workspace cleanup, exclude graph preparation, returned-result destruction, fingerprints and output. The same boundaries apply to Dijkstra. Profiled and allocation-intercepted executables never supply primary latency samples.

The external evidence root used for E1 is recorded in RESULTS.md. Preserve it: it contains baseline source archive, builds, exact CMake caches/compile/link records, fresh SDK inventory, input/source identities, all process logs, samples, vectors and failed setup attempts. No dependency installation is needed. The orchestrator uses Python's standard library; the recorded run used the existing Python3.11 interpreter. No pybind11 is required.

## Reproducing the experiment

Use a **fresh external directory**, export baseline commit `5e8b11b4db8a0883969e7fe1405b048f419d7f07` into `baseline-source`, and retain its tar SHA. `input-identities.json` contains only the three archived input records and host identification. Generate `.sources` files with `original_position external_vertex_id`, all100 for correctness and first10 for performance. The experiment uses the archived native exports directly; `experiment.py verify-graphs` independently compares directed endpoint/binary64-weight multisets to GraphML and preserves parallel multiplicity. The retained `run_baseline.py`, `run_candidate_checks.py`, `run_controlled.py` and sampling script document the exact executed sequence and command arguments.

For both source trees, configure with the same absolute compiler and process-local developer/SDK selection:

```sh
export DEVELOPER_DIR=/Library/Developer/CommandLineTools
export SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk
cmake -S "$E1_SOURCE" -B "$E1_BUILD" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=/Library/Developer/CommandLineTools/usr/bin/clang++ \
  -DCMAKE_OSX_SYSROOT="$SDKROOT" -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=26.0 -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DBMSSP_PYTHON=OFF -DBMSSP_SANITIZERS=OFF -DBMSSP_ALLOCATION_PROBE=OFF \
  -DCMAKE_PROJECT_bmssp_native_foundation_INCLUDE="$E1_REPO/research/exploratory_e1/add_target.cmake"
cmake --build "$E1_BUILD" --parallel 4
ctest --test-dir "$E1_BUILD" --output-on-failure -j 1
```

The library's actual compile commands use strict `-std=c++20`. The external project hook creates the measurement target before the root CMake extensions setting, so the driver's actual recorded flag is `-std=gnu++20`, identically for both builds; no GNU language extension is used. All actual flags are preserved rather than silently relabeled.

Run the all100-position check per graph with `e1_native check GRAPH POSITIONS bmssp 1 0 OUTPUT.bin`. Native pilot/profile commands and their individual output files are in the retained invocation journals. Run `sample` only against a separate `spin` diagnostic process. `attribution.py EVIDENCE` interprets its stored call tree, checks conservation of sample counts and separates inclusive from exclusive counts.

`allocation.cpp` defines executable-local ordinary/aligned C++ new/delete interception, compiled against each variant's own native library. It records requested bytes, not allocator overhead, C malloc, OS allocation or query-only RSS. The executable is entirely separate from `e1_native` and preserves oracle checks. Exact compiler argv is in the invocation journal.

Memory safety uses a separate Debug build with BMSSP_SANITIZERS=ON and the same native suite. Runtime settings: ASAN_OPTIONS=detect_leaks=0; UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1. This checks address/undefined behavior, not LeakSanitizer coverage. The controlled run follows successful correctness/sanitizer gates and a recorded20-second idle period; no builds, tests, samplers or allocation probes overlap primary latency processes.

From this directory, using the recorded Python interpreter:

```sh
python -B test_analysis.py
python -B experiment.py verify-graphs --evidence "$E1_EVIDENCE"
python -B build_manifest.py "$E1_EVIDENCE"
python -B experiment.py measure --evidence "$E1_EVIDENCE"
python -B experiment.py analyze --evidence "$E1_EVIDENCE"
```

`measure` creates ten blocks with four build/algorithm conditions, alternating forward/reverse condition order and rotating graphs/source positions. Each fresh process executes one warmup then five measured repetitions per source. It refuses to overwrite individual process logs and stops on process failure. Keep all observations and anomalies. `analyze` requires all6000 samples, checks per-source counts, fingerprints, BMSSP work-counter identity and disabled profile counters, then reports nearest-rank quantiles, paired ratios and deterministic block-bootstrap sensitivity. Only ten blocks and one host are available; high tails and bootstrap intervals are exploratory descriptions, not confirmatory guarantees.

The evidence receipt and source hashes identify this experimental implementation. The baseline/candidate driver sources and flags are identical. The tested singleton-insert change is retained as candidate-engine.diff; active engine source was restored because the performance decision is INCONCLUSIVE. Existing API, diagnostics, algorithm ordering and tests remain unchanged. Do not rebuild retained candidate artifacts against the restored checkout: reproduce them from the retained candidate source snapshot or apply the saved patch to a fresh baseline copy. The exploratory branch is not a production promotion.
