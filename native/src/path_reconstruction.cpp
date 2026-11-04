// SPDX-License-Identifier: Apache-2.0
#include "bmssp/result.hpp"
#include <algorithm>

namespace bmssp {
Path reconstruct_path(const Graph &graph, const ShortestPathResult &result,
                      ExternalVertexId target) {
    validate_numeric_environment();
    const auto n = graph.vertex_count();
    if (!graph.same_storage(result.graph) || result.source >= n || result.distances.size() != n ||
        result.predecessor_edges.size() != n)
        throw std::invalid_argument("result does not match graph");
    const auto destination = graph.vertex_index(target);
    if (result.distances[result.source] != 0 || result.predecessor_edges[result.source]) {
        throw std::invalid_argument("invalid source label or predecessor");
    }
    const auto distance = result.distances[destination];
    if (distance == unreachable) {
        if (result.predecessor_edges[destination])
            throw std::invalid_argument("unreachable target has predecessor");
        return {PathStatus::unreachable, unreachable, {}, {}};
    }
    if (!std::isfinite(distance) || distance < 0)
        throw std::invalid_argument("invalid target distance");
    Path path{PathStatus::reachable, distance, {}, {}};
    auto current = destination;
    for (std::size_t steps = 0; current != result.source; ++steps) {
        if (steps >= n || !result.predecessor_edges[current])
            throw std::invalid_argument("broken or cyclic predecessor chain");
        const auto &e = graph.edge(*result.predecessor_edges[current]);
        if (e.to != current)
            throw std::invalid_argument("predecessor edge has wrong direction");
        if (checked_distance_add(result.distances[e.from], e.weight) != result.distances[current]) {
            throw std::invalid_argument("predecessor label mismatch");
        }
        path.vertices.push_back(graph.external_id(current));
        path.edges.push_back(e.id);
        current = e.from;
    }
    path.vertices.push_back(graph.external_id(result.source));
    std::reverse(path.vertices.begin(), path.vertices.end());
    std::reverse(path.edges.begin(), path.edges.end());
    Distance sum = 0;
    for (const auto id : path.edges)
        sum = checked_distance_add(sum, graph.edge(id).weight);
    if (sum != distance)
        throw std::invalid_argument("path weight differs from reported distance");
    return path;
}
} // namespace bmssp
