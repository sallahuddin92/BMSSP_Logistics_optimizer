// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "clock.hpp"
#include <mach/mach_time.h>
#include <os/log.h>
#include <os/signpost.h>
#include <unistd.h>
#include <string>
#ifndef E3_TRACE_ON
#define E3_TRACE_ON 0
#endif
namespace e3 {
class Spans {
#if E3_TRACE_ON
 os_log_t log_=nullptr;
#endif
 std::uint64_t tid_,anchor_=0,sequence_=0;
 public:
 explicit Spans(std::uint64_t tid):tid_(tid){
#if E3_TRACE_ON
  log_=os_log_create("org.bmssp.exploratory.e3",OS_LOG_CATEGORY_POINTS_OF_INTEREST);
  if(!os_signpost_enabled(log_))throw std::runtime_error("required signposts unavailable");
#endif
  mach_timebase_info_data_t tb{};if(mach_timebase_info(&tb)!=KERN_SUCCESS)throw std::runtime_error("Mach timebase unavailable");
  prefix("timebase");std::cout<<",\"numer\":"<<tb.numer<<",\"denom\":"<<tb.denom<<",\"trace_on\":"<<(E3_TRACE_ON?"true":"false")<<"}\n";anchor(0);
 }
 void anchor(std::uint64_t id){
#if E3_TRACE_ON
  if(id==0)id=os_signpost_id_generate(log_);
#endif
  const auto before=clock(wall_clock_id);const auto absolute=mach_absolute_time();const auto continuous=mach_continuous_time();const auto number=anchor_++;
#if E3_TRACE_ON
  os_signpost_event_emit(log_,id,"E3ClockAnchor","anchor=%{public}llu pid=%{public}d tid=%{public}llu absolute=%{public}llu continuous=%{public}llu",static_cast<unsigned long long>(number),getpid(),static_cast<unsigned long long>(tid_),static_cast<unsigned long long>(absolute),static_cast<unsigned long long>(continuous));
#endif
  const auto after=clock(wall_clock_id);if(before.rc||after.rc)throw std::runtime_error("anchor clock error");
  prefix("anchor");std::cout<<",\"anchor_id\":"<<number<<",\"pid\":"<<getpid()<<",\"thread_id\":"<<tid_<<",\"signpost_id\":"<<id<<",\"raw_before_ns\":"<<before.ns<<",\"raw_after_ns\":"<<after.ns<<",\"mach_absolute_ticks\":"<<absolute<<",\"mach_continuous_ticks\":"<<continuous<<"}\n";
 }
 std::uint64_t begin(const std::string &qid){
  std::uint64_t id=++sequence_;
#if E3_TRACE_ON
  id=os_signpost_id_generate(log_);
#endif
  anchor(id);
#if E3_TRACE_ON
  os_signpost_interval_begin(log_,id,"E3Query","qid=%{public}s",qid.c_str());
#else
  (void)qid;
#endif
  return id;
 }
 void end(std::uint64_t id,const std::string &qid){
#if E3_TRACE_ON
  os_signpost_interval_end(log_,id,"E3Query","qid=%{public}s",qid.c_str());
#else
  (void)qid;
#endif
  anchor(id);
 }
 void finish(){anchor(0);}
};
}
