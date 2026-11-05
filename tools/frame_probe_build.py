#!/usr/bin/env python3
"""Isolated per-recursive-frame allocation and membership profiling, never latency."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
for name in ["source", "library", "output"]:
    p.add_argument("--" + name, type=Path, required=True)
p.add_argument("--compiler", required=True)
a = p.parse_args()
home = next(
    (
        s.partition("=")[2]
        for s in (a.library.parent / "CMakeCache.txt").read_text().splitlines()
        if s.startswith("CMAKE_HOME_DIRECTORY:INTERNAL=")
    ),
    None,
)
if home is None or Path(home).resolve() != a.source.resolve():
    p.error("Source/library CMake identity mismatch")
a.output.mkdir(parents=True, exist_ok=False)
repo = Path(__file__).resolve().parents[1]
source = a.source / "native/src/bmssp_bounded.cpp"
text = source.read_text()
start = text.index("BoundedResult BMSSPWorkspace::run(")
s = text[start:]


def replace(old, new):
    global s
    if s.count(old) != 1:
        raise ValueError("Unsupported run() source: " + old)
    s = s.replace(old, new)


replace(
    "    auto pivots = find_pivots(bound, frontier);",
    "    auto pivots = frame_measurement::measure(frame_measurement::Part::pivots,[&]{return find_pivots(bound,frontier);});",
)
replace(
    "    ProfileScope scope(ProfilePart::recursion);",
    "    frame_measurement::Call measurement(level,depth_,frontier.size());\n    ProfileScope scope(ProfilePart::recursion);",
)
replace(
    "        increment(diagnostics_.completed_vertex_events, result.completed.size());",
    "        measurement.returned(result.completed.size());\n        increment(diagnostics_.completed_vertex_events, result.completed.size());",
)
old = "    std::unordered_set<VertexIndex> complete_members;"
if old in s:
    replace(
        old,
        "    frame_measurement::constructed();\n    auto complete_members=frame_measurement::measure(frame_measurement::Part::membership,[]{return std::unordered_set<VertexIndex>{};});\n    measurement.ready();",
    )
else:
    old = "    auto complete_members = complete_frames_.acquire(depth_, graph_.vertex_count());"
    replace(
        old,
        "    frame_measurement::constructed();\n    auto complete_members=frame_measurement::measure(frame_measurement::Part::membership,[&]{return complete_frames_.acquire(depth_,graph_.vertex_count());});\n    frame_measurement::scratch(complete_members);\n    measurement.ready();",
    )
s = (
    s.replace(
        "complete_members.contains(e.key)",
        "frame_measurement::contains(complete_members,e.key)",
    )
    .replace(
        "complete_members.insert(u)", "frame_measurement::insert(complete_members,u)"
    )
    .replace(
        "complete_members.insert(x)", "frame_measurement::insert(complete_members,x)"
    )
)
replace(
    "            children.push_back(e.key);",
    "            frame_measurement::measure(frame_measurement::Part::children,[&]{children.push_back(e.key);});",
)
s = s.replace(
    "complete.push_back(u);",
    "frame_measurement::measure(frame_measurement::Part::owned,[&]{complete.push_back(u);});",
).replace(
    "complete.push_back(x);",
    "frame_measurement::measure(frame_measurement::Part::owned,[&]{complete.push_back(x);});",
)
s = s.replace(
    "prepend.push_back({edge.to, value});",
    "frame_measurement::measure(frame_measurement::Part::prepend,[&]{prepend.push_back({edge.to,value});});",
).replace(
    "prepend.push_back({x, labels_[x]});",
    "frame_measurement::measure(frame_measurement::Part::prepend,[&]{prepend.push_back({x,labels_[x]});});",
)
(a.output / "bmssp_bounded.cpp").write_text(
    '#include "frame_measurement.hpp"\n' + text[:start] + s
)
for name in [
    "native/tools/frame_probe.cpp",
    "native/test_support/frame_measurement.hpp",
    "native/test_support/allocation_tracking.hpp",
]:
    dst = a.output / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo / name, dst)
shutil.copy2(__file__, a.output / "builder.py")
(a.output / "original_bounded.cpp").write_text(text)
(a.output / "CMakeLists.txt").write_text(
    f"""cmake_minimum_required(VERSION 3.20)
project(frame_probe LANGUAGES CXX)
add_executable(frame_probe "{a.output.resolve()}/native/tools/frame_probe.cpp" bmssp_bounded.cpp)
target_compile_features(frame_probe PRIVATE cxx_std_20)
target_include_directories(frame_probe PRIVATE "{a.source.resolve()}/native/include" "{a.output.resolve()}/native/test_support")
target_link_libraries(frame_probe PRIVATE "{a.library.resolve()}")
"""
)
paths = [
    source,
    *sorted((a.source / "native/include").rglob("*.hpp")),
    repo / "native/tools/frame_probe.cpp",
    repo / "native/test_support/frame_measurement.hpp",
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
