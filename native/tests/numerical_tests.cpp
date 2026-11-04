// SPDX-License-Identifier: Apache-2.0
#include "bmssp/bmssp_2025.hpp"
#include "test_support.hpp"
#include <random>
#include <sstream>
using namespace bmssp;
int main() {
    test::run("binary64_magnitude_and_rounding_stress", [] {
        std::mt19937_64 rng(250417033);
        const double weights[] = {0, .1, .2, .3, 1, 1e-16, 1e16, 1e16 + 2};
        for (std::size_t trial = 0; trial < 2000; ++trial) {
            std::vector<InputEdge> edges;
            EdgeId id = 0;
            for (ExternalVertexId u = 0; u < 6; ++u)
                for (ExternalVertexId v = 0; v < 6; ++v)
                    if (rng() % 100 < 35)
                        edges.push_back({id++, u, v, weights[rng() % 8]});
            Graph g({0, 1, 2, 3, 4, 5}, edges);
            for (ExternalVertexId source = 0; source < 3; ++source)
                try {
                    const auto actual = bmssp_2025(g, source);
                    const auto reference = reference_dijkstra(g, source);
                    CHECK(actual.shortest_paths.distances == reference.distances);
                    for (ExternalVertexId target = 0; target < 6; ++target)
                        (void)reconstruct_path(g, actual.shortest_paths, target);
                } catch (const std::exception &error) {
                    std::ostringstream out;
                    out.precision(17);
                    out << "seed=250417033 trial=" << trial << " source=" << source
                        << " n=6\nvertices 0 1 2 3 4 5\nedges(id from to weight)\n";
                    for (const auto &e : edges)
                        out << e.id << ' ' << e.from << ' ' << e.to << ' ' << e.weight << '\n';
                    throw std::runtime_error(out.str() + error.what());
                }
        }
        std::cout << "floating_graphs=2000 source_queries=6000 reconstructed_paths=36000\n";
    });
    return test::finish();
}
