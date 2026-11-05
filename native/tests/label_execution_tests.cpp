// SPDX-License-Identifier: Apache-2.0
#include "../test_support/allocation_tracking.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include "bmssp_oracle.hpp"
#include "label_task12_symbolic.hpp"
#include "label_task12_workspace.hpp"
#include <future>
#include <random>
using namespace bmssp;
namespace {
std::size_t compared = 0, traces = 0;
auto work(const BMSSPDiagnostics &d) {
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
void same_labels(const auto &a, const auto &b) {
    CHECK(a.size() == b.size());
    for (std::size_t v = 0; v < a.size(); ++v) {
        auto x = independent::view(a[v]), y = independent::view(b[v]);
        CHECK(x.distance == y.distance);
        CHECK(x.vertices == y.vertices);
        CHECK(x.edges == y.edges);
        CHECK(a[v].finite() == b[v].finite());
        ++compared;
    }
}
void same_work(BMSSPWorkspace &w, task12_workspace::FrozenWorkspace &ref) {
    auto &actual = w.diagnostics();
    CHECK(work(actual) == work(ref.diagnostics()));
    CHECK(actual.label_nodes_materialized == actual.label_updates + 1);
    CHECK(actual.label_nodes_materialized <= actual.label_nodes_created);
    same_labels(w.labels(), ref.labels());
}
void differential(const Graph &g, ExternalVertexId source, std::size_t level,
                  SymbolicLabel bound = {}) {
    const auto truth = independent::truth(g, g.vertex_index(source));
    std::vector<BoundedTrace> a, b;
    BMSSPOptions ao, bo;
    ao.validate_frontier_operations = bo.validate_frontier_operations = true;
    ao.observer = [&](const BoundedTrace &e) {
        independent::bounded_contract(e, truth);
        a.push_back(e);
    };
    bo.observer = [&](const BoundedTrace &e) {
        independent::bounded_contract(e, truth);
        b.push_back(e);
    };
    BMSSPWorkspace w(g, source, 2, 2, ao);
    task12_workspace::FrozenWorkspace ref(g, source, 2, 2, bo);
    const auto s = g.vertex_index(source);
    auto x = w.run(level, bound, {s}), y = ref.run(level, bound, {s});
    CHECK(x.bound == y.bound);
    CHECK(x.completed == y.completed);
    same_work(w, ref);
    CHECK(a.size() == b.size());
    for (std::size_t i = 0; i < a.size(); ++i) {
        CHECK(a[i].level == b[i].level);
        CHECK(a[i].depth == b[i].depth);
        CHECK(a[i].input_bound == b[i].input_bound);
        CHECK(a[i].frontier == b[i].frontier);
        CHECK(a[i].result.bound == b[i].result.bound);
        CHECK(a[i].result.completed == b[i].result.completed);
        same_labels(a[i].before, b[i].before);
        same_labels(a[i].after, b[i].after);
        ++traces;
    }
}
Graph chain(std::size_t n) {
    std::vector<ExternalVertexId> ids;
    std::vector<InputEdge> edges;
    for (std::size_t i = 0; i < n; ++i) {
        ids.push_back(static_cast<ExternalVertexId>(i));
        if (i)
            edges.push_back({static_cast<EdgeId>(i), static_cast<ExternalVertexId>(i - 1),
                             static_cast<ExternalVertexId>(i), 0});
    }
    return {ids, edges};
}
} // namespace
int main() {
    test::run("frozen_symbolic_order_full_paths_and_long_chains", [] {
        std::vector<SymbolicLabel> a{{}, SymbolicLabel::root(0)};
        std::vector<task12_label::SymbolicLabel> b{{}, task12_label::SymbolicLabel::root(0)};
        std::mt19937 gen(132025);
        for (std::size_t i = 0; i < 300; ++i) {
            auto parent = 1 + gen() % (a.size() - 1);
            Edge edge{gen(), a[parent].node()->vertex, gen() % 10,
                      static_cast<double>(gen() % 4) / 4};
            a.push_back(a[parent].extend(edge));
            b.push_back(b[parent].extend(edge));
        }
        for (std::size_t i = 0; i < a.size(); ++i)
            for (std::size_t j = 0; j < a.size(); ++j) {
                CHECK(compare(a[i], a[j]) == compare(b[i], b[j]));
                CHECK(compare(a[i], a[j]) ==
                      independent::compare(independent::view(a[i]), independent::view(a[j])));
            }
        auto x = SymbolicLabel::root(0), y = SymbolicLabel::root(0);
        auto p = task12_label::SymbolicLabel::root(0), q = task12_label::SymbolicLabel::root(0);
        for (VertexIndex v = 1; v <= 12000; ++v) {
            Edge e{std::numeric_limits<EdgeId>::max() - v, v - 1, v, 0};
            x = x.extend(e);
            y = y.extend(e);
            p = p.extend(e);
            q = q.extend(e);
        }
        CHECK(x.node() != y.node());
        CHECK(x == y);
        CHECK(compare(p, q) == 0);
        // Same reversed vertices, refinement differs only at the oldest edge.
        auto low = SymbolicLabel::root(0).extend({1, 0, 1, 0}),
             high = SymbolicLabel::root(0).extend({2, 0, 1, 0});
        for (VertexIndex v = 2; v < 3000; ++v) {
            Edge e{v, v - 1, v, 0};
            low = low.extend(e);
            high = high.extend(e);
        }
        CHECK(low < high);
    });
    test::run("eager_relaxation_differential_all_ties_bounds", [] {
        const auto reduced = reduce_degree(
            Graph({5000000000LL, 6000000000LL, 7000000000LL, 8000000000LL, 9000000000LL},
                  {{std::numeric_limits<EdgeId>::max(), 5000000000LL, 6000000000LL, 0},
                   {0, 5000000000LL, 6000000000LL, 0},
                   {1, 6000000000LL, 5000000000LL, 0},
                   {2, 6000000000LL, 7000000000LL, 1},
                   {3, 5000000000LL, 8000000000LL, 0},
                   {4, 8000000000LL, 7000000000LL, 1}}));
        const auto &g = reduced.graph;
        const auto source = g.external_id(reduced.representative[0]);
        BMSSPWorkspace w(g, source, 2, 2);
        task12_workspace::FrozenWorkspace ref(g, source, 2, 2);
        for (std::size_t round = 0; round < 8; ++round)
            for (VertexIndex v = 0; v < g.vertex_count(); ++v)
                for (const auto &e : g.outgoing(v)) {
                    const auto expected =
                        w.labels()[e.from].finite()
                            ? std::optional<SymbolicLabel>(w.labels()[e.from].extend(e))
                            : std::nullopt;
                    const auto bound = round % 3 == 0 ? SymbolicLabel::root(0, 1) : SymbolicLabel{};
                    CHECK(w.relax(e, bound) == ref.relax(e, bound));
                    same_work(w, ref);
                    if (expected && *expected < bound) {
                        const auto &installed = w.labels()[e.to];
                        CHECK(compare(*expected, installed) >= 0);
                    }
                }
        CHECK(w.diagnostics().equality_relaxations > 0);
        CHECK(w.diagnostics().label_nodes_created > w.diagnostics().label_nodes_materialized);
        auto saved = w.labels()[reduced.representative[2]];
        auto snapshot = independent::view(saved);
        w.reset(source);
        CHECK(independent::view(saved).vertices == snapshot.vertices);
        CHECK(independent::view(saved).edges == snapshot.edges);
        differential(g, source, 4);
        differential(g, source, 4, SymbolicLabel::root(0, 1));
    });
    test::run("borrowed_candidate_long_distinct_ancestry_and_parallel_refinement", [] {
        const auto g = chain(1200);
        BMSSPWorkspace w(g, 0, 2, 2);
        auto a = SymbolicLabel::root(0), b = SymbolicLabel::root(0);
        for (VertexIndex v = 1; v < 1200; ++v) {
            a = a.extend(g.edge(v));
            b = b.extend(g.edge(v));
        }
        const auto parent = a.parent();
        // Defined test-only seeding with fully owned valid symbolic labels, as in
        // an identical pre-relaxed workspace. Distinct equal chains force a long
        // borrowed-versus-published comparison, including the edge pass.
        auto &labels = const_cast<std::vector<SymbolicLabel> &>(w.labels());
        labels[1198] = parent;
        labels[1199] = b;
        const auto before = w.diagnostics().label_nodes_materialized;
        CHECK(w.relax(g.edge(1199)));
        CHECK(w.diagnostics().equality_relaxations == 1);
        CHECK(!w.relax(g.edge(1199), a));
        CHECK(w.diagnostics().label_nodes_materialized == before);
        auto refined = SymbolicLabel::root(0).extend({std::numeric_limits<EdgeId>::max(), 0, 1, 0});
        for (VertexIndex v = 2; v < 1200; ++v)
            refined = refined.extend(g.edge(v));
        labels[1199] = refined;
        const auto saved = labels[1199];
        CHECK(w.relax(g.edge(1199)));
        CHECK(labels[1199] < saved);
        CHECK(labels[1199].node()->parent == parent.node());
        w.reset(0);
        CHECK(saved.node()->hops == 1199);
        CHECK(a == b);
    });
    test::run("checked_errors_even_for_rejectable_candidates", [] {
        const auto g = chain(2);
        BMSSPWorkspace w(g, 0, 2, 2);
        const auto low = SymbolicLabel::root(0, 0);
        for (double weight : {-1.0, std::numeric_limits<double>::quiet_NaN(), unreachable})
            test::throws<std::invalid_argument>([&] { (void)w.relax({0, 0, 1, weight}, low); });
        // Defined test-only mutation of allocated nonconst objects forces otherwise
        // infeasible arithmetic limits; restore before any later comparison/query.
        auto *root = const_cast<LabelNode *>(w.labels()[0].node());
        root->hops = std::numeric_limits<std::size_t>::max();
        test::throws<std::length_error>([&] { (void)w.relax({0, 0, 1, 1}, low); });
        root->hops = 0;
        root->distance = std::numeric_limits<double>::max();
        test::throws<std::overflow_error>(
            [&] { (void)w.relax({0, 0, 1, std::numeric_limits<double>::max()}, low); });
        root->distance = 0;
        test::throws<std::out_of_range>([&] { (void)w.relax({0, 0, 999, 0}); });
        CHECK(!w.relax({0, 0, 999, 0}, low));
        CHECK(!w.relax({0, 1, 999, -1}, low));
        test::throws<std::out_of_range>([&] { (void)w.relax({0, 999, 0, 0}); });
        test::throws<std::invalid_argument>([&] { (void)w.labels()[0].extend({0, 1, 0, 0}); });
        test::throws<std::invalid_argument>([] { (void)SymbolicLabel{}.extend({0, 0, 1, 0}); });
        auto large = SymbolicLabel::root(0, std::numeric_limits<double>::max() / 4)
                         .extend({0, 0, 1, std::numeric_limits<double>::max() / 4});
        CHECK(std::isfinite(large.distance()));
    });
    test::run("no_rejected_arena_growth_accepted_failure_public_extend", [] {
        const auto g = chain(100);
        BMSSPWorkspace w(g, 0, 2, 2);
        for (VertexIndex v = 1; v <= 31; ++v)
            CHECK(w.relax(g.edge(v)));
        CHECK(w.diagnostics().label_nodes_materialized == 32);
        const auto before = w.diagnostics().label_nodes_created;
        test::throws<std::bad_alloc>([&] {
            allocation_probe::FailAfter fail(0);
            (void)w.relax(g.edge(32));
        });
        CHECK(w.diagnostics().label_nodes_created == before);
        CHECK(!w.labels()[32].finite());
        {
            allocation_probe::Counters counts;
            allocation_probe::Track track(counts);
            for (std::size_t i = 0; i < 100; ++i) {
                CHECK(w.relax(g.edge(31)));
                CHECK(w.relax(g.edge(1)));
            }
            CHECK(counts.calls == 0);
        }
        // Public extend always materializes, including an equivalent path at a full slab.
        test::throws<std::bad_alloc>([&] {
            allocation_probe::FailAfter fail(0);
            (void)w.labels()[30].extend(g.edge(31));
        });
        CHECK(w.relax(g.edge(32)));
        CHECK(w.diagnostics().label_nodes_materialized == 33);
        const auto saved = w.labels()[32];
        w.reset(0);
        CHECK(saved.node()->hops == 32);
        const auto bound = SymbolicLabel::root(0, 0);
        {
            allocation_probe::FailAfter fail(0);
            CHECK(!w.relax(g.edge(1), bound));
        }
        CHECK(w.relax(g.edge(1)));
    });
    test::run("Task12_frozen_recursive_BellmanFord_Dijkstra_random", [] {
        std::mt19937 gen(132026);
        for (std::size_t round = 0; round < 30; ++round) {
            std::vector<ExternalVertexId> ids;
            for (ExternalVertexId i = 0; i < 10; ++i)
                ids.push_back(i);
            std::vector<InputEdge> edges;
            for (EdgeId e = 0; e < 30; ++e)
                edges.push_back({e, static_cast<ExternalVertexId>(gen() % 10),
                                 static_cast<ExternalVertexId>(gen() % 10),
                                 static_cast<double>(gen() % 5) / 4});
            const Graph original(ids, edges);
            const auto g = reduce_degree(original);
            for (VertexIndex v = 0; v < 2; ++v) {
                const auto source = g.graph.external_id(g.representative[v]);
                differential(g.graph, source, 4);
                auto result = bmssp_2025(original, original.external_id(v));
                CHECK(result.shortest_paths.distances ==
                      reference_dijkstra(original, original.external_id(v)).distances);
            }
        }
        for (auto level : {0U, 1U, 4U})
            differential(chain(70), 0, level);
        std::cout << "Task12 frozen labels=" << compared << " traces=" << traces << '\n';
        CHECK(traces > 1000);
    });
    test::run("concurrent_workspaces_shared_arena_saved_extensions", [] {
        const auto g = chain(500);
        std::array<std::future<void>, 4> jobs;
        const auto root = SymbolicLabel::root(0);
        for (auto &job : jobs)
            job = std::async(std::launch::async, [&] {
                for (std::size_t i = 0; i < 5; ++i) {
                    BMSSPWorkspace w(g, 0, 2, 2);
                    auto r = w.run(4, {}, {0});
                    CHECK(r.completed.size() == 500);
                    auto snapshot = w.labels()[499];
                    w.reset(0);
                    CHECK(snapshot.node()->hops == 499);
                    auto p = root;
                    for (VertexIndex v = 1; v < 500; ++v)
                        p = p.extend({v, v - 1, v, 0});
                    CHECK(p.node()->hops == 499);
                }
            });
        for (auto &job : jobs)
            job.get();
    });
    return test::finish();
}
