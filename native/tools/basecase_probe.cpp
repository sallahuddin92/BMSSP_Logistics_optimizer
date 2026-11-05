// SPDX-License-Identifier: Apache-2.0
#include "../test_support/allocation_tracking.hpp"
#include "../test_support/basecase_measurement.hpp"
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include <fstream>
#include <iostream>
#include <sys/resource.h>
namespace basecase_measurement {
thread_local Metrics *active = nullptr;
Allocation snapshot() noexcept {
    const auto *s = allocation_probe::active;
    return s ? Allocation{s->calls, s->bytes, s->frees} : Allocation{};
}
} // namespace basecase_measurement
using namespace bmssp;
int main(int argc, char **argv) {
    try {
        if (argc != 3)
            throw std::invalid_argument("Usage: basecase_probe GRAPH SOURCES");
        std::ifstream input(argv[1]), sources(argv[2]);
        if (!input || !sources)
            throw std::invalid_argument("Unreadable input");
        input.exceptions(std::ios::failbit | std::ios::badbit);
        std::size_t n, m;
        input >> n >> m;
        std::vector<ExternalVertexId> ids(n);
        for (auto &id : ids)
            input >> id;
        std::vector<InputEdge> edges(m);
        for (auto &edge : edges)
            input >> edge.id >> edge.from >> edge.to >> edge.weight;
        const Graph graph(std::move(ids), std::move(edges));
        const BMSSP2025Engine engine(graph);
        std::cout << "{\"queries\":[";
        ExternalVertexId source;
        bool first = true;
        while (sources >> source) {
            (void)engine.solve(source);
            const auto expected = reference_dijkstra(graph, source);
            allocation_probe::Counters allocations;
            basecase_measurement::Metrics metrics;
            double wall = 0;
            std::size_t actual_calls = 0;
            {
                allocation_probe::Track tracking(allocations);
                basecase_measurement::active = &metrics;
                const auto start = std::chrono::steady_clock::now();
                const auto actual = engine.solve(source);
                wall =
                    std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
                basecase_measurement::active = nullptr;
                allocation_probe::active = nullptr;
                if (actual.shortest_paths.distances != expected.distances)
                    throw std::logic_error("Probe distance mismatch");
                actual_calls = actual.diagnostics.base_calls;
                allocation_probe::active = &allocations;
            }
            if (metrics.calls != actual_calls)
                throw std::logic_error("Missing BaseCase probe calls");
            if (!first)
                std::cout << ',';
            first = false;
            std::cout << "{\"source\":" << source << ",\"instrumented_query_seconds\":" << wall;
#define FIELD(name) std::cout << ",\"" #name "\":" << metrics.name
            FIELD(calls);
            FIELD(allocations);
            FIELD(bytes);
            FIELD(frees);
            FIELD(heap_allocations);
            FIELD(heap_bytes);
            FIELD(pushes);
            FIELD(pops);
            FIELD(peak_size);
            FIELD(peak_capacity);
            FIELD(membership_allocations);
            FIELD(membership_bytes);
            FIELD(inserts);
            FIELD(contains);
            FIELD(completed_allocations);
            FIELD(completed_bytes);
            FIELD(completed_total);
            FIELD(completed_max);
            FIELD(stale);
            FIELD(duplicate);
            FIELD(partial);
            FIELD(exhausted);
            FIELD(inclusive_seconds);
            FIELD(setup_seconds);
            FIELD(body_seconds);
            FIELD(teardown_seconds);
#undef FIELD
            std::cout << ",\"completed_histogram\":[";
            for (std::size_t i = 0; i < metrics.completed_histogram.size(); ++i) {
                if (i)
                    std::cout << ',';
                std::cout << metrics.completed_histogram[i];
            }
            std::cout << "]}";
        }
        if (first || !sources.eof())
            throw std::invalid_argument("Empty or malformed sources");
        std::cout << "]}\n";
        return 0;
    } catch (const std::exception &e) {
        allocation_probe::active = nullptr;
        basecase_measurement::active = nullptr;
        std::cerr << e.what() << '\n';
        return 1;
    }
}
