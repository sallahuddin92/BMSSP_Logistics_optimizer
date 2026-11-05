// SPDX-License-Identifier: Apache-2.0
#pragma once
// CMake-generated test translation units only; never production hooks.
#include "bmssp/bmssp_2025.hpp"
#include <functional>
namespace run_test {
struct State {
    std::size_t level, depth, phase;
    std::vector<bmssp::VertexIndex> complete, members;
    bmssp::SymbolicLabel boundary;
};
inline thread_local std::function<void(const State &)> observer;
inline thread_local std::function<void(std::size_t, const std::vector<bmssp::VertexIndex> &,
                                       bmssp::FrontierPull &)>
    pull_fault;
inline thread_local std::function<void(std::size_t, const std::vector<bmssp::VertexIndex> &,
                                       bmssp::BoundedResult &)>
    child_fault;
template <class Workspace, class Set>
void state(Workspace &w, std::size_t level, std::size_t depth, std::size_t phase,
           const std::vector<bmssp::VertexIndex> &complete, const Set &set,
           const bmssp::SymbolicLabel &boundary) {
    if (!observer)
        return;
    State event{level, depth, phase, complete, {}, boundary};
    for (bmssp::VertexIndex v = 0; v < w.graph().vertex_count(); ++v)
        if (set.contains(v))
            event.members.push_back(v);
    observer(event);
}
inline void pulled(std::size_t depth, const std::vector<bmssp::VertexIndex> &complete,
                   bmssp::FrontierPull &value) {
    if (pull_fault)
        pull_fault(depth, complete, value);
}
inline void child(std::size_t depth, const std::vector<bmssp::VertexIndex> &complete,
                  bmssp::BoundedResult &value) {
    if (child_fault)
        child_fault(depth, complete, value);
}
} // namespace run_test
