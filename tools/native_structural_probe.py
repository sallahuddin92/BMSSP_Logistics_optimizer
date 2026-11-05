#!/usr/bin/env python3
"""Generate an explicitly instrumented baseline probe, outside the source archive.

Only for counts/diagnosis, never latency. Original source and binary stay intact.
Requires pristine 698c1495 native source and its matching static library.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--library", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--compiler", required=True)
a = p.parse_args()
# Refuse mixed private C++ layouts: the generated objects must match the
# baseline archive's headers and source, not the working candidate.
repository = Path(__file__).resolve().parents[1]
commit = "698c14951399aca25a2409c8d1e26532c9d26587"
entries = subprocess.check_output(
    ["git", "-C", str(repository), "ls-tree", "-r", "-z", commit, "native"]
).split(b"\0")
for entry in entries:
    if not entry:
        continue
    header, relative = entry.split(b"\t", 1)
    relative = relative.decode()
    if not relative.endswith((".cpp", ".hpp")):
        continue
    data = (a.source / relative).read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if blob != header.decode().split()[2]:
        raise ValueError(f"Source does not match baseline {commit}: {relative}")
a.output.mkdir(parents=True, exist_ok=False)
original = a.source / "native/src/symbolic_label.cpp"
s = original.read_text()
prefix = """namespace {
thread_local std::array<std::size_t,7> comparison_stats{};
thread_local bool count_comparisons=false;
}
extern "C" void comparison_probe_begin() { comparison_stats={}; count_comparisons=true; }
extern "C" const std::size_t *comparison_probe_end() { count_comparisons=false; return comparison_stats.data(); }
"""
s = s.replace("namespace bmssp {", prefix + "namespace bmssp {", 1)
s = s.replace(
    "    ProfileScope scope(ProfilePart::comparison);",
    "    ProfileScope scope(ProfilePart::comparison);\n    if (count_comparisons) ++comparison_stats[0];",
)
s = s.replace(
    """    if (a.node_ == b.node_)
        return 0;""",
    """    if (a.node_ == b.node_) {
        if (count_comparisons) ++comparison_stats[1];
        return 0;
    }""",
)
s = s.replace(
    "    if (const auto c = scalar(a.node_->hops, b.node_->hops); c != 0)",
    "    if (count_comparisons) ++comparison_stats[2];\n    if (const auto c = scalar(a.node_->hops, b.node_->hops); c != 0)",
)
s = s.replace(
    "    auto x = a.node_, y = b.node_;",
    "    if (count_comparisons) ++comparison_stats[3];\n    std::size_t depth=0;\n    auto x = a.node_, y = b.node_;",
)
needle = "    while (x && y && x != y) {"
assert s.count(needle) == 2
first = (
    needle
    + "\n        if (count_comparisons) { ++comparison_stats[4]; if (++depth>comparison_stats[6]) comparison_stats[6]=depth; }"
)
second = (
    needle
    + "\n        if (count_comparisons) { ++comparison_stats[5]; if (++depth>comparison_stats[6]) comparison_stats[6]=depth; }"
)
s = s.replace(needle, first, 1)
# Replace last original loop, leaving the first instrumented one intact.
pos = s.rindex(needle)
s = s[:pos] + s[pos:].replace(needle, second, 1)
s = s.replace("    // Parallel edges", "    depth=0;\n    // Parallel edges")
(a.output / "symbolic_label.cpp").write_text(s)
bounded = a.source / "native/src/bmssp_bounded.cpp"
b = bounded.read_text()
prefix = """extern "C" void validation_probe_enter();
extern "C" void validation_probe_exit();
struct ValidationProbeScope {
    ValidationProbeScope() { validation_probe_enter(); }
    ~ValidationProbeScope() { validation_probe_exit(); }
};
"""
b = b.replace("namespace bmssp {", prefix + "namespace bmssp {", 1)
needle = "const std::vector<VertexIndex> &frontier) const {"
assert b.count(needle) == 1
b = b.replace(needle, needle + "\n    ValidationProbeScope probe;", 1)
(a.output / "bmssp_bounded.cpp").write_text(b)
repo = Path(__file__).resolve().parents[1]
cmake = f"""cmake_minimum_required(VERSION 3.20)
project(native_structural_probe LANGUAGES CXX)
add_executable(structural_probe "{repo}/native/tools/allocation_probe.cpp" symbolic_label.cpp bmssp_bounded.cpp)
target_compile_features(structural_probe PRIVATE cxx_std_20)
target_compile_definitions(structural_probe PRIVATE BMSSP_STRUCTURAL_PROBE)
target_include_directories(structural_probe PRIVATE "{a.source.resolve()}/native/include")
target_link_libraries(structural_probe PRIVATE "{a.library.resolve()}")
"""
(a.output / "CMakeLists.txt").write_text(cmake)
manifest = {
    "baseline_commit": "698c14951399aca25a2409c8d1e26532c9d26587",
    "original_sources": {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [original, bounded]
    },
    "generated_sources": {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in a.output.glob("*.cpp")
    },
    "counters": [
        "calls",
        "same_node",
        "distance_ties_excluding_same_node",
        "hop_ties",
        "vertex_chain_steps",
        "edge_chain_steps",
        "max_chain_steps",
    ],
}
(a.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
subprocess.run(
    [
        "cmake",
        "-S",
        str(a.output),
        "-B",
        str(a.output / "build"),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_CXX_COMPILER=" + a.compiler,
    ],
    check=True,
)
subprocess.run(["cmake", "--build", str(a.output / "build"), "-j", "3"], check=True)
