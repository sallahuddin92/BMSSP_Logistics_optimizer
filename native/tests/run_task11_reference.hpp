// SPDX-License-Identifier: Apache-2.0
#pragma once
// Frozen workspace/state wrapper for Task 11 recursive differential execution.
#include "bmssp/bmssp_2025.hpp"
namespace task11_reference {
using namespace bmssp;
class FrozenWorkspace {
  public:
    FrozenWorkspace(Graph graph, ExternalVertexId source, std::size_t k, std::size_t t,
                    BMSSPOptions options = {});
    void reset(ExternalVertexId source);
    [[nodiscard]] const Graph &graph() const noexcept {
        return graph_;
    }
    [[nodiscard]] const std::vector<SymbolicLabel> &labels() const noexcept {
        return labels_;
    }
    [[nodiscard]] BMSSPDiagnostics &diagnostics() noexcept {
        return diagnostics_;
    }
    // A valid relaxation includes equality. A finite bound restricts updates strictly below it.
    bool relax(const Edge &edge, const SymbolicLabel &bound = SymbolicLabel{});
    [[nodiscard]] BoundedResult base_case(const SymbolicLabel &bound,
                                          const std::vector<VertexIndex> &frontier);
    [[nodiscard]] PivotResult find_pivots(const SymbolicLabel &bound,
                                          const std::vector<VertexIndex> &frontier);
    [[nodiscard]] BoundedResult run(std::size_t level, const SymbolicLabel &bound,
                                    const std::vector<VertexIndex> &frontier);

    void seed_labels(const std::vector<SymbolicLabel> &labels) {
        labels_ = labels;
    }

  private:
    Graph graph_;
    std::size_t k_, t_, depth_ = 0;
    BMSSPOptions options_;
    std::vector<SymbolicLabel> labels_;
    BMSSPDiagnostics diagnostics_;
    mutable detail::DenseMarks<> validation_seen_;
    detail::BaseCaseHeap base_heap_;
    // Separate from validation scratch; only the leaf BaseCase owns this epoch.
    detail::DenseMarks<> base_extracted_;
    detail::PivotScratch<> pivot_scratch_;
    void validate_frontier(const SymbolicLabel &bound,
                           const std::vector<VertexIndex> &frontier) const;
    [[nodiscard]] std::size_t power(std::size_t exponent) const;
    [[nodiscard]] std::size_t exponent(std::size_t level) const;
};
} // namespace task11_reference
