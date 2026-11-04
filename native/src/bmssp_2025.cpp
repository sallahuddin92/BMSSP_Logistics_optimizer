// SPDX-License-Identifier: Apache-2.0
#include "bmssp/bmssp_2025.hpp"
#include <algorithm>
#include <bit>
#include <chrono>
#include <queue>
namespace bmssp {
namespace {
using Clock = std::chrono::steady_clock;
double seconds(Clock::time_point start) {
    return std::chrono::duration<double>(Clock::now() - start).count();
}
DegreeReduction timed_reduce(const Graph &graph, double &duration) {
    const auto start = Clock::now();
    auto reduced = reduce_degree(graph);
    duration = seconds(start);
    return reduced;
}
} // namespace
BMSSP2025Engine::BMSSP2025Engine(const Graph &graph)
    : reduction_(timed_reduce(graph, preprocessing_seconds_)) {}
BMSSPResult BMSSP2025Engine::solve(ExternalVertexId source, BMSSPOptions options) const {
    QueryProfile profile;
    ProfileSession profile_session(options.profile ? &profile : nullptr);
    validate_numeric_environment();
    const auto original_source = reduction_.original.vertex_index(source);
    const auto start = Clock::now();
    const auto n = reduction_.graph.vertex_count();
    const auto log = std::log2(static_cast<long double>(n));
    if (!std::isfinite(log) || log < 0 || log > std::numeric_limits<std::size_t>::digits)
        throw std::length_error("invalid graph logarithm");
    std::size_t k = 1, t = 1;
    while (k < std::numeric_limits<std::size_t>::digits) {
        const auto next = static_cast<long double>(k + 1);
        if (next * next * next > log)
            break;
        ++k;
    }
    while (t < std::numeric_limits<std::size_t>::digits) {
        const auto next = static_cast<long double>(t + 1);
        if (next * next * next > log * log)
            break;
        ++t;
    }
    const auto log_ceil = static_cast<std::size_t>(std::bit_width(n - 1));
    const auto level = checked_size_add(log_ceil, t - 1) / t;
    const auto transformed_source = reduction_.representative[original_source];
    BMSSPWorkspace workspace(reduction_.graph, reduction_.graph.external_id(transformed_source), k,
                             t, std::move(options));
    const auto complete = workspace.run(level, {}, {transformed_source});
    if (complete.bound.finite())
        throw std::logic_error("SSSP root returned partial result");
    const auto finite =
        static_cast<std::size_t>(std::count_if(workspace.labels().begin(), workspace.labels().end(),
                                               [](const auto &label) { return label.finite(); }));
    if (complete.completed.size() != finite)
        throw std::logic_error("root completion set does not cover finite labels");
    ShortestPathResult result{
        reduction_.original,
        original_source,
        std::vector<Distance>(reduction_.original.vertex_count(), unreachable),
        std::vector<std::optional<EdgeId>>(reduction_.original.vertex_count()),
        {}};
    for (VertexIndex u = 0; u < result.distances.size(); ++u)
        result.distances[u] = workspace.labels()[reduction_.representative[u]].distance();
    // Contract zero-cost vertex cycles. Build an acyclic original tight-edge tree:
    // a transformed hop-optimal path can revisit an original vertex via different ports.
    std::queue<VertexIndex> queue;
    std::vector<bool> seen(result.distances.size(), false);
    queue.push(original_source);
    seen[original_source] = true;
    while (!queue.empty()) {
        const auto u = queue.front();
        queue.pop();
        for (const auto &edge : reduction_.original.outgoing(u))
            if (!seen[edge.to] && checked_distance_add(result.distances[u], edge.weight) ==
                                      result.distances[edge.to]) {
                seen[edge.to] = true;
                result.predecessor_edges[edge.to] = edge.id;
                queue.push(edge.to);
            }
    }
    auto diagnostics = workspace.diagnostics();
    for (VertexIndex u = 0; u < result.distances.size(); ++u)
        if (std::isfinite(result.distances[u])) {
            if (!seen[u])
                throw std::logic_error("no valid original tight-edge projection");
            diagnostics.original_reachable_vertices =
                checked_size_add(diagnostics.original_reachable_vertices, 1);
        }
    diagnostics.completed_vertices = complete.completed.size();
    diagnostics.transformed_vertices = n;
    diagnostics.transformed_edges = reduction_.graph.edge_count();
    diagnostics.root_level = level;
    diagnostics.preprocessing_seconds = preprocessing_seconds_;
    diagnostics.query_seconds = seconds(start);
    diagnostics.profile = profile;
    return {std::move(result), diagnostics};
}
BMSSPResult bmssp_2025(const Graph &graph, ExternalVertexId source, BMSSPOptions options) {
    (void)graph.vertex_index(source); // Reject empty/invalid sources before transformation.
    return BMSSP2025Engine(graph).solve(source, std::move(options));
}
} // namespace bmssp
