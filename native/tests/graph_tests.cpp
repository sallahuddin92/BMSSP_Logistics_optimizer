// SPDX-License-Identifier: Apache-2.0
#include "test_support.hpp"
#include <algorithm>
#include <limits>
using namespace bmssp;
int main() {
    test::run("empty", [] {
        Graph g({}, {});
        CHECK(g.vertex_count() == 0);
        CHECK(g.edge_count() == 0);
        test::throws<std::out_of_range>([&] { (void)g.outgoing(0); });
    });
    test::run("singleton", [] {
        Graph g({42}, {});
        CHECK(g.vertex_index(42) == 0);
        CHECK(g.outgoing(0).empty());
    });
    test::run("isolates_and_sinks", [] {
        Graph g({0, 1, 2}, {{1, 0, 1, 2}});
        CHECK(g.outgoing(1).empty());
        CHECK(g.outgoing(2).empty());
        CHECK(g.outgoing(0).size() == 1);
    });
    test::run("directed", [] {
        Graph g({0, 1}, {{8, 0, 1, 1}});
        CHECK(g.outgoing(1).empty());
        CHECK(g.edge(8).from == 0);
        CHECK(g.edge(8).to == 1);
    });
    test::run("parallel_edges", [] {
        Graph g({0, 1}, {{8, 0, 1, 3}, {2, 0, 1, 1}});
        CHECK(g.edge_count() == 2);
        CHECK(g.outgoing(0)[0].id == 2);
    });
    test::run("self_loop_zero", [] {
        Graph g({0}, {{99, 0, 0, 0}});
        CHECK(g.edge(99).weight == 0);
    });
    test::run("negative_rejected",
              [] { test::throws<std::invalid_argument>([] { Graph g({0}, {{0, 0, 0, -1}}); }); });
    test::run("nan_rejected", [] {
        test::throws<std::invalid_argument>(
            [] { Graph g({0}, {{0, 0, 0, std::numeric_limits<double>::quiet_NaN()}}); });
    });
    test::run("infinities_rejected", [] {
        for (double w : {unreachable, -unreachable})
            test::throws<std::invalid_argument>([w] { Graph g({0}, {{0, 0, 0, w}}); });
    });
    test::run("int64_ids", [] {
        Graph g({std::numeric_limits<ExternalVertexId>::min(), 5000000000LL,
                 std::numeric_limits<ExternalVertexId>::max()},
                {});
        CHECK(g.external_id(1) == 5000000000LL);
        CHECK(g.vertex_index(std::numeric_limits<ExternalVertexId>::max()) == 2);
    });
    test::run("invalid_references", [] {
        test::throws<std::invalid_argument>([] { Graph g({0}, {{0, 0, 1, 1}}); });
        Graph g({0}, {});
        test::throws<std::out_of_range>([&] { (void)g.vertex_index(1); });
        test::throws<std::out_of_range>([&] { (void)g.external_id(1); });
        test::throws<std::out_of_range>([&] { (void)g.edge(0); });
    });
    test::run("duplicate_ids", [] {
        test::throws<std::invalid_argument>([] { Graph g({0, 0}, {}); });
        test::throws<std::invalid_argument>([] { Graph g({0}, {{1, 0, 0, 0}, {1, 0, 0, 1}}); });
    });
    test::run("deterministic_permutations", [] {
        Graph a({3, 1, 2}, {{9, 3, 1, 2}, {4, 1, 2, 0}, {2, 1, 2, 1}});
        Graph b({2, 3, 1}, {{2, 1, 2, 1}, {9, 3, 1, 2}, {4, 1, 2, 0}});
        for (VertexIndex u = 0; u < a.vertex_count(); ++u) {
            CHECK(a.external_id(u) == b.external_id(u));
            const auto x = a.outgoing(u), y = b.outgoing(u);
            CHECK(x.size() == y.size());
            for (std::size_t i = 0; i < x.size(); ++i) {
                CHECK(x[i].id == y[i].id);
                CHECK(x[i].to == y[i].to);
                CHECK(x[i].weight == y[i].weight);
            }
        }
    });
    test::run("storage_lifetime", [] {
        Graph g = test::fixture();
        Graph copy = g;
        CHECK(copy.same_storage(g));
        CHECK(&copy.edge(10) == &g.edge(10));
        auto result = reference_dijkstra(test::fixture(), 0);
        CHECK(reconstruct_path(result.graph, result, 3).distance == 7);
    });
    test::run("checked_sizes", [] {
        test::throws<std::length_error>(
            [] { (void)checked_size_add(std::numeric_limits<std::size_t>::max(), 1); });
        test::throws<std::length_error>(
            [] { check_allocation_count<Edge>(std::numeric_limits<std::size_t>::max()); });
    });
    test::run("negative_zero_canonicalized", [] {
        Graph g({0}, {{0, 0, 0, -0.0}});
        CHECK(!std::signbit(g.edge(0).weight));
    });
    test::run("maximum_edge_id", [] {
        const auto id = std::numeric_limits<EdgeId>::max();
        Graph g({0, 1}, {{id, 0, 1, 2}});
        const auto r = reference_dijkstra(g, 0);
        CHECK(reconstruct_path(g, r, 1).edges == std::vector<EdgeId>({id}));
    });
    return test::finish();
}
