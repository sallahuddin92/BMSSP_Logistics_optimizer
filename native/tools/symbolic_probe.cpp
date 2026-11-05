// SPDX-License-Identifier: Apache-2.0
#include "allocation_tracking.hpp"
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include "symbolic_measurement.hpp"
#include <fstream>
#include <iostream>
#include <sys/resource.h>
using namespace bmssp;
namespace {
allocation_probe::Counters *saved_counts = nullptr;
}
extern "C" void probe_pause() {
    saved_counts = allocation_probe::active;
    allocation_probe::active = nullptr;
}
extern "C" void probe_resume() {
    allocation_probe::active = saved_counts;
}
int main(int argc, char **argv) {
    try {
        if (argc != 3)
            throw std::invalid_argument("graph sources");
        std::ifstream g(argv[1]), sources(argv[2]);
        g.exceptions(std::ios::failbit | std::ios::badbit);
        std::size_t n, m;
        g >> n >> m;
        std::vector<ExternalVertexId> ids(n);
        for (auto &v : ids)
            g >> v;
        std::vector<InputEdge> edges(m);
        for (auto &e : edges)
            g >> e.id >> e.from >> e.to >> e.weight;
        Graph graph(ids, edges);
        BMSSP2025Engine engine(graph);
        ExternalVertexId source;
        bool first = true;
        std::cout << "{\"queries\":[";
        while (sources >> source) {
            (void)engine.solve(source);
            auto truth = reference_dijkstra(graph, source);
            allocation_probe::Counters allocations;
            symbolic_measurement::Metrics metrics;
            double elapsed;
            {
                allocation_probe::Track tracking(allocations);
                symbolic_measurement::active = &metrics;
                auto start = symbolic_measurement::Clock::now();
                {
                    auto result = engine.solve(source);
                    elapsed =
                        std::chrono::duration<double>(symbolic_measurement::Clock::now() - start)
                            .count();
                    allocation_probe::active = nullptr;
                    if (result.shortest_paths.distances != truth.distances)
                        throw std::logic_error("oracle mismatch");
                    allocation_probe::active = &allocations;
                }
                symbolic_measurement::active = nullptr;
            }
            if (!first)
                std::cout << ',';
            first = false;
            std::cout << "{\"source\":" << source << ",\"instrumented_query_seconds\":" << elapsed;
#define FIELD(name) std::cout << ",\"" #name "\":" << metrics.name
            FIELD(calls);
            FIELD(vertex_steps);
            FIELD(edge_steps);
            FIELD(max_walk);
            FIELD(attempts);
            FIELD(strict);
            FIELD(equal);
            FIELD(rejected);
            FIELD(bounded);
            FIELD(allocations);
            FIELD(slabs);
            FIELD(capacity);
            FIELD(copies);
            FIELD(moves);
            FIELD(assigns);
            FIELD(destroys);
            FIELD(arena_copies);
            FIELD(locks);
            FIELD(contended);
            FIELD(current_labels);
            FIELD(ancestry);
            FIELD(allocation_seconds);
            FIELD(lock_seconds);
            FIELD(teardown_seconds);
            FIELD(label_destruction_seconds);
#undef FIELD
            std::cout << ",\"new_calls\":" << allocations.calls
                      << ",\"requested_bytes\":" << allocations.bytes << ",\"categories\":[";
            for (std::size_t i = 0; i < 9; ++i) {
                if (i)
                    std::cout << ',';
                std::cout << metrics.categories[i];
            }
            std::cout << "]}";
        }
        if (first || !sources.eof())
            throw std::invalid_argument("sources malformed");
        rusage usage{};
        if (getrusage(RUSAGE_SELF, &usage))
            throw std::runtime_error("getrusage failed");
        std::cout << "],\"peak_rss_platform_units\":" << usage.ru_maxrss << "}\n";
    } catch (const std::exception &e) {
        allocation_probe::active = nullptr;
        symbolic_measurement::active = nullptr;
        std::cerr << e.what() << '\n';
        return 1;
    }
}
