// SPDX-License-Identifier: Apache-2.0
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include <bit>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
using namespace bmssp;
int main(int argc, char **argv) {
    try {
        if (argc != 4)
            throw std::invalid_argument("graph sources enabled");
        std::ifstream input(argv[1]), sources(argv[2]);
        input.exceptions(std::ios::failbit | std::ios::badbit);
        std::size_t n, m;
        input >> n >> m;
        std::vector<ExternalVertexId> ids(n);
        for (auto &id : ids)
            input >> id;
        std::vector<InputEdge> edges(m);
        for (auto &e : edges)
            input >> e.id >> e.from >> e.to >> e.weight;
        const Graph graph(ids, edges);
        const BMSSP2025Engine engine(graph);
        BMSSPOptions options;
        options.profile = std::string(argv[3]) == "1";
        ExternalVertexId source;
        bool first = true;
        std::cout << "{\"queries\":[";
        while (sources >> source) {
            (void)engine.solve(source, options);
            const auto truth = reference_dijkstra(graph, source);
            const auto start = std::chrono::steady_clock::now();
            auto result = engine.solve(source, options);
            const double elapsed =
                std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            if (result.shortest_paths.distances != truth.distances)
                throw std::logic_error("distance mismatch");
            const auto &d = result.diagnostics;
            std::uint64_t hash = 14695981039346656037ULL;
            auto consume = [&](std::uint64_t value) {
                hash ^= value;
                hash *= 1099511628211ULL;
            };
            for (auto value : result.shortest_paths.distances)
                consume(std::bit_cast<std::uint64_t>(value));
            for (auto value : result.shortest_paths.predecessor_edges) {
                consume(value.has_value());
                if (value)
                    consume(*value);
            }
            if (!first)
                std::cout << ',';
            first = false;
            std::cout << "{\"source\":" << source
                      << ",\"profile_enabled\":" << (options.profile ? "true" : "false")
                      << ",\"seconds\":" << elapsed << ",\"native_seconds\":" << d.query_seconds
                      << ",\"return_and_workspace_teardown_seconds\":" << elapsed - d.query_seconds
                      << ",\"fingerprint\":" << hash << ",\"work\":[" << d.recursive_calls << ','
                      << d.base_calls << ',' << d.pivot_calls << ',' << d.relaxed_edges << ','
                      << d.equality_relaxations << ',' << d.label_updates << ','
                      << d.label_nodes_created << ',' << d.label_nodes_materialized
                      << "],\"profile_calls\":[";
            for (std::size_t i = 0; i < QueryProfile::size; ++i) {
                if (i)
                    std::cout << ',';
                std::cout << d.profile.calls[i];
                if (!options.profile && d.profile.calls[i] != 0)
                    throw std::logic_error("disabled profile counted");
                if (d.profile.inclusive[i] < 0 || d.profile.exclusive[i] < 0)
                    throw std::logic_error("negative duration");
            }
            std::cout << "],\"inclusive\":[";
            for (std::size_t i = 0; i < QueryProfile::size; ++i) {
                if (i)
                    std::cout << ',';
                std::cout << d.profile.inclusive[i];
            }
            std::cout << "],\"exclusive\":[";
            for (std::size_t i = 0; i < QueryProfile::size; ++i) {
                if (i)
                    std::cout << ',';
                std::cout << d.profile.exclusive[i];
            }
            std::cout << "]}";
        }
        if (first || !sources.eof())
            throw std::invalid_argument("sources malformed");
        std::cout << "]}\n";
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
