// SPDX-License-Identifier: Apache-2.0
// EXPLORATORY_BMSSP_TAIL_ATTRIBUTION; ordinary worker, no allocator interception.
#include "clock.hpp"
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include <bit>
#include <fstream>
#include <iomanip>
#include <memory>
#include <pthread.h>
#include <string>
#include <type_traits>
#include <sys/resource.h>
#include <unistd.h>
#include <mach-o/dyld.h>
using namespace bmssp;
namespace {
std::uint64_t fingerprint(const ShortestPathResult &r) {
 std::uint64_t h=14695981039346656037ULL;
 for(const auto d:r.distances){h^=std::bit_cast<std::uint64_t>(d);h*=1099511628211ULL;}
 for(const auto &p:r.predecessor_edges){h^=p.value_or(UINT64_MAX);h*=1099511628211ULL;}return h;
}
void work(const BMSSPDiagnostics &d){
 std::cout<<",\"work\":["<<d.recursive_calls<<','<<d.base_calls<<','<<d.pivot_calls<<','<<d.pivot_edge_scans<<','<<d.pivots_selected<<','<<d.relaxed_edges<<','<<d.equality_relaxations<<','<<d.label_updates<<','<<d.label_nodes_created<<','<<d.label_nodes_materialized<<','<<d.frontier.inserts<<','<<d.frontier.pulls<<','<<d.frontier.batches<<','<<d.frontier.splits<<','<<d.frontier.discards<<','<<d.frontier.peak_keys<<"],\"profile_calls\":[";
 for(std::size_t i=0;i<QueryProfile::size;++i){if(i)std::cout<<',';std::cout<<d.profile.calls[i];}std::cout<<']';
}
void characterization(){
 for(const auto id:{e2::wall_clock_id,CLOCK_THREAD_CPUTIME_ID}){
  timespec resolution{};const auto rc=clock_getres(id,&resolution);const auto error=rc==0?0:errno;e2::prefix("clock_resolution");std::cout<<",\"clock_id\":"<<id<<",\"rc\":"<<rc<<",\"errno\":"<<error<<",\"reported_seconds\":"<<resolution.tv_sec<<",\"reported_nanoseconds\":"<<resolution.tv_nsec<<"}\n";
  if(rc)throw std::runtime_error("clock_getres unsupported");
  auto prior=e2::clock(id);if(prior.rc)throw std::runtime_error("initial clock read failed");
  for(std::size_t i=0;i<10000;++i){const auto now=e2::clock(id);e2::prefix("clock_increment");std::cout<<",\"clock_id\":"<<id<<",\"iteration\":"<<i<<",\"delta_ns\":"<<now.ns-prior.ns<<",\"rc\":"<<now.rc<<",\"errno\":"<<now.error<<"}\n";if(now.rc||now.ns<prior.ns)throw std::runtime_error("clock failure/backward step");prior=e2::clock(id);if(prior.rc)throw std::runtime_error("clock read failed");}
 }
 for(std::size_t i=0;i<10000;++i){const auto a=e2::endpoint();const auto b=e2::endpoint();e2::prefix("empty_pair");std::cout<<",\"iteration\":"<<i;e2::timing(a,b);std::cout<<"}\n";if(!e2::good(a)||!e2::good(b)||b.before.ns<a.after.ns||b.cpu.ns<a.cpu.ns)throw std::runtime_error("unreliable endpoint");}
}
}
int main(int argc,char **argv){
 try{
  std::cout<<std::setprecision(17)<<std::unitbuf;
  if(argc==2&&std::string(argv[1])=="clock"){characterization();return 0;}
  if(argc!=10)throw std::invalid_argument("paired|plain graph positions A1|A2|B|D graph_name block repeats warmups unused");
  const std::string mode=argv[1],condition=argv[4],name=argv[5];if(mode!="paired"&&mode!="plain")throw std::invalid_argument("mode");if(condition!="A1"&&condition!="A2"&&condition!="B"&&condition!="D")throw std::invalid_argument("condition");
  const auto block=std::stoull(argv[6]),repeats=std::stoull(argv[7]),warmups=std::stoull(argv[8]);std::uint64_t tid=0;if(pthread_threadid_np(nullptr,&tid))throw std::runtime_error("thread identifier unavailable");
  std::ifstream input(argv[2]),sf(argv[3]);input.exceptions(std::ios::failbit|std::ios::badbit);if(!sf)throw std::invalid_argument("sources");std::size_t n,m;input>>n>>m;std::vector<ExternalVertexId> ids(n);for(auto &id:ids)input>>id;std::vector<InputEdge> edges(m);for(auto &e:edges)input>>e.id>>e.from>>e.to>>e.weight;
  const auto graph0=e2::clock(e2::wall_clock_id);const Graph graph(std::move(ids),std::move(edges));const auto graph1=e2::clock(e2::wall_clock_id);std::unique_ptr<BMSSP2025Engine> engine;if(condition!="D")engine=std::make_unique<BMSSP2025Engine>(graph);const auto prep=e2::clock(e2::wall_clock_id);
  e2::prefix("header");std::cout<<",\"condition\":\""<<condition<<"\",\"graph\":\""<<name<<"\",\"block\":"<<block<<",\"mode\":\""<<mode<<"\",\"pid\":"<<getpid()<<",\"thread_id\":"<<tid<<",\"vertices\":"<<n<<",\"edges\":"<<m<<",\"graph_construction_ns\":"<<graph1.ns-graph0.ns<<",\"preprocessing_ns\":"<<prep.ns-graph1.ns<<",\"image_slide\":"<<_dyld_get_image_vmaddr_slide(0)<<"}\n";
  std::size_t position,count=0;ExternalVertexId source;
  while(sf>>position>>source){
   for(std::size_t w=0;w<warmups;++w){if(engine)(void)engine->solve(source);else(void)reference_dijkstra(graph,source);}
   for(std::size_t rep=0;rep<repeats;++rep){
    const auto measure=[&](auto &&solve){
     const auto before=mode=="paired"?e2::endpoint():e2::Endpoint{e2::clock(e2::wall_clock_id),{}, {}};
     auto result=solve();
     const auto after=mode=="paired"?e2::endpoint():e2::Endpoint{e2::clock(e2::wall_clock_id),{}, {}};
     const ShortestPathResult &paths=[&]() -> const ShortestPathResult & {if constexpr(std::is_same_v<decltype(result),BMSSPResult>)return result.shortest_paths;else return result;}();
     e2::prefix("sample");std::cout<<",\"condition\":\""<<condition<<"\",\"graph\":\""<<name<<"\",\"block\":"<<block<<",\"position\":"<<position<<",\"source\":"<<source<<",\"repeat\":"<<rep<<",\"pid\":"<<getpid()<<",\"thread_id\":"<<tid<<",\"mode\":\""<<mode<<'"';
     if(mode=="paired")e2::timing(before,after);else std::cout<<",\"wall_ns\":"<<after.before.ns-before.before.ns<<",\"cpu_ns\":null,\"reason\":\"separate wall-only endpoint perturbation control\"";
     std::cout<<",\"fingerprint\":"<<fingerprint(paths);
     if constexpr(std::is_same_v<decltype(result),BMSSPResult>)work(result.diagnostics);else std::cout<<",\"dijkstra_work\":["<<paths.diagnostics.settled_vertices<<','<<paths.diagnostics.scanned_edges<<','<<paths.diagnostics.queue_pushes<<']';std::cout<<"}\n";
     if(mode=="paired"&&(!e2::good(before)||!e2::good(after)||after.before.ns<before.after.ns||after.cpu.ns<before.cpu.ns))throw std::runtime_error("clock error/backwards; sample retained");
     if(mode=="plain"&&(before.before.rc||after.before.rc))throw std::runtime_error("wall clock failure");++count;
    };
    if(engine)measure([&](){return engine->solve(source);});else measure([&](){return reference_dijkstra(graph,source);});
   } // Result destroyed after reads/fingerprinting/output, before the next endpoint.
  }
  if(!sf.eof()||!count)throw std::invalid_argument("source records");rusage u{};if(getrusage(RUSAGE_SELF,&u))throw std::runtime_error("rusage");e2::prefix("footer");std::cout<<",\"samples\":"<<count<<",\"peak_rss_bytes\":"<<u.ru_maxrss<<",\"exit_state\":\"SUCCESS\"}\n";
 }catch(const std::exception &e){e2::prefix("failure");std::cout<<",\"message\":\"native process failed; see retained stderr\"}\n";std::cerr<<e.what()<<'\n';return 1;}
}
