// SPDX-License-Identifier: Apache-2.0
#include "test_support.hpp"
using namespace bmssp;
int main() {
    test::run("connected_original_edges", [] {
        auto g = test::fixture();
        const auto r = reference_dijkstra(g, 0);
        const auto p = reconstruct_path(g, r, 3);
        CHECK(p.status == PathStatus::reachable);
        CHECK(p.vertices == std::vector<ExternalVertexId>({0, 2, 1, 3}));
        CHECK(p.edges == std::vector<EdgeId>({11, 12, 13}));
        CHECK(p.distance == 7);
    });
    test::run("unreachable", [] {
        auto g = test::fixture();
        const auto p = reconstruct_path(g, reference_dijkstra(g, 0), 4);
        CHECK(p.status == PathStatus::unreachable);
        CHECK(p.distance == unreachable);
        CHECK(p.edges.empty());
        CHECK(p.vertices.empty());
    });
    test::run("source_path", [] {
        auto g = test::fixture();
        auto p = reconstruct_path(g, reference_dijkstra(g, 0), 0);
        CHECK(p.vertices == std::vector<ExternalVertexId>({0}));
        CHECK(p.edges.empty());
        CHECK(p.distance == 0);
    });
    test::run("missing_predecessor", [] {
        auto g = test::fixture();
        auto r = reference_dijkstra(g, 0);
        r.predecessor_edges[3].reset();
        test::throws<std::invalid_argument>([&] { (void)reconstruct_path(g, r, 3); });
    });
    test::run("wrong_direction", [] {
        auto g = test::fixture();
        auto r = reference_dijkstra(g, 0);
        r.predecessor_edges[3] = 12;
        test::throws<std::invalid_argument>([&] { (void)reconstruct_path(g, r, 3); });
    });
    test::run("wrong_distance", [] {
        auto g = test::fixture();
        auto r = reference_dijkstra(g, 0);
        r.distances[3] = 8;
        test::throws<std::invalid_argument>([&] { (void)reconstruct_path(g, r, 3); });
    });
    test::run("cyclic_predecessors", [] {
        Graph g({0, 1, 2}, {{0, 0, 1, 0}, {1, 1, 2, 0}, {2, 2, 1, 0}});
        auto r = reference_dijkstra(g, 0);
        r.predecessor_edges[1] = 2;
        test::throws<std::invalid_argument>([&] { (void)reconstruct_path(g, r, 2); });
    });
    test::run("unknown_edge", [] {
        auto g = test::fixture();
        auto r = reference_dijkstra(g, 0);
        r.predecessor_edges[3] = 999;
        test::throws<std::out_of_range>([&] { (void)reconstruct_path(g, r, 3); });
    });
    test::run("graph_mismatch", [] {
        auto g = test::fixture(), other = test::fixture();
        const auto r = reference_dijkstra(g, 0);
        test::throws<std::invalid_argument>([&] { (void)reconstruct_path(other, r, 3); });
    });
    test::run("invalid_result_shape", [] {
        auto g = test::fixture();
        auto r = reference_dijkstra(g, 0);
        r.distances.pop_back();
        test::throws<std::invalid_argument>([&] { (void)reconstruct_path(g, r, 3); });
    });
    test::run("invalid_source_label", [] {
        auto g = test::fixture();
        auto r = reference_dijkstra(g, 0);
        r.predecessor_edges[0] = 10;
        test::throws<std::invalid_argument>([&] { (void)reconstruct_path(g, r, 3); });
    });
    test::run("invalid_target_label", [] {
        auto g = test::fixture();
        auto r = reference_dijkstra(g, 0);
        r.distances[3] = std::numeric_limits<double>::quiet_NaN();
        test::throws<std::invalid_argument>([&] { (void)reconstruct_path(g, r, 3); });
    });
    test::run("unreachable_has_predecessor", [] {
        auto g = test::fixture();
        auto r = reference_dijkstra(g, 0);
        r.predecessor_edges[4] = 10;
        test::throws<std::invalid_argument>([&] { (void)reconstruct_path(g, r, 4); });
    });
    test::run("invalid_target", [] {
        auto g = test::fixture();
        const auto r = reference_dijkstra(g, 0);
        test::throws<std::out_of_range>([&] { (void)reconstruct_path(g, r, 99); });
    });
    return test::finish();
}
