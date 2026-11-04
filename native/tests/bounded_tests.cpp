// SPDX-License-Identifier: Apache-2.0
#include "bmssp_oracle.hpp"
using namespace bmssp;
namespace {
Graph chain(std::size_t n, bool zero = false) {
    std::vector<ExternalVertexId> ids;
    std::vector<InputEdge> edges;
    for (std::size_t i = 0; i < n; ++i) {
        ids.push_back(static_cast<ExternalVertexId>(i));
        if (i)
            edges.push_back({static_cast<EdgeId>(i), static_cast<ExternalVertexId>(i - 1),
                             static_cast<ExternalVertexId>(i), zero ? 0.0 : 1.0});
    }
    return {ids, edges};
}
} // namespace
int main() {
    test::run("BaseCase_partial_and_exhausted", [] {
        const auto g = chain(8);
        BMSSPWorkspace w(g, 0, 2, 1);
        const auto a = w.base_case({}, {0});
        CHECK(a.completed == std::vector<VertexIndex>({0, 1}));
        CHECK(a.bound.distance() == 2);
        CHECK(a.bound.node()->vertex == 2);
        w.reset(0);
        const auto bound = SymbolicLabel::root(0, 2);
        const auto b = w.base_case(bound, {0});
        CHECK(b.bound == bound);
        CHECK(b.completed == std::vector<VertexIndex>({0, 1}));
        CHECK(!w.labels()[2].finite());
        test::throws<std::invalid_argument>([&] { (void)w.base_case({}, {}); });
    });
    test::run("BaseCase_symbolic_zero_boundary", [] {
        auto g = chain(8, true);
        BMSSPWorkspace w(g, 0, 2, 1);
        auto r = w.base_case({}, {0});
        CHECK(r.bound.distance() == 0);
        CHECK(r.bound.node()->hops == 2);
        CHECK(r.completed.size() == 2);
    });
    test::run("FindPivots_early_return", [] {
        Graph g({0, 1, 2}, {{0, 0, 1, 0}, {1, 0, 2, 0}});
        BMSSPWorkspace w(g, 0, 1, 1);
        auto r = w.find_pivots({}, {0});
        CHECK(r.early);
        CHECK(r.pivots == std::vector<VertexIndex>({0}));
        CHECK(r.visited.size() == 3);
    });
    test::run("FindPivots_reduction_and_coverage", [] {
        std::vector<ExternalVertexId> ids;
        for (ExternalVertexId i = 0; i < 31; ++i)
            ids.push_back(i);
        std::vector<InputEdge> edges;
        EdgeId id = 0;
        for (ExternalVertexId parent = 0; parent < 7; ++parent) {
            edges.push_back({id++, parent, 2 * parent + 1, 1});
            edges.push_back({id++, parent, 2 * parent + 2, 1});
        }
        ExternalVertexId next = 15;
        for (const ExternalVertexId root : {11, 12}) {
            auto prev = root;
            for (std::size_t j = 0; j < 8; ++j) {
                edges.push_back({id++, prev, next, 1});
                prev = next++;
            }
        }
        Graph g(ids, edges);
        BMSSPWorkspace w(g, 0, 3, 1);
        for (VertexIndex u = 0; u < 7; ++u)
            for (const auto &e : g.outgoing(u))
                CHECK(w.relax(e));
        const auto r = w.find_pivots({}, {7, 8, 9, 10, 11, 12, 13, 14});
        CHECK(!r.early);
        CHECK(r.pivots == std::vector<VertexIndex>({11, 12}));
        CHECK(r.visited.size() <= 24);
        CHECK(r.pivots.size() <= r.visited.size() / 3);
        const auto exact = independent::truth(g, 0);
        std::vector<VertexIndex> s{7, 8, 9, 10, 11, 12, 13, 14};
        for (VertexIndex v = 0; v < g.vertex_count(); ++v)
            if (independent::visits(exact[v], s)) {
                const bool complete =
                    std::find(r.visited.begin(), r.visited.end(), v) != r.visited.end() &&
                    independent::compare(independent::view(w.labels()[v]), exact[v]) == 0;
                CHECK(complete || independent::visits(exact[v], r.pivots));
            }
    });
    test::run("recursive_partial_contracts", [] {
        const auto g = chain(40);
        const auto exact = independent::truth(g, 0);
        std::size_t calls = 0;
        BMSSPOptions options;
        options.validate_frontier_operations = true;
        options.observer = [&](const BoundedTrace &event) {
            independent::bounded_contract(event, exact);
            ++calls;
        };
        BMSSPWorkspace w(g, 0, 2, 2, options);
        const auto result = w.run(1, {}, {0});
        CHECK(result.bound.finite());
        CHECK(result.completed.size() >= 8);
        CHECK(result.completed.size() <= 32);
        CHECK(calls > 1);
        CHECK(w.diagnostics().max_recursion_depth == 1);
    });
    test::run("recursive_full_zero_chain", [] {
        const auto g = chain(32, true);
        const auto exact = independent::truth(g, 0);
        BMSSPOptions options;
        options.validate_frontier_operations = true;
        options.observer = [&](const BoundedTrace &event) {
            independent::bounded_contract(event, exact);
        };
        BMSSPWorkspace w(g, 0, 2, 2, options);
        const auto r = w.run(3, {}, {0});
        CHECK(!r.bound.finite());
        CHECK(r.completed.size() == 32);
        CHECK(w.diagnostics().recursive_calls > 3);
    });
    return test::finish();
}
