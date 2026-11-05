#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build a fully separate symbolic diagnostic engine. Never use its clocks as latency.

Copies and rebuilds every native source against the same isolated header definitions;
no instrumented/uninstrumented class definitions share an executable. Source files
are never modified. Includes optional ownership copies, mutex and arena clocks,
allocation interception, comparator classes and final current-label ancestry census.
"""
from pathlib import Path
import argparse, shutil, subprocess, json, hashlib

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--compiler", required=True)
a = p.parse_args()
repository = Path(__file__).resolve().parents[1]
source = a.source.resolve()
out = a.output.resolve()
if out.is_relative_to(source):
    p.error("Keep generated instrumentation outside the source tree")
out.mkdir(parents=True, exist_ok=False)
shutil.copytree(source / "native/include", out / "include")
for p in (out / "include").rglob("*.hpp"):
    p.chmod(0o644)
support = out / "symbolic_measurement.hpp"
shutil.copy2(repository / "native/test_support/symbolic_measurement.hpp", support)
h = out / "include/bmssp/symbolic_label.hpp"
t = h.read_text()
t = '#include "symbolic_measurement.hpp"\n' + t
t = t.replace(
    "SymbolicLabel() = default;",
    r"""SymbolicLabel(const SymbolicLabel& other):arena_(other.arena_),node_(other.node_){symbolic_measurement::count(&symbolic_measurement::Metrics::copies);}
SymbolicLabel(SymbolicLabel&& other) noexcept:arena_(std::move(other.arena_)),node_(other.node_){symbolic_measurement::count(&symbolic_measurement::Metrics::moves);}
SymbolicLabel& operator=(const SymbolicLabel& other){arena_=other.arena_;node_=other.node_;symbolic_measurement::count(&symbolic_measurement::Metrics::assigns);return *this;}
SymbolicLabel& operator=(SymbolicLabel&& other)noexcept{arena_=std::move(other.arena_);node_=other.node_;symbolic_measurement::count(&symbolic_measurement::Metrics::moves);return *this;}
~SymbolicLabel(){symbolic_measurement::count(&symbolic_measurement::Metrics::destroys);symbolic_measurement::Timer timer(symbolic_measurement::active?&symbolic_measurement::active->label_destruction_seconds:nullptr);arena_.reset();}
SymbolicLabel() = default;""",
).replace("SymbolicLabel(arena_,", "SymbolicLabel(symbolic_measurement::copy(arena_),")
h.write_text(t)
for f in (source / "native/src").glob("*.cpp"):
    t = f.read_text()
    if f.name == "symbolic_label.cpp":
        for marker in [
            "struct LabelArena {",
            "        std::lock_guard<std::mutex> lock(mutex);",
            "            used = 0;",
        ]:
            if t.count(marker) != 1:
                raise ValueError("Unsupported symbolic source: " + marker)
    if f.name == "bmssp_bounded.cpp":
        for marker in [
            "    increment(diagnostics_.relaxed_edges);",
            "    if (c > 0)\n        return false;",
            "    if (c < 0) {",
            "        increment(diagnostics_.equality_relaxations);",
        ]:
            if t.count(marker) != 1:
                raise ValueError("Unsupported relaxation source: " + marker)
        if (
            sum(
                t.count(marker)
                for marker in [
                    "    if (!(candidate < bound))\n        return false;",
                    "    if (SymbolicLabel::compare_nodes(&candidate, bound.node()) >= 0)\n        return false;",
                ]
            )
            != 1
        ):
            raise ValueError("Unsupported bound rejection source")
    if f.name == "symbolic_label.cpp":
        start = (
            t.index("int compare(")
            if "int SymbolicLabel::compare_nodes(" not in t
            else t.index("int SymbolicLabel::compare_nodes(")
        )
        # Replace only the comparator body, preserving any wrapper after it.
        brace = t.index("{", start)
        depth = 1
        end = brace + 1
        while depth:
            depth += (t[end] == "{") - (t[end] == "}")
            end += 1
        args = "a.node_,b.node_" if t[start:].startswith("int compare(") else "a,b"
        t = (
            t[:brace]
            + "{ ProfileScope scope(ProfilePart::comparison); return symbolic_measurement::compare("
            + args
            + "); }"
            + t[end:]
        )
        t = t.replace(
            "struct LabelArena {",
            "struct LabelArena {\n~LabelArena(){symbolic_measurement::Timer timer(symbolic_measurement::active?&symbolic_measurement::active->teardown_seconds:nullptr);blocks.clear();}",
        )
        t = t.replace(
            "        std::lock_guard<std::mutex> lock(mutex);",
            """        symbolic_measurement::Timer allocation_timer(symbolic_measurement::active?&symbolic_measurement::active->allocation_seconds:nullptr);
        symbolic_measurement::count(&symbolic_measurement::Metrics::allocations);
        const auto lock_start=symbolic_measurement::active?symbolic_measurement::Clock::now():symbolic_measurement::Clock::time_point{};
        std::unique_lock<std::mutex> lock(mutex,std::defer_lock);
        symbolic_measurement::count(&symbolic_measurement::Metrics::locks);
        if(!lock.try_lock()){symbolic_measurement::count(&symbolic_measurement::Metrics::contended);lock.lock();}
        if(symbolic_measurement::active)symbolic_measurement::active->lock_seconds+=std::chrono::duration<double>(symbolic_measurement::Clock::now()-lock_start).count();""",
        )
        t = t.replace(
            "            used = 0;",
            """            used = 0;
            if(symbolic_measurement::active){++symbolic_measurement::active->slabs;symbolic_measurement::active->capacity+=next;}""",
        )
        t = t.replace(
            "SymbolicLabel(arena_,", "SymbolicLabel(symbolic_measurement::copy(arena_),"
        )
    if f.name == "bmssp_bounded.cpp":
        t = t.replace(
            "    increment(diagnostics_.relaxed_edges);",
            "    symbolic_measurement::count(&symbolic_measurement::Metrics::attempts);\n    increment(diagnostics_.relaxed_edges);",
        )
        t = t.replace(
            "    if (SymbolicLabel::compare_nodes(&candidate, bound.node()) >= 0)\n        return false;",
            "    if (SymbolicLabel::compare_nodes(&candidate, bound.node()) >= 0){symbolic_measurement::count(&symbolic_measurement::Metrics::bounded);symbolic_measurement::count(&symbolic_measurement::Metrics::rejected);return false;}",
        )
        t = t.replace(
            "    if (!(candidate < bound))\n        return false;",
            "    if (!(candidate < bound)){symbolic_measurement::count(&symbolic_measurement::Metrics::bounded);symbolic_measurement::count(&symbolic_measurement::Metrics::rejected);return false;}",
        )
        t = t.replace(
            "    if (c > 0)\n        return false;",
            "    if (c > 0){symbolic_measurement::count(&symbolic_measurement::Metrics::rejected);return false;}",
        )
        t = t.replace(
            "    if (c < 0) {",
            "    if (c < 0) {\n        symbolic_measurement::count(&symbolic_measurement::Metrics::strict);",
        )
        t = t.replace(
            "        increment(diagnostics_.equality_relaxations);",
            "        {symbolic_measurement::count(&symbolic_measurement::Metrics::equal);increment(diagnostics_.equality_relaxations);}",
        )
    if f.name == "bmssp_2025.cpp":
        marker = "    auto diagnostics = workspace.diagnostics();"
        t = t.replace(
            marker,
            """    if(symbolic_measurement::active){
      probe_pause();
      std::unordered_set<const LabelNode*> ancestry;
      for(const auto& label:workspace.labels())if(label.finite()){++symbolic_measurement::active->current_labels;for(auto* node=label.node();node&&ancestry.insert(node).second;node=node->parent){}}
      symbolic_measurement::active->ancestry=ancestry.size();probe_resume();
    }
"""
            + marker,
        )
        # allocation interception is defined in the driver only
    (out / f.name).write_text('#include "symbolic_measurement.hpp"\n' + t)
shutil.copy2(
    source / "native/test_support/allocation_tracking.hpp",
    out / "allocation_tracking.hpp",
)
shutil.copy2(__file__, out / "builder.py")
shutil.copy2(repository / "native/tools/symbolic_probe.cpp", out / "probe.cpp")
(out / "CMakeLists.txt").write_text(
    """cmake_minimum_required(VERSION 3.20)
project(symbolic_probe LANGUAGES CXX)
add_executable(symbolic_probe probe.cpp """
    + " ".join(f.name for f in (source / "native/src").glob("*.cpp"))
    + """)
target_compile_features(symbolic_probe PRIVATE cxx_std_20)
target_include_directories(symbolic_probe PRIVATE include .)
"""
)
(out / "hashes.json").write_text(
    json.dumps(
        {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                *sorted((source / "native/src").glob("*.cpp")),
                *sorted((source / "native/include").rglob("*.hpp")),
            ]
        },
        indent=2,
    )
)
for cmd in [
    [
        "cmake",
        "-S",
        str(out),
        "-B",
        str(out / "build"),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_CXX_COMPILER=" + a.compiler,
    ],
    ["cmake", "--build", str(out / "build"), "-j4"],
]:
    subprocess.run(cmd, check=True)
