// SPDX-License-Identifier: Apache-2.0
// Separate diagnostic executable ONLY; never linked into latency workers.
#include "../../native/test_support/allocation_tracking.hpp"
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include <bit>
#include <fstream>
#include <iostream>
#include <sys/resource.h>
using namespace bmssp;
int main(int argc,char **argv) {
    try {
        if(argc!=3)throw std::invalid_argument("graph positions");
        std::ifstream f(argv[1]),s(argv[2]);f.exceptions(std::ios::failbit|std::ios::badbit);
        if(!s)throw std::invalid_argument("sources");
        std::size_t n,m;f>>n>>m;std::vector<ExternalVertexId> ids(n);for(auto &v:ids)f>>v;
        std::vector<InputEdge> edges(m);for(auto &e:edges)f>>e.id>>e.from>>e.to>>e.weight;
        const Graph graph(std::move(ids),std::move(edges));const BMSSP2025Engine engine(graph);
        std::size_t position;ExternalVertexId source;
        while(s>>position>>source) {
            (void)engine.solve(source);const auto truth=reference_dijkstra(graph,source);allocation_probe::Counters stats;BMSSPDiagnostics d;
            {
                allocation_probe::Track tracking(stats);
                const auto actual=engine.solve(source);allocation_probe::active=nullptr;
                for(VertexIndex i=0;i<n;++i)if(std::bit_cast<std::uint64_t>(actual.shortest_paths.distances[i])!=std::bit_cast<std::uint64_t>(truth.distances[i]))throw std::logic_error("diagnostic exact oracle mismatch");
                d=actual.diagnostics;allocation_probe::active=&stats;
            }
            std::cout<<"{\"kind\":\"allocation_diagnostic\",\"position\":"<<position<<",\"source\":"<<source<<",\"new_calls\":"<<stats.calls<<",\"requested_bytes\":"<<stats.bytes<<",\"delete_calls\":"<<stats.frees<<",\"frontier_inserts\":"<<d.frontier.inserts<<",\"label_nodes_materialized\":"<<d.label_nodes_materialized<<"}\n";
        }
        if(!s.eof())throw std::invalid_argument("malformed sources");
        rusage u{};if(getrusage(RUSAGE_SELF,&u))throw std::runtime_error("rusage");std::cout<<"{\"kind\":\"footer\",\"peak_rss_bytes\":"<<u.ru_maxrss<<"}\n";
    }catch(const std::exception &e){allocation_probe::active=nullptr;std::cerr<<e.what()<<'\n';return 1;}
}
