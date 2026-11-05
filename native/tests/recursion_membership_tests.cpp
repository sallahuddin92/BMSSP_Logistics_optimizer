// SPDX-License-Identifier: Apache-2.0
#include "../test_support/allocation_tracking.hpp"
#include "../test_support/run_test_observer.hpp"
#include "bmssp/detail/completed_membership.hpp"
#include "bmssp_oracle.hpp"
#include "run_task11_reference.hpp"
#include <future>
#include <random>
#include <string_view>
using namespace bmssp;
namespace {
std::size_t traces = 0, states = 0;
struct Cleanup {
    ~Cleanup() {
        run_test::observer = {};
        run_test::pull_fault = {};
        run_test::child_fault = {};
    }
};
Graph chain(std::size_t n) {
    std::vector<ExternalVertexId> ids;
    std::vector<InputEdge> edges;
    for (std::size_t i = 0; i < n; ++i) {
        ids.push_back(static_cast<ExternalVertexId>(i));
        if (i)
            edges.push_back({static_cast<EdgeId>(i), ids[i - 1], ids[i], 0});
    }
    return {ids, edges};
}
auto counters(const BMSSPDiagnostics &d) {
    return std::vector<std::size_t>{d.recursive_calls,
                                    d.base_calls,
                                    d.max_recursion_depth,
                                    d.pivot_calls,
                                    d.pivot_edge_scans,
                                    d.pivots_selected,
                                    d.pivot_early_returns,
                                    d.relaxed_edges,
                                    d.equality_relaxations,
                                    d.label_updates,
                                    d.completed_vertex_events,
                                    d.completed_vertices,
                                    d.original_reachable_vertices,
                                    d.label_nodes_created,
                                    d.transformed_vertices,
                                    d.transformed_edges,
                                    d.k,
                                    d.t,
                                    d.root_level,
                                    d.frontier.initializations,
                                    d.frontier.discards,
                                    d.frontier.inserts,
                                    d.frontier.pulls,
                                    d.frontier.batches,
                                    d.frontier.splits,
                                    d.frontier.selection_work,
                                    d.frontier.pulled_keys,
                                    d.frontier.peak_keys};
}
void labels_equal(const std::vector<SymbolicLabel> &a, const std::vector<SymbolicLabel> &b) {
    CHECK(a.size() == b.size());
    for (std::size_t v = 0; v < a.size(); ++v)
        CHECK(independent::compare(independent::view(a[v]), independent::view(b[v])) == 0);
}
void verify(const Graph &g, ExternalVertexId source, std::size_t k, std::size_t t,
            std::size_t level, SymbolicLabel bound = {}, bool seed = false) {
    Cleanup cleanup;
    const auto s = g.vertex_index(source);
    const auto truth = independent::truth(g, s);
    std::vector<BoundedTrace> actual, frozen;
    std::vector<run_test::State> astate, fstate;
    BMSSPOptions options;
    options.validate_frontier_operations = true;
    options.observer = [&](const BoundedTrace &e) {
        independent::bounded_contract(e, truth);
        actual.push_back(e);
    };
    BMSSPWorkspace w(g, source, k, t, options);
    if (seed)
        for (const auto &edge : g.outgoing(s))
            (void)w.relax(edge);
    const auto initial_labels = w.labels();
    const auto initial_counters = w.diagnostics();
    run_test::observer = [&](const run_test::State &e) { astate.push_back(e); };
    const auto result = w.run(level, bound, {s});
    BMSSPOptions reference_options;
    reference_options.validate_frontier_operations = true;
    reference_options.observer = [&](const BoundedTrace &e) {
        independent::bounded_contract(e, truth);
        frozen.push_back(e);
    };
    task11_reference::FrozenWorkspace ref(g, source, k, t, reference_options);
    ref.seed_labels(initial_labels);
    ref.diagnostics() = initial_counters;
    run_test::observer = [&](const run_test::State &e) { fstate.push_back(e); };
    const auto expected = ref.run(level, bound, {s});
    CHECK(result.bound == expected.bound);
    CHECK(result.completed == expected.completed);
    labels_equal(w.labels(), ref.labels());
    CHECK(counters(w.diagnostics()) == counters(ref.diagnostics()));
    CHECK(actual.size() == frozen.size());
    for (std::size_t i = 0; i < actual.size(); ++i) {
        const auto &a = actual[i], &b = frozen[i];
        CHECK(a.level == b.level);
        CHECK(a.depth == b.depth);
        CHECK(a.input_bound == b.input_bound);
        CHECK(a.frontier == b.frontier);
        CHECK(a.result.bound == b.result.bound);
        CHECK(a.result.completed == b.result.completed);
        labels_equal(a.before, b.before);
        labels_equal(a.after, b.after);
    }
    CHECK(astate.size() == fstate.size());
    for (std::size_t i = 0; i < astate.size(); ++i) {
        const auto &a = astate[i], &b = fstate[i];
        CHECK(a.level == b.level);
        CHECK(a.depth == b.depth);
        CHECK(a.phase == b.phase);
        CHECK(a.complete == b.complete);
        CHECK(a.members == b.members);
        CHECK(a.boundary == b.boundary);
        auto sorted = a.complete;
        std::sort(sorted.begin(), sorted.end());
        CHECK(sorted == a.members);
    }
    traces += actual.size();
    states += astate.size();
}
template <class Pool> void ownership() {
    Pool pool;
    const void *identity = nullptr;
    {
        auto parent = pool.acquire(0, 4096);
        identity = parent.identity();
        CHECK(parent.insert(0));
        CHECK(parent.insert(4095));
        CHECK(!parent.insert(0));
        {
            auto child = pool.acquire(1, 4096);
            CHECK(!child.contains(0));
            CHECK(child.insert(0));
            CHECK(!child.contains(4095));
            std::vector<typename Pool::Lease> deep;
            for (std::size_t d = 2; d < 70; ++d) {
                deep.push_back(pool.acquire(d, 4096));
                CHECK(deep.back().insert(static_cast<VertexIndex>(d)));
                CHECK(parent.contains(0));
                CHECK(parent.contains(4095));
                CHECK(parent.identity() == identity);
            }
            test::throws<std::logic_error>([&] { (void)pool.acquire(0, 4096); });
        }
        {
            auto sibling = pool.acquire(1, 4096);
            CHECK(!sibling.contains(0));
            CHECK(sibling.size() == 0);
            CHECK(parent.contains(0));
        }
        CHECK(pool.active_count() == 1);
        test::throws<std::out_of_range>([&] { (void)parent.contains(4096); });
        test::throws<std::out_of_range>([&] { (void)parent.insert(4096); });
    }
    CHECK(pool.active_count() == 0);
    CHECK(pool.retained_bytes() > 0);
    Pool copy = pool;
    CHECK(copy.active_count() == 0);
    CHECK(copy.retained_bytes() == 0);
    Pool moved = std::move(pool);
    {
        auto fresh = moved.acquire(0, 4096);
        CHECK(fresh.identity() == identity);
        CHECK(!fresh.contains(0));
    }
}
template <template <class> class Storage, std::size_t Small> void epochs() {
    detail::CompletedFrames<Storage, Small, std::uint8_t> pool;
    for (std::size_t i = 0; i < 800; ++i) {
        auto parent = pool.acquire(0, 1300);
        for (VertexIndex v : {0U, 511U, 512U, 1023U, 1024U, 1299U, 1U, 513U, 1025U}) {
            CHECK(!parent.contains(v));
            CHECK(parent.insert(v));
            CHECK(!parent.insert(v));
        }
        auto child = pool.acquire(1, 1300);
        CHECK(!child.contains(511));
        CHECK(child.insert(511));
        CHECK(parent.contains(1299));
    }
}
void intended_failure(BMSSPWorkspace &w, std::string_view prefix, bool &fired) {
    bool caught = false;
    try {
        (void)w.run(3, {}, {0});
    } catch (const std::logic_error &e) {
        CHECK(std::string_view(e.what()).starts_with(prefix));
        caught = true;
    }
    CHECK(fired);
    CHECK(caught);
    run_test::pull_fault = {};
    run_test::child_fault = {};
    w.reset(0);
    const auto clean = w.run(3, {}, {0});
    CHECK(!clean.bound.finite());
    CHECK(clean.completed.size() == 80);
}
} // namespace
int main() {
    test::run("stable_slot_parent_child_siblings_growth_copy", [] {
        ownership<detail::DenseCompletedFrames>();
        ownership<detail::AdaptiveCompletedFrames>();
        epochs<detail::DenseCompletedStorage, 0>();
        epochs<detail::PagedCompletedStorage, 8>();
    });
    test::run("slot_creation_and_dense_paged_promotion_failure", [] {
        for (std::size_t point = 0; point < 2; ++point) {
            detail::AdaptiveCompletedFrames p;
            bool failed = false;
            try {
                allocation_probe::FailAfter fail(point);
                (void)p.acquire(0, 20000);
            } catch (const std::bad_alloc &) {
                failed = true;
            }
            CHECK(failed);
            CHECK(p.active_count() == 0);
            auto retry = p.acquire(0, 20000);
            CHECK(retry.insert(1));
        }
        {
            detail::DenseCompletedFrames p;
            auto lease = p.acquire(0, 20000);
            test::throws<std::bad_alloc>([&] {
                allocation_probe::FailAfter fail(0);
                (void)lease.insert(100);
            });
            CHECK(lease.size() == 0);
            CHECK(!lease.contains(100));
            CHECK(lease.insert(100));
        }
        for (std::size_t point = 0; point < 3; ++point) {
            detail::AdaptiveCompletedFrames p;
            auto lease = p.acquire(0, 20000);
            for (VertexIndex v = 0; v < 8; ++v)
                CHECK(lease.insert(v));
            CHECK(!lease.promoted());
            test::throws<std::bad_alloc>([&] {
                allocation_probe::FailAfter fail(point);
                (void)lease.insert(9000);
            });
            CHECK(lease.size() == 8);
            for (VertexIndex v = 0; v < 8; ++v)
                CHECK(lease.contains(v));
            CHECK(!lease.contains(9000));
            CHECK(lease.insert(9000));
            CHECK(lease.promoted());
        }
    });
    test::run("frozen_Task11_partial_full_zero_cycles_multigraphs", [] {
        for (auto k : {1U, 2U, 5U})
            for (auto level : {0U, 1U, 3U})
                verify(chain(40), 0, k, 2, level);
        verify(chain(25), 0, 1, 1, 10);
        verify(chain(40), 0, 2, 2, 3, {}, true);
        verify(chain(1), 0, 1, 1, 0);
        verify(chain(40), 0, 2, 2, 3, SymbolicLabel::root(0, 1));
        const auto g = reduce_degree(Graph({5000000000LL, 6000000000LL, 7000000000LL, 8000000000LL},
                                           {{0, 5000000000LL, 6000000000LL, 0},
                                            {1, 5000000000LL, 6000000000LL, 0},
                                            {2, 6000000000LL, 5000000000LL, 0},
                                            {3, 6000000000LL, 7000000000LL, 1}}));
        for (VertexIndex s = 0; s < g.graph.vertex_count(); ++s)
            verify(g.graph, g.graph.external_id(s), 2, 2, 4);
        std::mt19937 random(12025);
        for (std::size_t round = 0; round < 25; ++round) {
            std::vector<ExternalVertexId> ids;
            std::vector<InputEdge> edges;
            for (ExternalVertexId v = 0; v < 8; ++v)
                ids.push_back(v);
            for (EdgeId e = 0; e < 24; ++e)
                edges.push_back({e, static_cast<ExternalVertexId>(random() % 8),
                                 static_cast<ExternalVertexId>(random() % 8),
                                 static_cast<double>(random() % 5) / 4});
            const auto reduced = reduce_degree(Graph(ids, edges));
            for (VertexIndex s = 0; s < 2; ++s) {
                auto v = reduced.representative[s];
                verify(reduced.graph, reduced.graph.external_id(v), 2, 2, 4);
            }
        }
        CHECK(traces > 1000);
        CHECK(states > 1000);
        std::cout << "frozen recursive traces=" << traces << " membership states=" << states
                  << "\n";
    });
    test::run("intentional_overlap_stale_progress_boundary_faults", [] {
        Cleanup cleanup;
        const auto g = chain(80);
        {
            BMSSPWorkspace w(g, 0, 2, 2);
            bool fired = false;
            run_test::child_fault = [&](std::size_t depth, const auto &, auto &child) {
                if (depth == 0 && !fired && !child.completed.empty()) {
                    child.completed.push_back(child.completed.front());
                    fired = true;
                }
            };
            intended_failure(w, "completed child sets overlap", fired);
        }
        {
            BMSSPWorkspace w(g, 0, 2, 2);
            bool fired = false;
            run_test::pull_fault = [&](std::size_t depth, const auto &complete, auto &pull) {
                if (depth == 0 && !fired && !complete.empty() && !pull.entries.empty()) {
                    pull.entries.front().key = complete.front();
                    fired = true;
                }
            };
            intended_failure(w, "stale completed frontier entry", fired);
        }
        {
            BMSSPWorkspace w(g, 0, 2, 2);
            bool fired = false;
            run_test::child_fault = [&](std::size_t depth, const auto &, auto &child) {
                if (depth == 0 && !fired) {
                    child.completed.clear();
                    fired = true;
                }
            };
            intended_failure(w, "recursive call made no progress", fired);
        }
        {
            BMSSPWorkspace w(g, 0, 2, 2);
            bool fired = false;
            run_test::child_fault = [&](std::size_t depth, const auto &complete, auto &child) {
                if (depth == 0 && !fired && !complete.empty()) {
                    child.bound = SymbolicLabel::root(0);
                    fired = true;
                }
            };
            intended_failure(w, "nonmonotone recursive boundary", fired);
        }
    });
    test::run("nested_allocation_unwind_reset_repeated_and_copy", [] {
        const auto g = chain(200);
        std::size_t failures = 0, nested = 0;
        for (std::size_t point : {0U, 2U, 6U, 16U, 32U, 64U, 128U, 256U}) {
            BMSSPWorkspace w(g, 0, 2, 2);
            try {
                allocation_probe::FailAfter fail(point);
                (void)w.run(4, {}, {0});
            } catch (const std::bad_alloc &) {
                ++failures;
                nested += w.diagnostics().max_recursion_depth >= 2;
            }
            w.reset(0);
            CHECK(w.run(4, {}, {0}).completed.size() == 200);
        }
        CHECK(failures >= 4);
        CHECK(nested > 0);
        BMSSPWorkspace w(g, 0, 2, 2);
        auto saved = w.run(4, {}, {0});
        const auto keys = saved.completed;
        for (std::size_t i = 0; i < 20; ++i) {
            w.reset(0);
            CHECK(w.run(4, {}, {0}).completed == keys);
            CHECK(saved.completed == keys);
        }
        BMSSPWorkspace copied = w;
        copied.reset(0);
        CHECK(copied.run(4, {}, {0}).completed == keys);
        test::throws<std::invalid_argument>([&] { (void)w.run(1, {}, {999}); });
        w.reset(0);
        CHECK(w.run(4, {}, {0}).completed == keys);
    });
    test::run("independent_concurrent_workspaces", [] {
        const auto g = chain(300);
        std::array<std::future<void>, 4> jobs;
        for (auto &job : jobs)
            job = std::async(std::launch::async, [&] {
                for (std::size_t i = 0; i < 10; ++i) {
                    BMSSPWorkspace w(g, 0, 2, 2);
                    CHECK(w.run(5, {}, {0}).completed.size() == 300);
                }
            });
        for (auto &job : jobs)
            job.get();
    });
    return test::finish();
}
