// SPDX-License-Identifier: Apache-2.0
#include "../test_support/allocation_tracking.hpp"
#include "../test_support/pivot_test_observer.hpp"
#include "bmssp/detail/pivot_scratch.hpp"
#include "bmssp_oracle.hpp"
#include "pivot_task10_reference.hpp"
#include <future>
#include <random>
using namespace bmssp;
namespace {
std::size_t comparisons = 0, rounds = 0, early = 0, forest = 0, equal = 0;
void compare(const pivot_test::Event &e, const PivotResult &actual) {
    pivot_test::Task10Reference ref(e.workspace.graph(), e.k, e.before);
    const auto expected = ref.find_pivots(e.bound, e.frontier);
    CHECK(actual.visited == expected.visited);
    CHECK(actual.pivots == expected.pivots);
    CHECK(actual.early == expected.early);
    CHECK(e.rounds.size() == ref.rounds.size());
    CHECK(e.rounds.size() <= e.k);
    if (actual.early)
        CHECK(actual.visited.size() > e.k * e.frontier.size());
    else
        CHECK(e.rounds.size() == e.k);
    for (auto v : actual.pivots)
        CHECK(std::find(e.frontier.begin(), e.frontier.end(), v) != e.frontier.end());
    for (std::size_t i = 0; i < e.rounds.size(); ++i) {
        CHECK(e.rounds[i].current == ref.rounds[i].current);
        CHECK(e.rounds[i].next == ref.rounds[i].next);
        CHECK(e.rounds[i].visited == ref.rounds[i].visited);
    }
    const auto &a = e.workspace.labels();
    for (std::size_t v = 0; v < a.size(); ++v)
        CHECK(independent::compare(independent::view(a[v]), independent::view(ref.labels_[v])) ==
              0);
    const auto &after = e.workspace.diagnostics();
#define SAME(field) CHECK(after.field - e.diagnostics.field == ref.diagnostics_.field)
    SAME(pivot_calls);
    SAME(pivot_edge_scans);
    SAME(relaxed_edges);
    SAME(label_nodes_created);
    SAME(label_updates);
    SAME(equality_relaxations);
    SAME(pivot_early_returns);
    SAME(pivots_selected);
#undef SAME
    ++comparisons;
    rounds += e.rounds.size();
    early += actual.early;
    forest += !actual.early;
    equal += ref.diagnostics_.equality_relaxations;
}
struct Observe {
    Observe() {
        pivot_test::observer = compare;
    }
    ~Observe() {
        pivot_test::observer = {};
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
void run_case(const Graph &g, ExternalVertexId source, std::size_t k, SymbolicLabel bound = {}) {
    BMSSPWorkspace w(g, source, k, 2);
    (void)w.find_pivots(bound, {g.vertex_index(source)});
}
} // namespace
int main() {
    test::run("frozen_Task10_boundaries_cycles_duplicates_sinks", [] {
        Observe observe;
        for (std::size_t k : {1U, 2U, 3U, 8U}) {
            for (std::size_t n : {1U, 2U, 3U, 12U}) {
                run_case(chain(n), 0, k);
                run_case(chain(n), 0, k, SymbolicLabel::root(0, 1));
            }
            const auto reduced = reduce_degree(
                Graph({5000000000LL, 6000000000LL, 7000000000LL, 8000000000LL, 9000000000LL},
                      {{0, 5000000000LL, 6000000000LL, 0},
                       {1, 5000000000LL, 6000000000LL, 0},
                       {2, 6000000000LL, 7000000000LL, 0},
                       {3, 7000000000LL, 5000000000LL, 0},
                       {4, 5000000000LL, 7000000000LL, 1},
                       {5, 6000000000LL, 8000000000LL, 2}}));
            for (VertexIndex s = 0; s < reduced.graph.vertex_count(); ++s)
                run_case(reduced.graph, reduced.graph.external_id(s), k);
        }
        BMSSPWorkspace w(chain(3), 0, 3, 1);
        const auto exact = w.find_pivots({}, {0});
        CHECK(!exact.early);
        CHECK(exact.visited.size() == 3);
        CHECK(exact.pivots == std::vector<VertexIndex>{0});
        w.reset(0);
        CHECK(w.find_pivots({}, {}).visited.empty());
        test::throws<std::invalid_argument>([&] { (void)w.find_pivots({}, {99}); });
        test::throws<std::invalid_argument>([&] { (void)w.find_pivots({}, {0, 0}); });
        BMSSPWorkspace above(chain(4), 0, 8, 1);
        const auto r =
            above.find_pivots(SymbolicLabel::root(0).extend(chain(4).outgoing(0).front()), {0});
        CHECK(r.visited == std::vector<VertexIndex>{0});
        CHECK(above.labels()[1].finite());
        Graph positive({0, 1}, {{0, 0, 1, 5}});
        BMSSPWorkspace strictly_above(positive, 0, 3, 1);
        const auto beyond = strictly_above.find_pivots(SymbolicLabel::root(0, 1), {0});
        CHECK(beyond.visited == std::vector<VertexIndex>{0});
        CHECK(strictly_above.labels()[1].distance() == 5);
        Graph parallel({0, 1, 2}, {{0, 0, 1, 2}, {1, 0, 1, 1}, {2, 1, 2, 0}});
        BMSSPWorkspace duplicates(parallel, 0, 3, 1);
        const auto deduplicated = duplicates.find_pivots({}, {0});
        CHECK(deduplicated.visited == std::vector<VertexIndex>({0, 1, 2}));
        CHECK(duplicates.labels()[1].distance() == 1);
        Graph shared({0, 1, 2, 3}, {{0, 0, 1, 1}, {1, 0, 2, 1}, {2, 1, 3, 2}, {3, 2, 3, 1}});
        BMSSPWorkspace shared_successor(shared, 0, 4, 1);
        const auto shared_result = shared_successor.find_pivots({}, {0});
        CHECK(shared_result.visited == std::vector<VertexIndex>({0, 1, 2, 3}));
        CHECK(shared_successor.labels()[3].distance() == 2);
    });
    test::run("multiple_pivots_and_equality_saved_return_reset", [] {
        Observe observe;
        // Two disjoint branches at an already complete frontier; each subtree has k vertices.
        Graph g(
            {0, 1, 2, 3, 4, 5, 6},
            {{0, 0, 1, 0}, {1, 0, 2, 0}, {2, 1, 3, 0}, {3, 3, 5, 0}, {4, 2, 4, 0}, {5, 4, 6, 0}});
        BMSSPWorkspace w(g, 0, 3, 1);
        for (const auto &edge : g.outgoing(0))
            CHECK(w.relax(edge));
        const auto first = w.find_pivots({}, {1, 2});
        CHECK(!first.early);
        CHECK(first.pivots == std::vector<VertexIndex>({1, 2}));
        const auto saved = first.visited;
        const auto repeated = w.find_pivots({}, {1, 2});
        CHECK(repeated.visited == first.visited);
        CHECK(repeated.pivots == first.pivots);
        for (std::size_t i = 0; i < 350; ++i) {
            w.reset(0);
            for (const auto &edge : g.outgoing(0))
                CHECK(w.relax(edge));
            (void)w.find_pivots({}, {1, 2});
            CHECK(first.visited == saved);
        }
        w.reset(0);
        CHECK(w.relax(g.outgoing(0).front()));
        (void)w.find_pivots({}, {0});
        CHECK(w.diagnostics().equality_relaxations > 0);
    });
    test::run("lazy_failure_recovery_epoch_wrap_and_reentry_guard", [] {
        // Observer allocations are disabled here so injected failures target real code.
        const auto g = chain(70);
        std::size_t failures = 0;
        for (std::size_t point = 0; point < 24; ++point) {
            BMSSPWorkspace w(g, 0, 8, 1);
            const std::vector<VertexIndex> s{0};
            try {
                allocation_probe::FailAfter fail(point);
                (void)w.find_pivots({}, s);
            } catch (const std::bad_alloc &) {
                ++failures;
            }
            w.reset(0);
            const auto result = w.find_pivots({}, s);
            CHECK(result.early);
            CHECK(result.visited.size() == 9);
        }
        CHECK(failures >= 4);
        detail::PivotScratch<std::uint8_t> scratch;
        scratch.visited.resize(4);
        scratch.round.resize(4);
        for (std::size_t i = 0; i < 1024; ++i) {
            detail::PivotScratch<std::uint8_t>::Use use(scratch);
            scratch.visited.begin();
            CHECK(!scratch.visited.contains(1));
            CHECK(scratch.visited.insert(1));
            for (std::size_t j = 0; j < 3; ++j) {
                scratch.round.begin();
                CHECK(scratch.round.insert(1));
                CHECK(!scratch.round.insert(1));
                CHECK(scratch.visited.contains(1));
            }
        }
        {
            detail::PivotScratch<std::uint8_t>::Use use(scratch);
            test::throws<std::logic_error>(
                [&] { detail::PivotScratch<std::uint8_t>::Use nested(scratch); });
        }
        {
            detail::PivotScratch<std::uint8_t>::Use use(scratch);
            CHECK(scratch.visited.contains(1));
        }
        test::throws<std::out_of_range>([&] { (void)scratch.round.insert(4); });
    });
    test::run("actual_FindPivots_reentry_rejected_and_recovered", [] {
        Observe cleanup;
        BMSSPWorkspace w(chain(3), 0, 3, 1);
        bool attempted = false;
        pivot_test::observer = [&](const pivot_test::Event &, const PivotResult &) {
            if (attempted)
                return;
            attempted = true;
            test::throws<std::logic_error>([&] { (void)w.find_pivots({}, {0}); });
        };
        (void)w.find_pivots({}, {0});
        pivot_test::observer = {};
        CHECK(attempted);
        w.reset(0);
        CHECK(w.find_pivots({}, {0}).visited.size() == 3);
    });
    test::run("recursive_random_independent_coverage_and_frozen_rounds", [] {
        Observe observe;
        std::mt19937 rng(11025);
        for (std::size_t round = 0; round < 35; ++round) {
            std::vector<ExternalVertexId> ids;
            std::vector<InputEdge> edges;
            for (ExternalVertexId v = 0; v < 10; ++v)
                ids.push_back(v);
            for (EdgeId id = 0; id < 36; ++id)
                edges.push_back({id, static_cast<ExternalVertexId>(rng() % 10),
                                 static_cast<ExternalVertexId>(rng() % 10),
                                 static_cast<double>(rng() % 5) / 4});
            const auto reduced = reduce_degree(Graph(ids, edges));
            for (VertexIndex s = 0; s < 3; ++s) {
                const auto source = reduced.representative[s];
                const auto truth = independent::truth(reduced.graph, source);
                BMSSPOptions options;
                options.validate_frontier_operations = true;
                options.observer = [&](const BoundedTrace &e) {
                    independent::bounded_contract(e, truth);
                };
                BMSSPWorkspace w(reduced.graph, reduced.graph.external_id(source), 2, 2, options);
                const auto result = w.run(4, {}, {source});
                CHECK(!result.bound.finite());
                for (VertexIndex v = 0; v < truth.size(); ++v)
                    CHECK(independent::compare(independent::view(w.labels()[v]), truth[v]) == 0);
            }
        }
        CHECK(comparisons > 500);
        CHECK(early > 0);
        CHECK(forest > 0);
        CHECK(equal > 0);
        std::cout << "FindPivots comparisons=" << comparisons << " rounds=" << rounds
                  << " early=" << early << " forest=" << forest << " equal=" << equal << "\n";
    });
    test::run("concurrent_independent_workspaces", [] {
        const auto g = chain(300);
        std::array<std::future<void>, 4> jobs;
        for (auto &job : jobs)
            job = std::async(std::launch::async, [&] {
                for (std::size_t i = 0; i < 20; ++i) {
                    BMSSPWorkspace w(g, 0, 2, 2);
                    const auto r = w.run(5, {}, {0});
                    CHECK(r.completed.size() == 300);
                    CHECK(!r.bound.finite());
                }
            });
        for (auto &job : jobs)
            job.get();
    });
    return test::finish();
}
