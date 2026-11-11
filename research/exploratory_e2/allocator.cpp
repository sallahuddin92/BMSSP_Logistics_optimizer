// SPDX-License-Identifier: Apache-2.0
// EXPLORATORY_BMSSP_TAIL_ATTRIBUTION: separate intercepted diagnostic executable.
#include "../../native/test_support/allocation_tracking.hpp"
#include "alloc_observer.hpp"
#include "clock.hpp"
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include <bit>
#include <fstream>
#include <iostream>
#include <mach/mach.h>
#include <sys/resource.h>
using namespace bmssp;
namespace {
std::uint64_t resident(){mach_task_basic_info_data_t info{};mach_msg_type_number_t count=MACH_TASK_BASIC_INFO_COUNT;const auto rc=task_info(mach_task_self(),MACH_TASK_BASIC_INFO,reinterpret_cast<task_info_t>(&info),&count);return rc==KERN_SUCCESS?info.resident_size:0;}
template<class T>void array(const char *key,const T &a){std::cout<<",\""<<key<<"\":[";bool first=true;for(auto x:a){if(!first)std::cout<<',';first=false;std::cout<<x;}std::cout<<']';}
}
int main(int argc,char **argv){
 try{
  if(argc!=3)throw std::invalid_argument("graph positions");std::ifstream f(argv[1]),sf(argv[2]);f.exceptions(std::ios::failbit|std::ios::badbit);if(!sf)throw std::invalid_argument("sources");std::size_t n,m;f>>n>>m;std::vector<ExternalVertexId> ids(n);for(auto &id:ids)f>>id;std::vector<InputEdge> edges(m);for(auto &e:edges)f>>e.id>>e.from>>e.to>>e.weight;const Graph graph(std::move(ids),std::move(edges));const BMSSP2025Engine engine(graph);
  e2::prefix("allocator_header");std::cout<<",\"table_capacity\":"<<e2alloc::table_capacity<<",\"event_capacity\":"<<e2alloc::event_capacity<<",\"static_buffer_bytes\":"<<sizeof(e2alloc::table)+sizeof(e2alloc::events)<<"}\n";
  std::size_t position;ExternalVertexId source;
  while(sf>>position>>source){
   (void)engine.solve(source);const auto truth=reference_dijkstra(graph,source);
   for(std::size_t rep=0;rep<3;++rep){
    e2alloc::stats={};++e2alloc::query;e2alloc::phase=0;const auto before=resident();std::uint64_t retained=0,returned=0;BMSSPDiagnostics d;const auto start=e2::endpoint();
    e2alloc::active=true;allocation_probe::observer=e2alloc::observe;
    {
     const auto result=engine.solve(source);const auto end=e2::endpoint();e2alloc::active=false;e2alloc::phase=1;returned=resident();
     for(VertexIndex v=0;v<n;++v)if(std::bit_cast<std::uint64_t>(result.shortest_paths.distances[v])!=std::bit_cast<std::uint64_t>(truth.distances[v]))throw std::logic_error("allocator oracle mismatch");
     d=result.diagnostics;retained=e2alloc::live_bytes;e2::prefix("allocator_query");std::cout<<",\"position\":"<<position<<",\"source\":"<<source<<",\"repeat\":"<<rep<<",\"query_id\":"<<e2alloc::query<<",\"work\":["<<d.relaxed_edges<<','<<d.label_nodes_materialized<<','<<d.frontier.inserts<<']';e2::timing(start,end);
     e2alloc::phase=2;e2alloc::active=true;
    }
    e2alloc::active=false;allocation_probe::observer=nullptr;const auto &s=e2alloc::stats;
    std::cout<<",\"allocations\":"<<s.allocations<<",\"deallocations\":"<<s.frees<<",\"requested_bytes\":"<<s.bytes<<",\"reused_addresses\":"<<s.reused_addresses<<",\"reused_different_size\":"<<s.reused_different_size<<",\"insert_allocations\":"<<s.insert_allocations<<",\"insert_bytes\":"<<s.insert_bytes<<",\"insert_32_allocations\":"<<s.insert_32_allocations<<",\"insert_32_same_scope_frees\":"<<s.insert_32_same_scope_frees<<",\"tracked_live_on_return\":"<<retained<<",\"tracked_live_after_result_destroy\":"<<e2alloc::live_bytes<<",\"peak_tracked_live\":"<<s.peak_live<<",\"rss_before\":"<<before<<",\"rss_return\":"<<returned<<",\"rss_destroy\":"<<resident()<<",\"table_overflow\":"<<s.overflow<<",\"unknown_frees\":"<<s.unknown_frees<<",\"double_live\":"<<s.double_live;
    array("allocation_size_pow2_upper_bins",s.allocation_bins);array("free_size_pow2_upper_bins",s.free_bins);array("insert_size_pow2_upper_bins",s.insert_bins);array("lifetime_in_observed_events_pow2_upper_bins",s.event_lifetime_bins);array("phase_allocations",s.phase_allocations);array("phase_deallocations",s.phase_frees);std::cout<<"}\n";
   }
  }
  if(!sf.eof())throw std::invalid_argument("source parse");
  for(std::size_t i=0;i<e2alloc::event_count;++i){const auto &e=e2alloc::events[i];e2::prefix("allocator_event");std::cout<<",\"address\":"<<e.pointer<<",\"bytes\":"<<e.bytes<<",\"sequence\":"<<e.sequence<<",\"query_id\":"<<e.query<<",\"phase\":"<<e.phase<<",\"insert_depth\":"<<e.depth<<",\"allocation\":"<<(e.allocation?"true":"false")<<"}\n";}
  rusage u{};if(getrusage(RUSAGE_SELF,&u))throw std::runtime_error("rusage");e2::prefix("allocator_footer");std::cout<<",\"event_records\":"<<e2alloc::event_count<<",\"event_records_not_retained\":"<<e2alloc::event_dropped<<",\"peak_rss_bytes\":"<<u.ru_maxrss<<"}\n";
 }catch(const std::exception &e){e2alloc::active=false;allocation_probe::observer=nullptr;std::cerr<<e.what()<<'\n';return 1;}
}
