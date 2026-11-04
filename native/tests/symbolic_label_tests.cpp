// SPDX-License-Identifier: Apache-2.0
#include "bmssp/bmssp_2025.hpp"
#include "test_support.hpp"
using namespace bmssp;
int main() {
    test::run("numeric_hops_reverse_vertex_order", [] {
        const auto root = SymbolicLabel::root(0);
        const auto a = root.extend({1, 0, 2, 0}).extend({2, 2, 3, 1});
        const auto b = root.extend({3, 0, 1, 0}).extend({4, 1, 3, 1});
        CHECK(b < a);
        CHECK(root.extend({5, 0, 3, 1}) < b);
        CHECK(b < SymbolicLabel{});
    });
    test::run("parallel_edge_refinement", [] {
        const auto r = SymbolicLabel::root(0);
        CHECK(r.extend({2, 0, 1, 1}) < r.extend({3, 0, 1, 1}));
    });
    test::run("equality_valid_and_zero_cycle_safe", [] {
        Graph g({0, 1}, {{1, 0, 1, 0}, {2, 1, 0, 0}});
        BMSSPWorkspace w(g, 0, 2, 1);
        CHECK(w.relax(g.edge(1)));
        CHECK(w.relax(g.edge(1)));
        CHECK(w.diagnostics().equality_relaxations == 1);
        CHECK(!w.relax(g.edge(2)));
        CHECK(w.labels()[0].node()->hops == 0);
    });
    test::run("immutable_bound_and_same_parent_improvement", [] {
        Graph g({0, 1, 2, 3}, {{1, 0, 2, 0}, {2, 2, 3, 1}, {3, 0, 1, 0}, {4, 1, 3, 1}});
        BMSSPWorkspace w(g, 0, 2, 1);
        CHECK(w.relax(g.edge(1)));
        CHECK(w.relax(g.edge(2)));
        const auto saved = w.labels()[3];
        CHECK(w.relax(g.edge(3)));
        CHECK(w.relax(g.edge(4)));
        CHECK(w.labels()[3] < saved);
        CHECK(saved.node()->parent->vertex == 2);
        w.reset(0);
        CHECK(!w.labels()[3].finite());
        CHECK(saved.finite());
    });
    test::run("bounded_relaxation_rejects_outside", [] {
        Graph g({0, 1}, {{0, 0, 1, 4}});
        BMSSPWorkspace w(g, 0, 1, 1);
        CHECK(!w.relax(g.edge(0), SymbolicLabel::root(0, 3)));
        CHECK(!w.labels()[1].finite());
    });
    test::run("deep_snapshot_destruction", [] {
        auto label = SymbolicLabel::root(0);
        for (VertexIndex v = 1; v <= 20000; ++v)
            label = label.extend({static_cast<EdgeId>(v), v - 1, v, 1});
        CHECK(label.node()->hops == 20000);
        label = {};
        CHECK(!label.finite());
    });
    return test::finish();
}
