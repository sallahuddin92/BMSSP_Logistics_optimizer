// SPDX-License-Identifier: Apache-2.0
#include "../test_support/allocation_tracking.hpp"
#include "../test_support/pivot_measurement.hpp"
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include <fstream>
#include <iostream>
#include <sys/resource.h>
namespace pivot_measurement {
thread_local Metrics *active = nullptr;
Pause::Pause() : counters_(allocation_probe::active), observer_(allocation_probe::observer) {
    // Preserve the function pointer without nonportable function/object casts.
    allocation_probe::active = nullptr;
    allocation_probe::observer = nullptr;
}
Pause::~Pause() {
    allocation_probe::active = static_cast<allocation_probe::Counters *>(counters_);
    allocation_probe::observer = observer_;
}
void observe(void *pointer, std::size_t bytes, bool allocation) noexcept {
    if (!active)
        return;
    Pause pause;
    try {
        if (allocation) {
            if (active->current == static_cast<std::size_t>(-1))
                return;
            const auto part = active->part;
            const auto i = static_cast<std::size_t>(part);
            const auto id = active->current;
            active->pointers.emplace(pointer, Record{bytes, id, part});
            auto &s = active->parts[i];
            ++s.allocations;
            s.bytes += bytes;
            s.live += bytes;
            s.peak_live = std::max(s.peak_live, s.live);
            active->calls[id].live[i] += bytes;
            active->live += bytes;
            active->peak_live = std::max(active->peak_live, active->live);
        } else if (auto it = active->pointers.find(pointer); it != active->pointers.end()) {
            const auto record = it->second;
            auto &s = active->parts[static_cast<std::size_t>(record.part)];
            ++s.frees;
            s.live -= record.bytes;
            active->live -= record.bytes;
            active->calls[record.call].live[static_cast<std::size_t>(record.part)] -= record.bytes;
            active->pointers.erase(it);
        }
    } catch (...) {
        active->failed = true;
    }
}
// Restore callbacks before Metrics is destroyed, including exceptional unwinding.
class Observation {
    Metrics *previous_metrics_;
    allocation_probe::Observer previous_observer_;

  public:
    explicit Observation(Metrics &metrics)
        : previous_metrics_(active), previous_observer_(allocation_probe::observer) {
        active = &metrics;
        allocation_probe::observer = observe;
    }
    Observation(const Observation &) = delete;
    Observation &operator=(const Observation &) = delete;
    ~Observation() {
        active = previous_metrics_;
        allocation_probe::observer = previous_observer_;
    }
};
} // namespace pivot_measurement
using namespace bmssp;
int main(int argc, char **argv) {
    try {
        if (argc != 3)
            throw std::invalid_argument("Usage: pivot_probe GRAPH SOURCES");
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
            pivot_measurement::Metrics metrics;
            double wall = 0;
            std::size_t actual_calls = 0;
            {
                allocation_probe::Track tracking(allocations);
                pivot_measurement::Observation observation(metrics);
                const auto start = std::chrono::steady_clock::now();
                const auto actual = engine.solve(source);
                wall =
                    std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
                allocation_probe::observer = nullptr;
                pivot_measurement::active = nullptr;
                allocation_probe::active = nullptr;
                if (actual.shortest_paths.distances != expected.distances)
                    throw std::logic_error("Probe distance mismatch");
                actual_calls = actual.diagnostics.pivot_calls;
                allocation_probe::active = &allocations;
            }
            if (metrics.calls.size() != actual_calls || metrics.failed ||
                !metrics.pointers.empty() || metrics.live != 0)
                throw std::logic_error("Invalid FindPivots probe accounting");
            if (!first)
                std::cout << ',';
            first = false;
            std::cout << "{\"source\":" << source << ",\"instrumented_query_seconds\":" << wall;
            std::cout << ",\"scratch_bytes\":" << metrics.scratch_bytes
                      << ",\"peak_tagged_live_bytes\":" << metrics.peak_live << ",\"parts\":[";
            for (std::size_t i = 0; i < pivot_measurement::count; ++i) {
                if (i)
                    std::cout << ',';
                const auto &s = metrics.parts[i];
                std::cout << "{\"allocations\":" << s.allocations << ",\"bytes\":" << s.bytes
                          << ",\"frees\":" << s.frees << ",\"peak_live\":" << s.peak_live
                          << ",\"attempts\":" << s.attempts << ",\"unique\":" << s.unique
                          << ",\"duplicates\":" << s.duplicates
                          << ",\"constructions\":" << s.constructions
                          << ",\"instrumented_operation_seconds\":" << s.seconds << "}";
            }
            std::cout << "],\"calls\":[";
            for (std::size_t i = 0; i < metrics.calls.size(); ++i) {
                if (i)
                    std::cout << ',';
                const auto &c = metrics.calls[i];
                std::cout << "{\"frontier\":" << c.frontier << ",\"pivots\":" << c.pivots
                          << ",\"visited\":" << c.visited
                          << ",\"early\":" << (c.early ? "true" : "false")
                          << ",\"seconds\":" << c.seconds << ",\"retained_requested_bytes\":[";
                for (std::size_t j = 0; j < c.retained.size(); ++j) {
                    if (j)
                        std::cout << ',';
                    std::cout << c.retained[j];
                }
                std::cout << "],\"rounds\":[";
                for (std::size_t j = 0; j < c.rounds.size(); ++j) {
                    if (j)
                        std::cout << ',';
                    const auto &v = c.rounds[j];
                    std::cout << "[" << v.current << "," << v.next << "," << v.visited << "]";
                }
                std::cout << "]}";
            }
            std::cout << "]}";
        }
        if (first || !sources.eof())
            throw std::invalid_argument("Empty or malformed sources");
        std::cout << "]}\n";
        return 0;
    } catch (const std::exception &e) {
        allocation_probe::active = nullptr;
        allocation_probe::observer = nullptr;
        pivot_measurement::active = nullptr;
        std::cerr << e.what() << '\n';
        return 1;
    }
}
