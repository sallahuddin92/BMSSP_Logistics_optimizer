// SPDX-License-Identifier: Apache-2.0
#include "test_support.hpp"
#include <limits>
using namespace bmssp;
int main() {
    test::run("single_edge", [] {
        Graph g({0, 1}, {{0, 0, 1, 5}});
        const auto r = reference_dijkstra(g, 0);
        CHECK(r.distances == std::vector<Distance>({0, 5}));
        CHECK(r.predecessor_edges[1] == 0);
    });
    test::run("alternative_paths", [] {
        auto g = test::fixture();
        const auto r = reference_dijkstra(g, 0);
        CHECK(r.distances == std::vector<Distance>({0, 3, 2, 7, unreachable}));
        CHECK(r.diagnostics.settled_vertices == 4);
        CHECK(r.diagnostics.scanned_edges == 5);
    });
    test::run("equal_cost_deterministic", [] {
        Graph g({0, 1, 2, 3}, {{8, 0, 2, 1}, {7, 0, 1, 1}, {2, 1, 3, 1}, {1, 2, 3, 1}});
        const auto a = reference_dijkstra(g, 0), b = reference_dijkstra(g, 0);
        CHECK(a.predecessor_edges == b.predecessor_edges);
        CHECK(a.predecessor_edges[3] == 2);
    });
    test::run("directed_cycle", [] {
        Graph g({0, 1, 2}, {{0, 0, 1, 2}, {1, 1, 2, 3}, {2, 2, 0, 4}});
        CHECK(reference_dijkstra(g, 2).distances == std::vector<Distance>({4, 6, 0}));
    });
    test::run("zero_cycle", [] {
        Graph g({0, 1, 2}, {{0, 0, 1, 0}, {1, 1, 0, 0}, {2, 1, 2, 0}, {3, 2, 1, 0}});
        const auto r = reference_dijkstra(g, 0);
        CHECK(r.distances == std::vector<Distance>({0, 0, 0}));
        CHECK(!r.predecessor_edges[0]);
        CHECK(reconstruct_path(g, r, 2).edges == std::vector<EdgeId>({0, 2}));
    });
    test::run("isolated_source", [] {
        auto g = test::fixture();
        const auto r = reference_dijkstra(g, 4);
        CHECK(r.distances ==
              std::vector<Distance>({unreachable, unreachable, unreachable, unreachable, 0}));
    });
    test::run("sink_source", [] {
        auto g = test::fixture();
        CHECK(reference_dijkstra(g, 3).distances ==
              std::vector<Distance>({unreachable, unreachable, unreachable, 0, unreachable}));
    });
    test::run("parallel_minimum", [] {
        Graph g({0, 1}, {{9, 0, 1, 8}, {7, 0, 1, 2}, {6, 0, 1, 2}});
        const auto r = reference_dijkstra(g, 0);
        CHECK(r.distances[1] == 2);
        CHECK(r.predecessor_edges[1] == 6);
    });
    test::run("invalid_source", [] {
        Graph g({}, {});
        test::throws<std::out_of_range>([&] { (void)reference_dijkstra(g, 0); });
    });
    test::run("repeated_sources", [] {
        auto g = test::fixture();
        const auto a = reference_dijkstra(g, 0);
        (void)reference_dijkstra(g, 3);
        const auto b = reference_dijkstra(g, 0);
        CHECK(a.distances == b.distances);
        CHECK(a.predecessor_edges == b.predecessor_edges);
        CHECK(g.edge(10).weight == 9);
    });
    test::run("overflow_rejected", [] {
        Graph g({0, 1, 2}, {{0, 0, 1, std::numeric_limits<double>::max()},
                            {1, 1, 2, std::numeric_limits<double>::max()}});
        test::throws<std::overflow_error>([&] { (void)reference_dijkstra(g, 0); });
    });
    test::run("invalid_arithmetic", [] {
        test::throws<std::invalid_argument>([] { (void)checked_distance_add(unreachable, 0); });
        test::throws<std::invalid_argument>([] { (void)checked_distance_add(0, -1); });
    });
    test::run("fractional_comparison", [] {
        Graph g({0, 1, 2}, {{0, 0, 1, .1}, {1, 1, 2, .2}, {2, 0, 2, .3}});
        const auto r = reference_dijkstra(g, 0);
        CHECK(r.distances[2] == .3);
        CHECK(reconstruct_path(g, r, 2).edges == std::vector<EdgeId>({2}));
    });
    test::run("subnormal", [] {
        const auto w = std::numeric_limits<double>::denorm_min();
        Graph g({0, 1}, {{0, 0, 1, w}});
        CHECK(reference_dijkstra(g, 0).distances[1] == w);
    });
    test::run("large_sparse_chain", [] {
        std::vector<ExternalVertexId> ids;
        std::vector<InputEdge> edges;
        for (ExternalVertexId i = 0; i < 10000; ++i) {
            ids.push_back(i);
            if (i > 0)
                edges.push_back({static_cast<EdgeId>(i), i - 1, i, 1});
        }
        Graph g(std::move(ids), std::move(edges));
        const auto r = reference_dijkstra(g, 0);
        CHECK(r.distances.back() == 9999);
        CHECK(reconstruct_path(g, r, 9999).edges.size() == 9999);
    });
    test::run("rounding_mode_rejected", [] {
        const auto original = std::fegetround();
        CHECK(std::fesetround(FE_DOWNWARD) == 0);
        bool rejected = false;
        try {
            Graph g({0}, {});
            (void)reference_dijkstra(g, 0);
        } catch (const std::invalid_argument &) {
            rejected = true;
        }
        const auto restored = std::fesetround(original);
        CHECK(restored == 0);
        CHECK(rejected);
    });
    return test::finish();
}
