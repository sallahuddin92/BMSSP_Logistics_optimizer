// SPDX-License-Identifier: Apache-2.0
#include "bmssp/reference_dijkstra.hpp"
#include <functional>
#include <queue>
#include <utility>

namespace bmssp {
ShortestPathResult reference_dijkstra(const Graph &graph, ExternalVertexId source) {
    validate_numeric_environment();
    const auto start = graph.vertex_index(source);
    check_allocation_count<Distance>(graph.vertex_count());
    check_allocation_count<std::optional<EdgeId>>(graph.vertex_count());
    ShortestPathResult result{graph,
                              start,
                              std::vector<Distance>(graph.vertex_count(), unreachable),
                              std::vector<std::optional<EdgeId>>(graph.vertex_count()),
                              {}};
    using Item = std::pair<Distance, VertexIndex>;
    std::priority_queue<Item, std::vector<Item>, std::greater<>> queue;
    result.distances[start] = 0;
    queue.emplace(0, start);
    result.diagnostics.queue_pushes = 1;
    while (!queue.empty()) {
        const auto [distance, u] = queue.top();
        queue.pop();
        if (distance != result.distances[u])
            continue;
        result.diagnostics.settled_vertices =
            checked_size_add(result.diagnostics.settled_vertices, 1);
        for (const auto &e : graph.outgoing(u)) {
            result.diagnostics.scanned_edges =
                checked_size_add(result.diagnostics.scanned_edges, 1);
            const auto candidate = checked_distance_add(distance, e.weight);
            if (candidate < result.distances[e.to]) {
                result.distances[e.to] = candidate;
                result.predecessor_edges[e.to] = e.id;
                queue.emplace(candidate, e.to);
                result.diagnostics.successful_relaxations =
                    checked_size_add(result.diagnostics.successful_relaxations, 1);
                result.diagnostics.queue_pushes =
                    checked_size_add(result.diagnostics.queue_pushes, 1);
            }
        }
    }
    return result;
}
} // namespace bmssp
