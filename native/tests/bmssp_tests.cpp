// SPDX-License-Identifier: Apache-2.0
#include "bmssp_oracle.hpp"
#include <future>
#include <random>
#include <sstream>
using namespace bmssp;
namespace {
std::size_t graphs = 0, queries = 0, paths = 0, trace_calls = 0, discarded = 0, projected_paths = 0;
void verify(const Graph &graph, std::uint64_t seed, bool traces) {
    BMSSP2025Engine engine(graph);
    for (VertexIndex s = 0; s < graph.vertex_count(); ++s) {
        try {
            const auto expected = reference_dijkstra(graph, graph.external_id(s));
            BMSSPOptions options;
            options.validate_frontier_operations = true;
            std::vector<independent::Label> exact;
            std::vector<SymbolicLabel> transformed_labels;
            if (traces) {
                exact = independent::truth(engine.reduction().graph,
                                           engine.reduction().representative[s]);
                options.observer = [&](const BoundedTrace &event) {
                    independent::bounded_contract(event, exact);
                    ++trace_calls;
                    if (event.depth == 0)
                        transformed_labels = event.after;
                };
            }
            const auto actual = engine.solve(graph.external_id(s), options);
            ++queries;
            CHECK(actual.diagnostics.recursive_calls > 0);
            discarded += actual.diagnostics.frontier.discards;
            CHECK(actual.shortest_paths.distances == expected.distances);
            const auto original_exact = independent::truth(graph, s);
            for (VertexIndex v = 0; v < graph.vertex_count(); ++v) {
                CHECK(actual.shortest_paths.distances[v] == original_exact[v].distance);
                const auto p = reconstruct_path(graph, actual.shortest_paths, graph.external_id(v));
                ++paths;
                if (traces) {
                    CHECK(transformed_labels.size() == engine.reduction().graph.vertex_count());
                    const auto projected =
                        project_path(engine.reduction(),
                                     transformed_labels[engine.reduction().representative[v]]);
                    CHECK(projected.status == p.status);
                    CHECK(projected.distance == p.distance);
                    if (projected.status == PathStatus::reachable) {
                        CHECK(projected.vertices.front() == graph.external_id(s));
                        CHECK(projected.vertices.back() == graph.external_id(v));
                    }
                    ++projected_paths;
                }
                CHECK((p.status == PathStatus::reachable) == std::isfinite(expected.distances[v]));
                if (p.status == PathStatus::unreachable)
                    continue;
                CHECK(p.vertices.front() == graph.external_id(s));
                CHECK(p.vertices.back() == graph.external_id(v));
                CHECK(p.vertices.size() == p.edges.size() + 1);
                double sum = 0;
                for (std::size_t j = 0; j < p.edges.size(); ++j) {
                    const auto &e = graph.edge(p.edges[j]);
                    CHECK(graph.external_id(e.from) == p.vertices[j]);
                    CHECK(graph.external_id(e.to) == p.vertices[j + 1]);
                    sum += e.weight;
                }
                CHECK(sum == p.distance);
            }
        } catch (const std::exception &error) {
            std::ostringstream out;
            out << "seed=" << seed << " source=" << graph.external_id(s)
                << " n=" << graph.vertex_count() << " m=" << graph.edge_count() << "\nvertices";
            for (VertexIndex v = 0; v < graph.vertex_count(); ++v)
                out << ' ' << graph.external_id(v);
            out << "\nedges(id from to weight)\n";
            for (VertexIndex u = 0; u < graph.vertex_count(); ++u)
                for (const auto &e : graph.outgoing(u))
                    out << e.id << ' ' << graph.external_id(e.from) << ' '
                        << graph.external_id(e.to) << ' ' << e.weight << '\n';
            throw std::runtime_error(out.str() + error.what());
        }
    }
    ++graphs;
}
} // namespace
int main() {
    test::run("manual_graph_families", [] {
        verify(Graph({5000000000LL}, {}), 0, true);
        verify(Graph({std::numeric_limits<ExternalVertexId>::min(),
                      std::numeric_limits<ExternalVertexId>::max()},
                     {{std::numeric_limits<EdgeId>::max(),
                       std::numeric_limits<ExternalVertexId>::min(),
                       std::numeric_limits<ExternalVertexId>::max(), .25}}),
               0, true);
        verify(test::fixture(), 0, true);
        verify(Graph({0, 1, 2, 3, 4}, {{0, 0, 1, 0},
                                       {1, 1, 0, 0},
                                       {2, 1, 2, 0},
                                       {3, 2, 1, 0},
                                       {4, 0, 2, 1},
                                       {5, 2, 3, 2},
                                       {6, 2, 3, 2}}),
               0, true);
        verify(Graph({0, 1, 2, 3, 4},
                     {{0, 0, 1, 1}, {1, 0, 2, 1}, {2, 1, 3, 1}, {3, 2, 3, 1}, {4, 4, 4, 0}}),
               0, true);
    });
    test::run("randomized_three_way_differential", [] {
        for (const std::uint64_t seed : {2025ULL, 17033ULL, 45141ULL}) {
            std::mt19937_64 rng(seed);
            for (const std::size_t n : {2U, 4U, 8U, 16U})
                for (const std::uint64_t density : {0ULL, 10ULL, 40ULL, 100ULL}) {
                    std::vector<ExternalVertexId> ids;
                    for (std::size_t i = 0; i < n; ++i)
                        ids.push_back(5000000000LL + static_cast<ExternalVertexId>(i));
                    std::vector<InputEdge> edges;
                    EdgeId id = 0;
                    for (const auto u : ids)
                        for (const auto v : ids)
                            if (rng() % 100 < density) {
                                edges.push_back({id++, u, v, static_cast<double>(rng() % 33) / 4});
                                if (rng() % 7 == 0)
                                    edges.push_back(
                                        {id++, u, v, static_cast<double>(rng() % 33) / 4});
                            }
                    verify(Graph(ids, edges), seed, n <= 8);
                }
        }
    });
    test::run("large_sparse_chain_and_high_degree", [] {
        std::vector<ExternalVertexId> ids;
        std::vector<InputEdge> chain, star;
        for (ExternalVertexId i = 0; i < 2048; ++i) {
            ids.push_back(i);
            if (i) {
                chain.push_back({static_cast<EdgeId>(i), i - 1, i, 1});
                star.push_back({static_cast<EdgeId>(i), 0, i, static_cast<double>(i % 11)});
            }
        }
        for (const auto *edges : {&chain, &star}) {
            Graph g(ids, *edges);
            const auto actual = bmssp_2025(g, 0);
            CHECK(actual.shortest_paths.distances == reference_dijkstra(g, 0).distances);
            CHECK(reconstruct_path(g, actual.shortest_paths, 2047).status == PathStatus::reachable);
            CHECK(actual.diagnostics.max_recursion_depth >= 2);
        }
    });
    test::run("rounded_binary64_smoke", [] {
        verify(Graph({0, 1, 2, 3}, {{0, 0, 1, .1}, {1, 1, 2, .2}, {2, 0, 2, .3}, {3, 2, 3, .1}}), 0,
               false);
        verify(
            Graph({0, 1, 2, 3}, {{0, 0, 1, 1e16}, {1, 1, 2, 1}, {2, 2, 3, 1}, {3, 0, 3, 1e16 + 2}}),
            0, false);
    });
    test::run("exhaustive_three_vertex_exact_oracle", [] {
        constexpr std::uint64_t absent = std::numeric_limits<std::uint64_t>::max();
        for (std::size_t mask = 0; mask < 729; ++mask) {
            std::vector<InputEdge> edges;
            auto code = mask;
            EdgeId id = 0;
            for (ExternalVertexId u = 0; u < 3; ++u)
                for (ExternalVertexId v = 0; v < 3; ++v)
                    if (u != v) {
                        const auto digit = code % 3;
                        code /= 3;
                        if (digit)
                            edges.push_back({id++, u, v, static_cast<double>(digit - 1)});
                    }
            Graph g({0, 1, 2}, edges);
            BMSSP2025Engine engine(g);
            for (VertexIndex source = 0; source < 3; ++source) {
                std::vector<std::uint64_t> exact(3, absent);
                std::vector<bool> used(3, false);
                std::function<void(VertexIndex, std::uint64_t)> dfs = [&](VertexIndex u,
                                                                          std::uint64_t cost) {
                    exact[u] = std::min(exact[u], cost);
                    used[u] = true;
                    for (const auto &e : g.outgoing(u))
                        if (!used[e.to])
                            dfs(e.to, cost + static_cast<std::uint64_t>(e.weight));
                    used[u] = false;
                };
                dfs(source, 0);
                try {
                    const auto actual = engine.solve(g.external_id(source));
                    for (VertexIndex v = 0; v < 3; ++v) {
                        CHECK(actual.shortest_paths.distances[v] ==
                              (exact[v] == absent ? unreachable : static_cast<double>(exact[v])));
                        (void)reconstruct_path(g, actual.shortest_paths, g.external_id(v));
                    }
                } catch (const std::exception &error) {
                    std::ostringstream out;
                    out << "exhaustive_mask=" << mask << " source=" << source
                        << "\nvertices 0 1 2\nedges(id from to weight)\n";
                    for (const auto &e : edges)
                        out << e.id << ' ' << e.from << ' ' << e.to << ' ' << e.weight << '\n';
                    throw std::runtime_error(out.str() + error.what());
                }
            }
        }
    });
    std::cout << "exhaustive_graphs=729 source_queries=2187 reconstructed_paths=6561\n";
    test::run("invalid_inputs_and_overflow", [] {
        test::throws<std::out_of_range>([] { (void)bmssp_2025(Graph({}, {}), 0); });
        Graph single({0}, {});
        BMSSP2025Engine engine(single);
        test::throws<std::out_of_range>([&] { (void)engine.solve(1); });
        test::throws<std::invalid_argument>([&] { BMSSPWorkspace w(single, 0, 0, 1); });
        BMSSPWorkspace w(single, 0, 1, 1);
        test::throws<std::invalid_argument>([&] { (void)w.run(1000, {}, {0}); });
        const double max = std::numeric_limits<double>::max();
        test::throws<std::overflow_error>(
            [&] { (void)bmssp_2025(Graph({0, 1, 2}, {{0, 0, 1, max}, {1, 1, 2, max}}), 0); });
    });
    test::run("independent_concurrent_queries", [] {
        auto graph = test::fixture();
        const BMSSP2025Engine engine(graph);
        auto a = std::async(std::launch::async, [&] { return engine.solve(0); });
        auto b = std::async(std::launch::async, [&] { return engine.solve(3); });
        CHECK(a.get().shortest_paths.distances == reference_dijkstra(graph, 0).distances);
        CHECK(b.get().shortest_paths.distances == reference_dijkstra(graph, 3).distances);
    });
    test::run("legacy_options_and_opt_in_profile", [] {
        const BMSSP2025Engine engine(test::fixture());
        std::size_t observed = 0;
        BMSSPOptions legacy{false, [&](const BoundedTrace &) { ++observed; }};
        CHECK(!legacy.profile);
        const auto plain = engine.solve(0, legacy);
        CHECK(observed > 0);
        legacy.profile = true;
        const auto profiled = engine.solve(0, legacy);
        CHECK(plain.shortest_paths.distances == profiled.shortest_paths.distances);
        const auto recursion = static_cast<std::size_t>(ProfilePart::recursion);
        CHECK(plain.diagnostics.profile.calls[recursion] == 0);
        CHECK(profiled.diagnostics.profile.calls[recursion] ==
              profiled.diagnostics.recursive_calls);
    });
    test::run("completed_record_retirement_exercised", [] { CHECK(discarded > 0); });
    std::cout << "graphs=" << graphs << " queries=" << queries << " paths=" << paths
              << " bounded_contract_checks=" << trace_calls
              << " stale_records_discarded=" << discarded << " projected_paths=" << projected_paths
              << '\n';
    return test::finish();
}
