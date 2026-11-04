// SPDX-License-Identifier: Apache-2.0
#include "bmssp/degree_reduction.hpp"
#include <algorithm>
#include <limits>
#include <unordered_set>
namespace bmssp {
DegreeReduction reduce_degree(const Graph &original) {
    const auto n = original.vertex_count();
    std::vector<Edge> edges;
    edges.reserve(original.edge_count());
    std::vector<std::size_t> count(n, 0);
    for (VertexIndex u = 0; u < n; ++u)
        for (const auto &e : original.outgoing(u)) {
            edges.push_back(e);
            count[e.from] = checked_size_add(count[e.from], 1);
            count[e.to] = checked_size_add(count[e.to], 1);
        }
    std::sort(edges.begin(), edges.end(), [](const auto &a, const auto &b) { return a.id < b.id; });
    std::vector<VertexIndex> reps(n), owners;
    std::vector<ExternalVertexId> vertices;
    for (VertexIndex u = 0; u < n; ++u) {
        reps[u] = vertices.size();
        for (std::size_t j = 0; j < std::max(std::size_t{1}, count[u]); ++j) {
            if (vertices.size() >=
                static_cast<std::uint64_t>(std::numeric_limits<ExternalVertexId>::max()))
                throw std::length_error("transformed vertex IDs exhausted");
            vertices.push_back(static_cast<ExternalVertexId>(vertices.size()));
            owners.push_back(u);
        }
    }
    std::vector<InputEdge> transformed;
    std::vector<std::optional<EdgeId>> mapping;
    const auto add = [&](VertexIndex from, VertexIndex to, Weight weight,
                         std::optional<EdgeId> id) {
        if (transformed.size() >= std::numeric_limits<EdgeId>::max())
            throw std::length_error("transformed edge IDs exhausted");
        transformed.push_back({static_cast<EdgeId>(transformed.size()),
                               static_cast<ExternalVertexId>(from),
                               static_cast<ExternalVertexId>(to), weight});
        mapping.push_back(id);
    };
    for (VertexIndex u = 0; u < n; ++u)
        if (count[u] > 1) {
            for (std::size_t j = 0; j < count[u]; ++j)
                add(reps[u] + j, reps[u] + (j + 1) % count[u], 0, std::nullopt);
        }
    auto next = reps;
    for (const auto &e : edges) {
        const auto from = next[e.from]++;
        const auto to = next[e.to]++;
        add(from, to, e.weight, e.id);
    }
    DegreeReduction reduced{original, Graph(std::move(vertices), std::move(transformed)),
                            std::move(reps), std::move(owners), std::move(mapping)};
    reduced.validate();
    return reduced;
}
void DegreeReduction::validate() const {
    if (representative.size() != original.vertex_count() ||
        original_vertex.size() != graph.vertex_count() ||
        original_edge.size() != graph.edge_count())
        throw std::logic_error("invalid transformation mapping sizes");
    std::vector<std::size_t> indegree(graph.vertex_count(), 0);
    std::size_t real_count = 0;
    std::unordered_set<EdgeId> unique_original;
    std::vector<std::optional<VertexIndex>> successor(graph.vertex_count());
    std::vector<std::size_t> synthetic_in(graph.vertex_count(), 0),
        owner_count(original.vertex_count(), 0);
    for (VertexIndex u = 0; u < graph.vertex_count(); ++u) {
        if (original_vertex[u] >= original.vertex_count() || graph.outgoing(u).size() > 2)
            throw std::logic_error("invalid transformed vertex");
        ++owner_count[original_vertex[u]];
        for (const auto &e : graph.outgoing(u)) {
            if (++indegree[e.to] > 2 || e.id >= original_edge.size())
                throw std::logic_error("transformed degree/edge violation");
            if (const auto id = original_edge[static_cast<std::size_t>(e.id)]) {
                const auto &old = original.edge(*id);
                ++real_count;
                if (!unique_original.insert(*id).second)
                    throw std::logic_error("duplicate original edge mapping");
                if (old.from != original_vertex[e.from] || old.to != original_vertex[e.to] ||
                    old.weight != e.weight)
                    throw std::logic_error("original edge not preserved");
            } else {
                if (e.weight != 0 || original_vertex[e.from] != original_vertex[e.to] ||
                    successor[e.from] || ++synthetic_in[e.to] > 1)
                    throw std::logic_error("invalid synthetic edge");
                successor[e.from] = e.to;
            }
        }
    }
    if (real_count != original.edge_count())
        throw std::logic_error("original edge count mismatch");
    std::vector<bool> visited(graph.vertex_count(), false);
    for (VertexIndex u = 0; u < representative.size(); ++u) {
        if (representative[u] >= graph.vertex_count() || original_vertex[representative[u]] != u)
            throw std::logic_error("invalid representative");
        auto v = representative[u];
        if (owner_count[u] == 1 && !successor[v]) {
            visited[v] = true;
            continue;
        }
        for (std::size_t i = 0; i < owner_count[u]; ++i) {
            if (visited[v] || original_vertex[v] != u || !successor[v] || synthetic_in[v] != 1)
                throw std::logic_error("invalid synthetic vertex cycle");
            visited[v] = true;
            v = *successor[v];
        }
        if (v != representative[u])
            throw std::logic_error("synthetic cycle is not closed");
    }
    if (std::find(visited.begin(), visited.end(), false) != visited.end())
        throw std::logic_error("unmapped transformed port");
}
Path project_path(const DegreeReduction &reduction, const SymbolicLabel &label) {
    if (!label.finite())
        return {PathStatus::unreachable, unreachable, {}, {}};
    std::vector<EdgeId> transformed;
    auto node = label.node();
    if (node->vertex >= reduction.graph.vertex_count())
        throw std::invalid_argument("projection vertex out of range");
    const auto target = reduction.original_vertex[node->vertex];
    for (std::size_t steps = 0; node->parent; ++steps) {
        if (steps >= reduction.graph.vertex_count() || !node->edge)
            throw std::invalid_argument("projection chain is cyclic/invalid");
        const auto &edge = reduction.graph.edge(*node->edge);
        if (edge.to != node->vertex || edge.from != node->parent->vertex ||
            checked_distance_add(node->parent->distance, edge.weight) != node->distance)
            throw std::invalid_argument("invalid transformed path");
        transformed.push_back(edge.id);
        node = node->parent;
    }
    Path path{PathStatus::reachable,
              label.distance(),
              {reduction.original.external_id(reduction.original_vertex[node->vertex])},
              {}};
    std::reverse(transformed.begin(), transformed.end());
    Distance sum = 0;
    for (const auto id : transformed)
        if (const auto old_id = reduction.original_edge.at(static_cast<std::size_t>(id))) {
            const auto &e = reduction.original.edge(*old_id);
            if (reduction.original.external_id(e.from) != path.vertices.back())
                throw std::logic_error("projected path disconnected");
            path.vertices.push_back(reduction.original.external_id(e.to));
            path.edges.push_back(*old_id);
            sum = checked_distance_add(sum, e.weight);
        }
    if (path.vertices.back() != reduction.original.external_id(target) || sum != path.distance)
        throw std::logic_error("projected path distance mismatch");
    return path;
}
} // namespace bmssp
