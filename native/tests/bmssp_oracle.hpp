// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/bmssp_2025.hpp"
#include "test_support.hpp"
#include <algorithm>
#include <unordered_set>
namespace independent {
struct Label {
    double distance = bmssp::unreachable;
    std::vector<bmssp::VertexIndex> vertices;
    std::vector<bmssp::EdgeId> edges;
};
inline int compare(const Label &a, const Label &b) {
    if (a.distance < b.distance)
        return -1;
    if (b.distance < a.distance)
        return 1;
    if (a.vertices.empty() && b.vertices.empty())
        return 0;
    if (a.edges.size() < b.edges.size())
        return -1;
    if (b.edges.size() < a.edges.size())
        return 1;
    if (std::lexicographical_compare(a.vertices.rbegin(), a.vertices.rend(), b.vertices.rbegin(),
                                     b.vertices.rend()))
        return -1;
    if (std::lexicographical_compare(b.vertices.rbegin(), b.vertices.rend(), a.vertices.rbegin(),
                                     a.vertices.rend()))
        return 1;
    if (std::lexicographical_compare(a.edges.rbegin(), a.edges.rend(), b.edges.rbegin(),
                                     b.edges.rend()))
        return -1;
    if (std::lexicographical_compare(b.edges.rbegin(), b.edges.rend(), a.edges.rbegin(),
                                     a.edges.rend()))
        return 1;
    return 0;
}
inline Label view(const bmssp::SymbolicLabel &label) {
    Label result;
    result.distance = label.distance();
    auto node = label.node();
    while (node) {
        result.vertices.push_back(node->vertex);
        if (node->edge)
            result.edges.push_back(*node->edge);
        node = node->parent;
    }
    std::reverse(result.vertices.begin(), result.vertices.end());
    std::reverse(result.edges.begin(), result.edges.end());
    return result;
}
// Independent Bellman-Ford stores full vertex/edge sequences and compares reversed vectors.
inline std::vector<Label> truth(const bmssp::Graph &graph, bmssp::VertexIndex source) {
    std::vector<Label> result(graph.vertex_count());
    result.at(source) = {0, {source}, {}};
    for (std::size_t round = 1; round < graph.vertex_count(); ++round) {
        bool changed = false;
        for (bmssp::VertexIndex u = 0; u < graph.vertex_count(); ++u)
            if (!result[u].vertices.empty())
                for (const auto &edge : graph.outgoing(u)) {
                    auto next = result[u];
                    next.distance += edge.weight;
                    next.vertices.push_back(edge.to);
                    next.edges.push_back(edge.id);
                    if (compare(next, result[edge.to]) < 0) {
                        result[edge.to] = std::move(next);
                        changed = true;
                    }
                }
        if (!changed)
            break;
    }
    return result;
}
inline bool visits(const Label &path, const std::vector<bmssp::VertexIndex> &set) {
    for (const auto vertex : path.vertices)
        if (std::find(set.begin(), set.end(), vertex) != set.end())
            return true;
    return false;
}
inline void bounded_contract(const bmssp::BoundedTrace &event, const std::vector<Label> &exact) {
    const auto bound = view(event.input_bound), returned = view(event.result.bound);
    CHECK(compare(returned, bound) <= 0);
    std::unordered_set<bmssp::VertexIndex> actual(event.result.completed.begin(),
                                                  event.result.completed.end());
    CHECK(actual.size() == event.result.completed.size());
    std::vector<bmssp::VertexIndex> complete_frontier;
    for (const auto s : event.frontier)
        if (compare(view(event.before[s]), exact[s]) == 0)
            complete_frontier.push_back(s);
    for (bmssp::VertexIndex v = 0; v < exact.size(); ++v) {
        if (compare(exact[v], bound) < 0 && compare(view(event.before[v]), exact[v]) != 0)
            CHECK(visits(exact[v], complete_frontier));
        const bool expected = compare(exact[v], returned) < 0 && visits(exact[v], event.frontier);
        CHECK(actual.contains(v) == expected);
        if (actual.contains(v))
            CHECK(compare(view(event.after[v]), exact[v]) == 0);
    }
}
} // namespace independent
