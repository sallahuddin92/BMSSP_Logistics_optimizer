#!/usr/bin/env python3
"""Create an opt-in instrumented BaseCase executable; never a latency binary.
The source archive and matching baseline library are read-only inputs.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--library", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--compiler", required=True)
a = p.parse_args()
# Reject mismatched source/library layouts before linking private workspace data.
cache = a.library.parent / "CMakeCache.txt"
entry = "CMAKE_HOME_DIRECTORY:INTERNAL=" + str(a.source.resolve())
if entry not in cache.read_text().splitlines():
    p.error("Library must come from a CMake build of the supplied source tree")
a.output.mkdir(parents=True, exist_ok=False)
repo = Path(__file__).resolve().parents[1]
source = a.source / "native/src/bmssp_bounded.cpp"
s = source.read_text()
start = s.index("BoundedResult BMSSPWorkspace::base_case(")
end = s.index("PivotResult BMSSPWorkspace::find_pivots(", start)
body = s[start:end]
body = body.replace(
    "    ProfileScope scope(ProfilePart::base);",
    "    basecase_measurement::Call measurement;\n    ProfileScope scope(ProfilePart::base);",
    1,
)
old = (
    "    std::priority_queue<Item, std::vector<Item>, decltype(greater)> heap(greater);"
)
if old in body:
    body = body.replace(
        old,
        "    basecase_measurement::CapacityQueue<Item, std::vector<Item>, decltype(greater)> raw_heap(greater);\n    basecase_measurement::HeapView heap(raw_heap);",
    )
else:
    assert "auto &heap = base_heap_;" in body
    body = body.replace(
        "auto &heap = base_heap_;", "basecase_measurement::HeapView heap(base_heap_);"
    )
old = "    std::unordered_set<VertexIndex> extracted;"
if old in body:
    body = body.replace(
        old,
        "    std::unordered_set<VertexIndex> raw_extracted;\n    basecase_measurement::MembershipView extracted(raw_extracted);",
    )
else:
    assert "auto &extracted = base_extracted_;" in body
    begin = "    if (base_extracted_.size() != graph_.vertex_count())"
    assert begin in body
    body = body.replace(
        begin,
        "    const auto membership_before = basecase_measurement::snapshot();\n"
        + begin,
    )
    body = body.replace(
        "    base_extracted_.begin();",
        "    base_extracted_.begin();\n    basecase_measurement::membership_prepared(membership_before);",
    )
    body = body.replace(
        "auto &extracted = base_extracted_;",
        "basecase_measurement::MembershipView extracted(base_extracted_);",
    )
reserve = "    completed.reserve(std::min(graph_.vertex_count(), std::min(k_, std::size_t{7}) + 1));"
if reserve in body:
    body = body.replace(
        reserve,
        "    const auto completed_before = basecase_measurement::snapshot();\n"
        + reserve
        + "\n    basecase_measurement::completed_prepared(completed_before);",
    )
body = body.replace(
    "    while (!heap.empty()", "    measurement.ready();\n    while (!heap.empty()", 1
)
body = body.replace(
    "completed.push_back(item.key);",
    "basecase_measurement::completed_push(completed,item.key);",
)
old = """        if (!(item.value == labels_[item.key]) || !extracted.insert(item.key).second)
            continue;"""
new = """        if (!(item.value == labels_[item.key])) { if(basecase_measurement::active)++basecase_measurement::active->stale; continue; }
        if (!extracted.insert(item.key).second) { if(basecase_measurement::active)++basecase_measurement::active->duplicate; continue; }"""
if old in body:
    body = body.replace(old, new)
else:
    old = old.replace(".second", "")
    assert old in body
    body = body.replace(old, new.replace(".second", ""))
old = """    if (completed.size() <= k_)
        return {bound, std::move(completed)};"""
assert old in body
body = body.replace(
    old,
    """    if (completed.size() <= k_) {
        measurement.returned(false,completed.size());
        return {bound, std::move(completed)};
    }""",
)
body = body.replace(
    "    return {boundary, std::move(completed)};",
    "    measurement.returned(true,completed.size());\n    return {boundary, std::move(completed)};",
)
s = '#include "basecase_measurement.hpp"\n' + s[:start] + body + s[end:]
(a.output / "bmssp_bounded.cpp").write_text(s)
cmake = f"""cmake_minimum_required(VERSION 3.20)
project(basecase_probe LANGUAGES CXX)
add_executable(basecase_probe "{repo}/native/tools/basecase_probe.cpp" bmssp_bounded.cpp)
target_compile_features(basecase_probe PRIVATE cxx_std_20)
target_include_directories(basecase_probe PRIVATE "{a.source.resolve()}/native/include" "{repo}/native/test_support")
target_link_libraries(basecase_probe PRIVATE "{a.library.resolve()}")
"""
(a.output / "CMakeLists.txt").write_text(cmake)
(a.output / "source-hashes.json").write_text(
    json.dumps(
        {
            "input": hashlib.sha256(source.read_bytes()).hexdigest(),
            "instrumented": hashlib.sha256(s.encode()).hexdigest(),
            "library": hashlib.sha256(a.library.read_bytes()).hexdigest(),
            "headers": {
                str(p.relative_to(a.source)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((a.source / "native/include").rglob("*.hpp"))
            },
            "driver": hashlib.sha256(
                (repo / "native/tools/basecase_probe.cpp").read_bytes()
            ).hexdigest(),
            "measurement": hashlib.sha256(
                (repo / "native/test_support/basecase_measurement.hpp").read_bytes()
            ).hexdigest(),
        },
        indent=2,
    )
)
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
