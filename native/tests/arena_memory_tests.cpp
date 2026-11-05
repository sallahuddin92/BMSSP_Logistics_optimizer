// SPDX-License-Identifier: Apache-2.0
#include "../test_support/allocation_tracking.hpp"
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include "test_support.hpp"
#include <future>
using namespace bmssp;
int main() {
    test::run("failed_root_construction_unwinds", [] {
        for (std::size_t point = 0; point < 3; ++point) {
            bool failed = false;
            try {
                allocation_probe::FailAfter inject(point);
                (void)SymbolicLabel::root(0);
            } catch (const std::bad_alloc &) {
                failed = true;
            }
            CHECK(failed);
            CHECK(SymbolicLabel::root(0).finite());
        }
    });
    test::run("failed_growth_preserves_published_parents", [] {
        const auto root = SymbolicLabel::root(0);
        const auto *root_address = root.node();
        auto current = root;
        for (std::size_t point = 0; point < 4; ++point) {
            bool failed = false;
            try {
                allocation_probe::FailAfter inject(point);
                for (std::size_t i = 0; i < 100000; ++i) {
                    const auto from = current.node()->vertex;
                    current = current.extend({static_cast<EdgeId>(from), from, from + 1, 1});
                }
            } catch (const std::bad_alloc &) {
                failed = true;
            }
            CHECK(failed);
            CHECK(root.node() == root_address);
            CHECK(root.distance() == 0);
            const auto previous = current;
            const auto from = previous.node()->vertex;
            current = current.extend({static_cast<EdgeId>(from), from, from + 1, 1});
            CHECK(current.node()->parent == previous.node());
            CHECK(current.distance() == previous.distance() + 1);
            for (auto node = current.node(); node->parent; node = node->parent) {
                CHECK(node->hops == node->parent->hops + 1);
                CHECK(node->distance == node->parent->distance + 1);
            }
        }
    });
    test::run("shared_arena_concurrent_growth_and_order", [] {
        const auto root = SymbolicLabel::root(0);
        std::array<std::future<SymbolicLabel>, 4> jobs;
        for (std::size_t thread = 0; thread < jobs.size(); ++thread)
            jobs[thread] = std::async(std::launch::async, [root, thread] {
                auto current = root;
                for (VertexIndex v = 1; v <= 5000; ++v)
                    current =
                        current.extend({static_cast<EdgeId>(thread * 10000 + v), v - 1, v, 0});
                return current;
            });
        std::array<SymbolicLabel, 4> results;
        for (std::size_t i = 0; i < jobs.size(); ++i) {
            results[i] = jobs[i].get();
            CHECK(results[i].node()->hops == 5000);
            CHECK(results[i].distance() == 0);
        }
        for (std::size_t i = 1; i < results.size(); ++i)
            CHECK(results[i - 1] < results[i]);
        CHECK(root.node()->vertex == 0);
    });
    test::run("query_failure_does_not_poison_engine", [] {
        const auto graph = test::fixture();
        const BMSSP2025Engine engine(graph);
        const auto expected = reference_dijkstra(graph, 0).distances;
        for (const std::size_t point : {0U, 1U, 2U, 4U, 8U, 16U}) {
            bool failed = false;
            try {
                allocation_probe::FailAfter inject(point);
                (void)engine.solve(0);
            } catch (const std::bad_alloc &) {
                failed = true;
            }
            CHECK(failed);
            CHECK(engine.solve(0).shortest_paths.distances == expected);
        }
    });
    test::run("frontier_reinitialize_after_allocation_failure", [] {
        const auto root = SymbolicLabel::root(0);
        FrontierCounters counters;
        BoundedFrontier frontier(4, {}, counters);
        for (const std::size_t point : {0U, 1U, 3U}) {
            frontier.initialize(4, {});
            bool failed = false;
            try {
                allocation_probe::FailAfter inject(point);
                for (VertexIndex key = 0; key < 100000; ++key)
                    frontier.insert(key, root.extend({static_cast<EdgeId>(key), 0, key,
                                                      100 + static_cast<double>(key)}));
            } catch (const std::bad_alloc &) {
                failed = true;
            }
            CHECK(failed);
            frontier.initialize(4, {});
            frontier.validate();
            CHECK(frontier.empty());
            frontier.insert(9, root.extend({9, 0, 9, 9}));
            CHECK(frontier.pull().entries.at(0).key == 9);
        }
    });
    test::run("repeated_large_arena_lifetime", [] {
        for (std::size_t repeat = 0; repeat < 20; ++repeat) {
            auto current = SymbolicLabel::root(0);
            const auto saved = current;
            for (VertexIndex v = 1; v <= 30000; ++v)
                current = current.extend({static_cast<EdgeId>(v), v - 1, v, 0});
            CHECK(saved.node()->parent == nullptr);
            CHECK(saved.distance() == 0);
            CHECK(current.node()->hops == 30000);
        }
    });
    return test::finish();
}
