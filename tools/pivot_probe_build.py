#!/usr/bin/env python3
"""Build isolated FindPivots attribution against a matching external CMake library."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil

p = argparse.ArgumentParser(description=__doc__)
for name in ("source", "library", "output"):
    p.add_argument("--" + name, type=Path, required=True)
p.add_argument("--compiler", required=True)
a = p.parse_args()
cache = (a.library.parent / "CMakeCache.txt").read_text().splitlines()
home = next(
    (
        line.partition("=")[2]
        for line in cache
        if line.startswith("CMAKE_HOME_DIRECTORY:INTERNAL=")
    ),
    None,
)
if home is None or Path(home).resolve() != a.source.resolve():
    p.error("Source/library CMake identity mismatch")
a.output.mkdir(parents=True, exist_ok=False)
repo = Path(__file__).resolve().parents[1]
source = a.source / "native/src/bmssp_bounded.cpp"
text = source.read_text()
x = text.index("PivotResult BMSSPWorkspace::find_pivots(")
y = text.index("std::size_t BMSSPWorkspace::power(", x)
s = text[x:y]


def replace(old, new):
    global s
    if s.count(old) != 1:
        raise ValueError("Unsupported FindPivots source: " + old)
    s = s.replace(old, new)


replace(
    "    ProfileScope scope(ProfilePart::pivots);",
    "    pivot_measurement::Call measurement(frontier.size());\n    ProfileScope scope(ProfilePart::pivots);",
)
replace(
    "    std::vector<VertexIndex> visited = frontier, current = frontier;",
    """    auto visited = pivot_measurement::measure(pivot_measurement::Part::owned_results,[&]{return std::vector<VertexIndex>(frontier);});
    auto current = pivot_measurement::measure(pivot_measurement::Part::current_next,[&]{return std::vector<VertexIndex>(frontier);});""",
)
old = (
    "    std::unordered_set<VertexIndex> membership(frontier.begin(), frontier.end());"
)
if old in s:
    replace(
        old,
        "    pivot_measurement::constructed(pivot_measurement::Part::cumulative);\n    auto membership=pivot_measurement::measure(pivot_measurement::Part::cumulative,[&]{return std::unordered_set<VertexIndex>(frontier.begin(),frontier.end());});\n    pivot_measurement::seeded(frontier.size());",
    )
else:
    begin = s.index("    if (pivot_scratch_.visited.size()")
    end = s.index("    if (frontier.size()", begin)
    s = (
        s[:begin]
        + "    { pivot_measurement::Scope attribution(pivot_measurement::Part::cumulative);\n"
        + s[begin:end].replace("    auto &membership = pivot_scratch_.visited;", "")
        + "    }\n    auto &membership = pivot_scratch_.visited;\n"
        + s[end:]
    )
    # Initial frontier insertions need operation counts too.
    s = s.replace(
        "pivot_scratch_.visited.insert(v)",
        "pivot_measurement::insert(pivot_scratch_.visited,v,pivot_measurement::Part::cumulative)",
    )
replace(
    "    for (std::size_t round = 0; round < k_; ++round) {",
    "    for (std::size_t round = 0; round < k_; ++round) {\n        measurement.round(current.size());",
)
old = "        std::unordered_set<VertexIndex> next_members;"
if old in s:
    replace(
        old,
        "        pivot_measurement::constructed(pivot_measurement::Part::round);\n        auto next_members=pivot_measurement::measure(pivot_measurement::Part::round,[]{return std::unordered_set<VertexIndex>{};});",
    )
else:
    begin = s.index("        if (pivot_scratch_.round.size()")
    end = s.index("        for (const auto u : current)", begin)
    s = (
        s[:begin]
        + "        { pivot_measurement::Scope attribution(pivot_measurement::Part::round);\n"
        + s[begin:end].replace("        auto &next_members = pivot_scratch_.round;", "")
        + "        }\n        auto &next_members = pivot_scratch_.round;\n"
        + s[end:]
    )
s = s.replace(
    "next_members.insert(edge.to)",
    "pivot_measurement::insert(next_members,edge.to,pivot_measurement::Part::round)",
)
s = s.replace(
    "membership.insert(v)",
    "pivot_measurement::insert(membership,v,pivot_measurement::Part::cumulative)",
)
replace(
    "                        next.push_back(edge.to);",
    "                        pivot_measurement::measure(pivot_measurement::Part::current_next,[&]{next.push_back(edge.to);});",
)
replace(
    "                visited.push_back(v);",
    "                pivot_measurement::measure(pivot_measurement::Part::owned_results,[&]{visited.push_back(v);});",
)
replace(
    "        if (visited.size() > limit) {",
    "        measurement.sizes(next.size(),visited.size());\n        if (visited.size() > limit) {",
)
replace(
    "            return {frontier, std::move(visited), true};",
    "            measurement.returned(true,frontier.size(),visited.size());\n            return pivot_measurement::measure(pivot_measurement::Part::owned_results,[&]{return PivotResult{frontier,std::move(visited),true};});",
)
replace(
    "    for (const auto v : visited) {",
    "    for (const auto v : visited) {\n        pivot_measurement::Scope attribution(pivot_measurement::Part::forest);",
)
replace(
    "            pivots.push_back(v);",
    "            pivot_measurement::measure(pivot_measurement::Part::owned_results,[&]{pivots.push_back(v);});",
)
replace(
    "    return {std::move(pivots), std::move(visited), false};",
    "    measurement.returned(false,pivots.size(),visited.size());\n    return {std::move(pivots), std::move(visited), false};",
)
# Capture logically retained workspace storage after every return, including early ones.
if "pivot_scratch_" in s:
    # Record the logical dense array footprint after lazy initialization.
    for part in ["visited", "round"]:
        if f"pivot_scratch_.{part}.resize(" in s:
            line = f"pivot_scratch_.{part}.resize(graph_.vertex_count());"
            s = s.replace(
                line,
                line
                + f"\n    if(pivot_measurement::active) pivot_measurement::active->scratch_bytes=std::max(pivot_measurement::active->scratch_bytes,sizeof(std::uint32_t)*(pivot_scratch_.visited.size()+pivot_scratch_.round.size()));",
            )
generated = '#include "pivot_measurement.hpp"\n' + text[:x] + s + text[y:]
(a.output / "bmssp_bounded.cpp").write_text(generated)
# Freeze executable-only support so later edits cannot change a retained build.
for relative in [
    "native/tools/pivot_probe.cpp",
    "native/test_support/pivot_measurement.hpp",
    "native/test_support/allocation_tracking.hpp",
]:
    target = a.output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo / relative, target)
shutil.copy2(Path(__file__), a.output / "builder.py")
(a.output / "original_bounded.cpp").write_text(text)
(a.output / "CMakeLists.txt").write_text(
    f"""cmake_minimum_required(VERSION 3.20)
project(pivot_probe LANGUAGES CXX)
add_executable(pivot_probe "{a.output.resolve()}/native/tools/pivot_probe.cpp" bmssp_bounded.cpp)
target_compile_features(pivot_probe PRIVATE cxx_std_20)
target_include_directories(pivot_probe PRIVATE "{a.source.resolve()}/native/include" "{a.output.resolve()}/native/test_support")
target_link_libraries(pivot_probe PRIVATE "{a.library.resolve()}")
"""
)
paths = [
    source,
    *sorted((a.source / "native/include").rglob("*.hpp")),
    repo / "native/tools/pivot_probe.cpp",
    repo / "native/test_support/pivot_measurement.hpp",
    repo / "native/test_support/allocation_tracking.hpp",
    a.library,
]
(a.output / "hashes.json").write_text(
    json.dumps(
        {str(q): hashlib.sha256(q.read_bytes()).hexdigest() for q in paths}, indent=2
    )
)
for cmd in [
    [
        "cmake",
        "-S",
        str(a.output),
        "-B",
        str(a.output / "build"),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_CXX_COMPILER=" + a.compiler,
    ],
    ["cmake", "--build", str(a.output / "build"), "-j3"],
]:
    subprocess.run(cmd, check=True)
