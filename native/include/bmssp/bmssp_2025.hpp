// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/bounded_frontier.hpp"
#include "bmssp/degree_reduction.hpp"
#include "bmssp/detail/dense_marks.hpp"
#include "bmssp/profile.hpp"
#include <functional>
namespace bmssp {
struct BMSSPDiagnostics {
    std::size_t recursive_calls = 0, base_calls = 0, max_recursion_depth = 0, pivot_calls = 0,
                pivot_edge_scans = 0;
    std::size_t pivots_selected = 0, pivot_early_returns = 0, relaxed_edges = 0,
                equality_relaxations = 0, label_updates = 0;
    std::size_t completed_vertex_events = 0, completed_vertices = 0,
                original_reachable_vertices = 0, label_nodes_created = 0;
    std::size_t transformed_vertices = 0, transformed_edges = 0, k = 0, t = 0, root_level = 0;
    double preprocessing_seconds = 0, query_seconds = 0;
    FrontierCounters frontier;
    QueryProfile profile;
};
struct BoundedResult {
    SymbolicLabel bound;
    std::vector<VertexIndex> completed;
};
struct PivotResult {
    std::vector<VertexIndex> pivots, visited;
    bool early = false;
};
struct BoundedTrace {
    std::size_t level, depth;
    SymbolicLabel input_bound;
    std::vector<VertexIndex> frontier;
    std::vector<SymbolicLabel> before, after;
    BoundedResult result;
};
struct BMSSPOptions {
    bool validate_frontier_operations = false;
    std::function<void(const BoundedTrace &)> observer;
    bool profile = false; // Append fields to preserve existing aggregate initializers.
};
class BMSSPWorkspace {
  public:
    BMSSPWorkspace(Graph graph, ExternalVertexId source, std::size_t k, std::size_t t,
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

  private:
    Graph graph_;
    std::size_t k_, t_, depth_ = 0;
    BMSSPOptions options_;
    std::vector<SymbolicLabel> labels_;
    BMSSPDiagnostics diagnostics_;
    mutable detail::DenseMarks<> validation_seen_;
    void validate_frontier(const SymbolicLabel &bound,
                           const std::vector<VertexIndex> &frontier) const;
    [[nodiscard]] std::size_t power(std::size_t exponent) const;
    [[nodiscard]] std::size_t exponent(std::size_t level) const;
};
struct BMSSPResult {
    ShortestPathResult shortest_paths;
    BMSSPDiagnostics diagnostics;
};
class BMSSP2025Engine {
  public:
    explicit BMSSP2025Engine(const Graph &graph);
    [[nodiscard]] BMSSPResult solve(ExternalVertexId source, BMSSPOptions options = {}) const;
    [[nodiscard]] const DegreeReduction &reduction() const noexcept {
        return reduction_;
    }

  private:
    double preprocessing_seconds_ = 0;
    DegreeReduction reduction_;
};
[[nodiscard]] BMSSPResult bmssp_2025(const Graph &graph, ExternalVertexId source,
                                     BMSSPOptions options = {});
} // namespace bmssp
