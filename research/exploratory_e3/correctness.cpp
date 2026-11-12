// SPDX-License-Identifier: Apache-2.0
// EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION: no Task15 execution or acceptance semantics.
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include <bit>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>
#include <sys/resource.h>
#include <unistd.h>
using namespace bmssp;
namespace {
using Clock = std::chrono::steady_clock;
double elapsed(Clock::time_point start) {
    return std::chrono::duration<double>(Clock::now() - start).count();
}
std::uint64_t fingerprint(const ShortestPathResult &r) {
    std::uint64_t hash = 14695981039346656037ULL;
    for (const auto d : r.distances) { hash ^= std::bit_cast<std::uint64_t>(d); hash *= 1099511628211ULL; }
    for (const auto &p : r.predecessor_edges) { hash ^= p.value_or(UINT64_MAX); hash *= 1099511628211ULL; }
    return hash;
}
void diagnostics(const BMSSPDiagnostics &d) {
    std::cout << ",\"work\":[" << d.recursive_calls << ',' << d.base_calls << ',' << d.pivot_calls
              << ',' << d.pivot_edge_scans << ',' << d.pivots_selected << ',' << d.relaxed_edges
              << ',' << d.equality_relaxations << ',' << d.label_updates << ',' << d.label_nodes_created
              << ',' << d.label_nodes_materialized << ',' << d.frontier.pulls << ',' << d.frontier.batches
              << ',' << d.frontier.splits << ',' << d.frontier.discards << ']';
    std::cout << ",\"profile_inclusive\":[";
    for (std::size_t i=0;i<QueryProfile::size;++i) { if(i)std::cout<<','; std::cout<<d.profile.inclusive[i]; }
    std::cout << "],\"profile_exclusive\":[";
    for (std::size_t i=0;i<QueryProfile::size;++i) { if(i)std::cout<<','; std::cout<<d.profile.exclusive[i]; }
    std::cout << "],\"profile_calls\":[";
    for (std::size_t i=0;i<QueryProfile::size;++i) { if(i)std::cout<<','; std::cout<<d.profile.calls[i]; }
    std::cout<<']';
}
void validate_paths(const Graph &graph,const ShortestPathResult &r,std::size_t &reachable,std::size_t &unreachable_count) {
    for(VertexIndex v=0;v<graph.vertex_count();++v) {
        const auto path=reconstruct_path(graph,r,graph.external_id(v));
        if(path.status==PathStatus::unreachable) { ++unreachable_count; continue; }
        ++reachable;
        if(path.vertices.empty() || path.vertices.front()!=graph.external_id(r.source) || path.vertices.back()!=graph.external_id(v) || path.edges.size()+1!=path.vertices.size()) throw std::logic_error("path endpoints");
        Distance sum=0;
        for(std::size_t i=0;i<path.edges.size();++i) {
            const auto &e=graph.edge(path.edges[i]);
            if(graph.external_id(e.from)!=path.vertices[i] || graph.external_id(e.to)!=path.vertices[i+1])throw std::logic_error("directed path orientation");
            sum=checked_distance_add(sum,e.weight);
        }
        if(std::bit_cast<std::uint64_t>(sum)!=std::bit_cast<std::uint64_t>(r.distances[v]))throw std::logic_error("path distance bits");
    }
}
}
int main(int argc,char **argv) {
    try {
        if(argc!=8)throw std::invalid_argument("mode graph positions algorithm repetitions warmups dump-or-seconds");
        const std::string mode=argv[1],algorithm=argv[4];
        const auto repetitions=std::stoull(argv[5]),warmups=std::stoull(argv[6]);
        if(mode!="bench" && mode!="profile" && mode!="check" && mode!="spin")throw std::invalid_argument("mode");
        if(algorithm!="bmssp" && algorithm!="dijkstra")throw std::invalid_argument("algorithm");
        std::cout << std::setprecision(17) << std::unitbuf;
        std::ifstream input(argv[2]),source_file(argv[3]);input.exceptions(std::ios::failbit|std::ios::badbit);
        if(!source_file)throw std::invalid_argument("source file");
        std::size_t n,m;input>>n>>m;std::vector<ExternalVertexId> ids(n);for(auto &id:ids)input>>id;
        std::vector<InputEdge> edges(m);for(auto &e:edges)input>>e.id>>e.from>>e.to>>e.weight;
        const auto graph_start=Clock::now();const Graph graph(std::move(ids),std::move(edges));const auto graph_seconds=elapsed(graph_start);
        std::vector<std::pair<std::size_t,ExternalVertexId>> sources;std::size_t position;ExternalVertexId id;
        while(source_file>>position>>id)sources.emplace_back(position,id);
        if(!source_file.eof()||sources.empty())throw std::invalid_argument("source records");
        const auto prep=Clock::now();std::unique_ptr<BMSSP2025Engine> engine;
        if(algorithm=="bmssp"||mode=="check")engine=std::make_unique<BMSSP2025Engine>(graph);
        const auto preparation=elapsed(prep);
        std::cout<<"{\"label\":\"EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION\",\"kind\":\"header\",\"pid\":"<<getpid()<<",\"vertices\":"<<n<<",\"edges\":"<<m<<",\"graph_construction_seconds\":"<<graph_seconds<<",\"preprocessing_seconds\":"<<preparation<<",\"algorithm\":\""<<algorithm<<"\",\"mode\":\""<<mode<<"\"}\n";
        if(mode=="spin") {
            const auto start=Clock::now();std::size_t count=0;std::uint64_t sink=0;
            while(elapsed(start)<std::stod(argv[7])) { auto r=engine->solve(sources[count%sources.size()].second);sink^=fingerprint(r.shortest_paths);++count; }
            std::cout<<"{\"label\":\"EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION\",\"kind\":\"spin\",\"queries\":"<<count<<",\"sink\":"<<sink<<"}\n";
        } else if(mode=="check") {
            std::ofstream dump(argv[7],std::ios::binary);dump.exceptions(std::ios::failbit|std::ios::badbit);
            std::size_t mismatch_total=0;
            for(const auto &[pos,source]:sources) {
                const auto actual=engine->solve(source);const auto reference=reference_dijkstra(graph,source);
                std::size_t mismatches=0,reachable=0,unreachable_count=0;
                std::cout<<"{\"label\":\"EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION\",\"kind\":\"correctness\",\"position\":"<<pos<<",\"source\":"<<source<<",\"mismatches\":[";
                for(VertexIndex v=0;v<n;++v) {
                    const auto a=std::bit_cast<std::uint64_t>(actual.shortest_paths.distances[v]),b=std::bit_cast<std::uint64_t>(reference.distances[v]);
                    dump.write(reinterpret_cast<const char*>(&a),sizeof(a));dump.write(reinterpret_cast<const char*>(&b),sizeof(b));
                    if(a!=b) { if(mismatches)std::cout<<',';std::cout<<"["<<graph.external_id(v)<<','<<a<<','<<b<<']';++mismatches; }
                }
                validate_paths(graph,actual.shortest_paths,reachable,unreachable_count);validate_paths(graph,reference,reachable,unreachable_count);
                std::cout<<"],\"distance_count\":"<<n<<",\"reachable_paths\":"<<reachable<<",\"unreachable_paths\":"<<unreachable_count<<",\"fingerprint\":"<<fingerprint(actual.shortest_paths);
                diagnostics(actual.diagnostics);std::cout<<"}\n";mismatch_total+=mismatches;
            }
            if(mismatch_total)throw std::logic_error("exact distance mismatches retained");
        } else {
            for(const auto &[pos,source]:sources) {
                const BMSSPOptions options{false,{},mode=="profile"};
                for(std::size_t w=0;w<warmups;++w) { if(engine)(void)engine->solve(source,options);else (void)reference_dijkstra(graph,source); }
                for(std::size_t rep=0;rep<repetitions;++rep) {
                    // Equal outer solve-return boundaries: result destruction/fingerprinting/I/O outside.
                    if(engine) {
                        const auto start=Clock::now();auto r=engine->solve(source,options);const auto seconds=elapsed(start);
                        std::cout<<"{\"label\":\"EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION\",\"kind\":\"sample\",\"position\":"<<pos<<",\"source\":"<<source<<",\"repeat\":"<<rep<<",\"seconds\":"<<seconds<<",\"fingerprint\":"<<fingerprint(r.shortest_paths);diagnostics(r.diagnostics);std::cout<<"}\n";
                    } else {
                        const auto start=Clock::now();auto r=reference_dijkstra(graph,source);const auto seconds=elapsed(start);
                        std::cout<<"{\"label\":\"EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION\",\"kind\":\"sample\",\"position\":"<<pos<<",\"source\":"<<source<<",\"repeat\":"<<rep<<",\"seconds\":"<<seconds<<",\"fingerprint\":"<<fingerprint(r)<<",\"dijkstra_work\":["<<r.diagnostics.settled_vertices<<','<<r.diagnostics.scanned_edges<<','<<r.diagnostics.successful_relaxations<<','<<r.diagnostics.queue_pushes<<"]}\n";
                    }
                }
            }
        }
        rusage usage{};if(getrusage(RUSAGE_SELF,&usage))throw std::runtime_error("rusage");
        std::cout<<"{\"label\":\"EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION\",\"kind\":\"footer\",\"peak_rss_bytes\":"<<usage.ru_maxrss<<"}\n";
        return 0;
    }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
}
