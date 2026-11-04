// SPDX-License-Identifier: Apache-2.0
#include "bmssp/degree_reduction.hpp"
#include "test_support.hpp"
#include <set>
using namespace bmssp;
int main() {
    test::run("empty_and_isolates", [] {
        auto r = reduce_degree(Graph({0, 1, 2}, {}));
        r.validate();
        CHECK(r.graph.vertex_count() == 3);
        CHECK(r.graph.edge_count() == 0);
        CHECK(reduce_degree(Graph({}, {})).graph.vertex_count() == 0);
    });
    test::run("high_degree_parallel_loop", [] {
        std::vector<ExternalVertexId> ids;
        std::vector<InputEdge> edges;
        EdgeId id = 0;
        for (ExternalVertexId v = 0; v < 20; ++v)
            ids.push_back(5000000000LL + v);
        for (std::size_t v = 0; v < ids.size(); ++v) {
            edges.push_back({id++, ids[0], ids[v], static_cast<double>(v)});
            edges.push_back({id++, ids[v], ids[0], 0});
        }
        edges.push_back({id++, ids[0], ids[1], 1});
        Graph g(ids, edges);
        const auto r = reduce_degree(g);
        r.validate();
        CHECK(r.graph.vertex_count() == 2 * g.edge_count());
        std::set<EdgeId> retained;
        for (const auto mapping : r.original_edge)
            if (mapping)
                CHECK(retained.insert(*mapping).second);
        CHECK(retained.size() == g.edge_count());
        for (const auto source : ids) {
            const auto expected = reference_dijkstra(g, source);
            const auto actual = reference_dijkstra(
                r.graph, r.graph.external_id(r.representative[g.vertex_index(source)]));
            for (VertexIndex v = 0; v < g.vertex_count(); ++v)
                CHECK(expected.distances[v] == actual.distances[r.representative[v]]);
        }
    });
    test::run("concrete_path_projection", [] {
        Graph g({10, 20, 30}, {{99, 10, 20, 2}, {100, 20, 30, 3}});
        const auto r = reduce_degree(g);
        const auto d = reference_dijkstra(r.graph, r.graph.external_id(r.representative[0]));
        const auto p = reconstruct_path(r.graph, d, r.graph.external_id(r.representative[2]));
        auto label = SymbolicLabel::root(r.representative[0]);
        for (const auto e : p.edges)
            label = label.extend(r.graph.edge(e));
        const auto projected = project_path(r, label);
        CHECK(projected.vertices == std::vector<ExternalVertexId>({10, 20, 30}));
        CHECK(projected.edges == std::vector<EdgeId>({99, 100}));
        CHECK(projected.distance == 5);
    });
    return test::finish();
}
