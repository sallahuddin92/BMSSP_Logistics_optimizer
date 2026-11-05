// SPDX-License-Identifier: Apache-2.0
#pragma once
// Used only by the CMake-generated pivot_tests bounded translation unit.
#include "bmssp/bmssp_2025.hpp"
#include <functional>
namespace pivot_test {
struct TraceRound {
    std::vector<bmssp::VertexIndex> current, next, visited;
};
struct Event {
    bmssp::BMSSPWorkspace &workspace;
    std::size_t k;
    bmssp::SymbolicLabel bound;
    std::vector<bmssp::VertexIndex> frontier;
    std::vector<bmssp::SymbolicLabel> before;
    bmssp::BMSSPDiagnostics diagnostics;
    std::vector<TraceRound> rounds;
};
inline thread_local std::function<void(const Event &, const bmssp::PivotResult &)> observer;
class Scope {
    std::optional<Event> event_;

  public:
    Scope(bmssp::BMSSPWorkspace &w, std::size_t k, const bmssp::SymbolicLabel &bound,
          const std::vector<bmssp::VertexIndex> &frontier) {
        if (observer)
            event_.emplace(Event{w, k, bound, frontier, w.labels(), w.diagnostics(), {}});
    }
    void round(const std::vector<bmssp::VertexIndex> &current,
               const std::vector<bmssp::VertexIndex> &next,
               const std::vector<bmssp::VertexIndex> &visited) {
        if (event_)
            event_->rounds.push_back({current, next, visited});
    }
    bmssp::PivotResult finish(bmssp::PivotResult result) {
        if (event_)
            observer(*event_, result);
        return result;
    }
};
} // namespace pivot_test
