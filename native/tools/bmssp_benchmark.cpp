// SPDX-License-Identifier: Apache-2.0
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include <chrono>
#include <iomanip>
#include <iostream>
#include <random>
using namespace bmssp;
namespace {
Graph fixture(std::string_view family) {
    const std::size_t n = family == "sparse" ? 96 : 256;
    std::vector<ExternalVertexId> ids;
    std::vector<InputEdge> edges;
    EdgeId id = 0;
    for (std::size_t i = 0; i < n; ++i)
        ids.push_back(static_cast<ExternalVertexId>(i));
    if (family == "chain")
        for (std::size_t i = 1; i < n; ++i)
            edges.push_back({id++, ids[i - 1], ids[i], 1});
    else if (family == "star")
        for (std::size_t i = 1; i < n; ++i)
            edges.push_back({id++, ids[0], ids[i], static_cast<double>(i % 17)});
    else {
        std::mt19937_64 rng(2025);
        for (const auto u : ids)
            for (const auto v : ids)
                if (rng() % 100 < 5)
                    edges.push_back({id++, u, v, static_cast<double>(rng() % 101) / 4});
    }
    return {std::move(ids), std::move(edges)};
}
} // namespace
int main() {
    try {
        std::cout << std::setprecision(10);
        std::cout
            << "family,n,m,source,repeat,transformed_n,transformed_m,k,t,level,preprocessing_"
               "seconds,bmssp_query_seconds,dijkstra_seconds,recursive_calls,max_depth,pivot_scans,"
               "pivots,pulls,batches,splits,discards,relaxed_edges,completed,label_nodes\n";
        for (const auto family : {"chain", "star", "sparse"}) {
            const auto graph = fixture(family);
            const BMSSP2025Engine engine(graph);
            for (const auto source : std::vector<ExternalVertexId>{
                     0, static_cast<ExternalVertexId>(graph.vertex_count() / 2),
                     static_cast<ExternalVertexId>(graph.vertex_count() - 1)}) {
                (void)engine.solve(source); // One untimed warmup per source and engine.
                for (std::size_t repeat = 0; repeat < 3; ++repeat) {
                    const auto actual = engine.solve(source);
                    const auto start = std::chrono::steady_clock::now();
                    const auto reference = reference_dijkstra(graph, source);
                    const auto dijkstra =
                        std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
                            .count();
                    if (actual.shortest_paths.distances != reference.distances)
                        throw std::logic_error("benchmark correctness gate failed");
                    const auto &d = actual.diagnostics;
                    std::cout << family << ',' << graph.vertex_count() << ',' << graph.edge_count()
                              << ',' << source << ',' << repeat << ',' << d.transformed_vertices
                              << ',' << d.transformed_edges << ',' << d.k << ',' << d.t << ','
                              << d.root_level << ',' << d.preprocessing_seconds << ','
                              << d.query_seconds << ',' << dijkstra << ',' << d.recursive_calls
                              << ',' << d.max_recursion_depth << ',' << d.pivot_edge_scans << ','
                              << d.pivots_selected << ',' << d.frontier.pulls << ','
                              << d.frontier.batches << ',' << d.frontier.splits << ','
                              << d.frontier.discards << ',' << d.relaxed_edges << ','
                              << d.completed_vertices << ',' << d.label_nodes_created << '\n';
                }
            }
        }
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
