// SPDX-License-Identifier: Apache-2.0
#include "../test_support/allocation_tracking.hpp"
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include <chrono>
#include <fstream>
#include <iostream>
#include <sys/resource.h>
using namespace bmssp;
#ifdef BMSSP_STRUCTURAL_PROBE
extern "C" void comparison_probe_begin();
extern "C" const std::size_t *comparison_probe_end();
namespace {
std::size_t validation_calls = 0, validation_allocations = 0, validation_bytes = 0;
std::size_t started_calls = 0, started_bytes = 0;
double validation_seconds = 0;
std::chrono::steady_clock::time_point validation_start;
bool validation_active = false;
} // namespace
extern "C" void validation_probe_enter() {
    if (!allocation_probe::active)
        return;
    validation_active = true;
    started_calls = allocation_probe::active->calls;
    started_bytes = allocation_probe::active->bytes;
    validation_start = std::chrono::steady_clock::now();
}
extern "C" void validation_probe_exit() {
    if (!validation_active)
        return;
    validation_active = false;
    validation_seconds +=
        std::chrono::duration<double>(std::chrono::steady_clock::now() - validation_start).count();
    ++validation_calls;
    validation_allocations += allocation_probe::active->calls - started_calls;
    validation_bytes += allocation_probe::active->bytes - started_bytes;
}
#endif
int main(int argc, char **argv) {
    try {
        if (argc != 3)
            throw std::invalid_argument("Usage: allocation_probe GRAPH.txt SOURCES.txt");
        std::ifstream input(argv[1]), source_file(argv[2]);
        if (!input.is_open() || !source_file.is_open())
            throw std::invalid_argument("Graph and source files must be readable");
        input.exceptions(std::ios::failbit | std::ios::badbit);
        std::size_t n, m;
        input >> n >> m;
        std::vector<ExternalVertexId> ids(n);
        for (auto &id : ids)
            input >> id;
        std::vector<InputEdge> edges(m);
        for (auto &e : edges)
            input >> e.id >> e.from >> e.to >> e.weight;
        const Graph graph(std::move(ids), std::move(edges));
        const BMSSP2025Engine engine(graph);
        ExternalVertexId source;
        std::cout << "{\"label_node_bytes\":" << sizeof(LabelNode) << ",\"queries\":[";
        bool first = true;
        while (source_file >> source) {
            (void)engine.solve(source); // Untallied warmup; this is not a latency benchmark.
            allocation_probe::Counters stats;
            std::size_t labels = 0, materialized = 0;
            const auto expected = reference_dijkstra(graph, source);
            {
                allocation_probe::Track tracking(stats);
#ifdef BMSSP_STRUCTURAL_PROBE
                validation_calls = validation_allocations = validation_bytes = 0;
                validation_seconds = 0;
                comparison_probe_begin();
#endif
                const auto actual = engine.solve(source);
                allocation_probe::active = nullptr;
                if (actual.shortest_paths.distances != expected.distances)
                    throw std::logic_error("Allocation probe oracle mismatch");
                labels = actual.diagnostics.label_nodes_created;
                materialized = actual.diagnostics.label_nodes_materialized;
                allocation_probe::active = &stats;
            } // Includes returned result destruction, as well as workspace teardown.
            allocation_probe::active = nullptr;
            if (!first)
                std::cout << ',';
            first = false;
            std::cout << "{\"source\":" << source << ",\"label_nodes\":" << labels
                      << ",\"label_nodes_materialized\":" << materialized
                      << ",\"new_calls\":" << stats.calls << ",\"requested_bytes\":" << stats.bytes
                      << ",\"delete_calls\":" << stats.frees << ",\"size_bins_pow2_upper_bound\":[";
            for (std::size_t i = 0; i < stats.size_bins.size(); ++i) {
                if (i)
                    std::cout << ',';
                std::cout << stats.size_bins[i];
            }
            std::cout << "]";
#ifdef BMSSP_STRUCTURAL_PROBE
            const auto *comparisons = comparison_probe_end();
            std::cout << ",\"comparison_counters\":[";
            for (std::size_t i = 0; i < 7; ++i) {
                if (i)
                    std::cout << ',';
                std::cout << comparisons[i];
            }
            std::cout << "],\"validation\":{\"calls\":" << validation_calls
                      << ",\"new_calls\":" << validation_allocations
                      << ",\"bytes\":" << validation_bytes
                      << ",\"instrumented_seconds\":" << validation_seconds << '}';
#endif
            std::cout << '}';
        }
        if (first || !source_file.eof())
            throw std::invalid_argument("Empty or malformed source list");
        rusage usage{};
        if (getrusage(RUSAGE_SELF, &usage))
            throw std::runtime_error("getrusage failed");
        std::cout << "],\"peak_rss_platform_units\":" << usage.ru_maxrss << "}\n";
        return 0;
    } catch (const std::exception &error) {
        allocation_probe::active = nullptr;
        std::cerr << error.what() << '\n';
        return 1;
    }
}
