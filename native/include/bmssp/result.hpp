// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/graph.hpp"
#include <optional>
#include <vector>

namespace bmssp {
struct Diagnostics {
    std::size_t settled_vertices = 0;
    std::size_t scanned_edges = 0;
    std::size_t successful_relaxations = 0;
    std::size_t queue_pushes = 0;
};
struct ShortestPathResult {
    Graph graph; // Keeps the exact immutable graph alive; no graph data copy.
    VertexIndex source;
    std::vector<Distance> distances;
    std::vector<std::optional<EdgeId>> predecessor_edges;
    Diagnostics diagnostics;
};
enum class PathStatus { reachable, unreachable };
struct Path {
    PathStatus status;
    Distance distance;
    std::vector<ExternalVertexId> vertices;
    std::vector<EdgeId> edges;
};
[[nodiscard]] Path reconstruct_path(const Graph &graph, const ShortestPathResult &result,
                                    ExternalVertexId target);
} // namespace bmssp
