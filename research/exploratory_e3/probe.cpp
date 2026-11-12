// SPDX-License-Identifier: Apache-2.0
// EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION: minimal availability probe, no BMSSP queries.
#include <cerrno>
#include <cstdint>
#include <iostream>
#include <mach/mach_time.h>
#include <os/log.h>
#include <os/signpost.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>
namespace {
constexpr const char *label="EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION";
std::uint64_t now(clockid_t id){timespec t{};if(clock_gettime(id,&t))throw errno;return static_cast<std::uint64_t>(t.tv_sec)*1000000000ULL+static_cast<std::uint64_t>(t.tv_nsec);}
void anchor(os_log_t log,os_signpost_id_t id,unsigned number,std::uint64_t tid){
 const auto before=now(CLOCK_MONOTONIC_RAW);const auto absolute=mach_absolute_time();const auto continuous=mach_continuous_time();
 os_signpost_event_emit(log,id,"E3ClockAnchor","anchor=%{public}u pid=%{public}d tid=%{public}llu absolute=%{public}llu continuous=%{public}llu",number,getpid(),static_cast<unsigned long long>(tid),static_cast<unsigned long long>(absolute),static_cast<unsigned long long>(continuous));
 const auto after=now(CLOCK_MONOTONIC_RAW);
 std::cout<<"{\"label\":\""<<label<<"\",\"kind\":\"anchor\",\"anchor_id\":"<<number<<",\"pid\":"<<getpid()<<",\"thread_id\":"<<tid<<",\"signpost_id\":"<<id<<",\"raw_before_ns\":"<<before<<",\"raw_after_ns\":"<<after<<",\"mach_absolute_ticks\":"<<absolute<<",\"mach_continuous_ticks\":"<<continuous<<"}\n";
}
}
int main(){
 try{
  std::cout<<std::unitbuf;std::uint64_t tid=0;if(pthread_threadid_np(nullptr,&tid))return 2;
  mach_timebase_info_data_t tb{};if(mach_timebase_info(&tb)!=KERN_SUCCESS)return 3;
  os_log_t log=os_log_create("org.bmssp.exploratory.e3",OS_LOG_CATEGORY_POINTS_OF_INTEREST);
  std::cout<<"{\"label\":\""<<label<<"\",\"kind\":\"probe_header\",\"pid\":"<<getpid()<<",\"thread_id\":"<<tid<<",\"timebase_numer\":"<<tb.numer<<",\"timebase_denom\":"<<tb.denom<<",\"signpost_enabled\":"<<(os_signpost_enabled(log)?"true":"false")<<"}\n";
  for(unsigned rep=0;rep<3;++rep){
   const auto id=os_signpost_id_generate(log);anchor(log,id,rep*2,tid);
   os_signpost_interval_begin(log,id,"E3Query","qid=E3-availability-%{public}u graph=availability source=-1 variant=probe block=-1 rep=%{public}u pid=%{public}d tid=%{public}llu",rep,rep,getpid(),static_cast<unsigned long long>(tid));
   const auto w0=now(CLOCK_MONOTONIC_RAW);const auto c0=now(CLOCK_THREAD_CPUTIME_ID);
   std::uint64_t checksum=1;const auto busy_end=w0+30000000ULL;
   while(now(CLOCK_MONOTONIC_RAW)<busy_end)checksum=checksum*6364136223846793005ULL+1;
   usleep(30000); // Deliberate probe blocking, not invented scheduler state.
   const auto c1=now(CLOCK_THREAD_CPUTIME_ID);const auto w1=now(CLOCK_MONOTONIC_RAW);
   os_signpost_interval_end(log,id,"E3Query","qid=E3-availability-%{public}u checksum=%{public}llu",rep,static_cast<unsigned long long>(checksum));
   anchor(log,id,rep*2+1,tid);
   std::cout<<"{\"label\":\""<<label<<"\",\"kind\":\"probe_span\",\"query_id\":\"E3-availability-"<<rep<<"\",\"pid\":"<<getpid()<<",\"thread_id\":"<<tid<<",\"signpost_id\":"<<id<<",\"wall_start_ns\":"<<w0<<",\"wall_end_ns\":"<<w1<<",\"cpu_start_ns\":"<<c0<<",\"cpu_end_ns\":"<<c1<<",\"checksum\":"<<checksum<<"}\n";
  }
  usleep(200000);
 }catch(int error){std::cerr<<"clock error "<<error<<'\n';return 4;}
}
