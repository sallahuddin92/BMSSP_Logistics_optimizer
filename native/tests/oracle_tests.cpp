// SPDX-License-Identifier: Apache-2.0
#include "test_support.hpp"
#include <algorithm>
#include <array>
#include <random>
#include <sstream>
using namespace bmssp;
namespace {
// Test-only Bellman-Ford over raw input edges: no CSR traversal or production arithmetic helper.
std::vector<double> bellman_ford(const std::vector<ExternalVertexId> &ids,
                                 const std::vector<InputEdge> &edges, std::size_t source) {
    std::vector<double> distance(ids.size(), std::numeric_limits<double>::infinity());
    distance[source] = 0;
    for (std::size_t pass = 1; pass < ids.size(); ++pass) {
        bool changed = false;
        for (const auto &e : edges) {
            const auto u =
                static_cast<std::size_t>(std::find(ids.begin(), ids.end(), e.from) - ids.begin());
            const auto v =
                static_cast<std::size_t>(std::find(ids.begin(), ids.end(), e.to) - ids.begin());
            if (std::isfinite(distance[u]) && distance[u] + e.weight < distance[v]) {
                distance[v] = distance[u] + e.weight;
                changed = true;
            }
        }
        if (!changed)
            break;
    }
    return distance;
}
std::size_t graphs = 0, queries = 0, paths = 0, max_vertices = 0, max_edges = 0;
void verify(const std::vector<ExternalVertexId> &ids, const std::vector<InputEdge> &edges,
            std::uint64_t seed) {
    try {
        Graph graph(ids, edges);
        ++graphs;
        max_vertices = std::max(max_vertices, ids.size());
        max_edges = std::max(max_edges, edges.size());
        for (std::size_t s = 0; s < ids.size(); ++s) {
            const auto expected = bellman_ford(ids, edges, s);
            const auto result = reference_dijkstra(graph, ids[s]);
            ++queries;
            for (std::size_t t = 0; t < ids.size(); ++t) {
                const auto d = result.distances[graph.vertex_index(ids[t])];
                CHECK(d == expected[t]); // Integer/dyadic fixture sums are exact; no tolerance.
                const auto path = reconstruct_path(graph, result, ids[t]);
                ++paths;
                CHECK((path.status == PathStatus::unreachable) == !std::isfinite(expected[t]));
                if (path.status == PathStatus::unreachable)
                    continue;
                CHECK(path.vertices.front() == ids[s]);
                CHECK(path.vertices.back() == ids[t]);
                CHECK(path.vertices.size() == path.edges.size() + 1);
                double sum = 0;
                for (std::size_t i = 0; i < path.edges.size(); ++i) {
                    const auto it = std::find_if(edges.begin(), edges.end(), [&](const auto &e) {
                        return e.id == path.edges[i];
                    });
                    CHECK(it != edges.end());
                    CHECK(it->from == path.vertices[i]);
                    CHECK(it->to == path.vertices[i + 1]);
                    sum += it->weight;
                }
                CHECK(sum == expected[t]);
            }
        }
    } catch (const std::exception &e) {
        std::ostringstream out;
        out << "seed=" << seed << " n=" << ids.size() << " m=" << edges.size() << "\nvertices";
        for (const auto id : ids)
            out << ' ' << id;
        out << "\nedges(id from to weight)\n";
        for (const auto &edge : edges)
            out << edge.id << ' ' << edge.from << ' ' << edge.to << ' ' << edge.weight << '\n';
        throw std::runtime_error(out.str() + e.what());
    }
}
} // namespace
int main() {
    test::run("manual_oracle_fixture", [] {
        verify({0, 1, 2, 3, 4},
               {{10, 0, 1, 9}, {11, 0, 2, 2}, {12, 2, 1, 1}, {13, 1, 3, 4}, {14, 2, 3, 20}}, 0);
    });
    test::run("undirected_paired_arcs", [] {
        verify({0, 1, 2}, {{0, 0, 1, 2}, {1, 1, 0, 2}, {2, 1, 2, 0}, {3, 2, 1, 0}}, 0);
    });
    test::run("fixed_seed_differential", [] {
        for (const std::uint64_t seed : std::array<std::uint64_t, 3>{2025, 17033, 0xB055ULL}) {
            std::mt19937_64 rng(seed);
            for (const std::size_t n : std::array<std::size_t, 6>{1, 2, 5, 12, 32, 64}) {
                for (const std::uint64_t density : std::array<std::uint64_t, 4>{0, 5, 25, 100}) {
                    std::vector<ExternalVertexId> ids;
                    for (std::size_t i = 0; i < n; ++i)
                        ids.push_back(5000000000LL + static_cast<ExternalVertexId>(i));
                    std::vector<InputEdge> edges;
                    EdgeId id = 0;
                    for (const auto u : ids)
                        for (const auto v : ids)
                            if (rng() % 100 < density) {
                                edges.push_back(
                                    {id++, u, v, static_cast<double>(rng() % 81) / 4.0});
                                if (rng() % 11 == 0)
                                    edges.push_back(
                                        {id++, u, v, static_cast<double>(rng() % 81) / 4.0});
                            }
                    verify(ids, edges, seed);
                }
            }
        }
    });
    std::cout << "graphs=" << graphs << " source_queries=" << queries << " path_checks=" << paths
              << " max_vertices=" << max_vertices << " max_edges=" << max_edges << '\n';
    return test::finish();
}
