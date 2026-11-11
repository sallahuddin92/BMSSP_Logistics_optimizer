// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
namespace e2alloc {
inline thread_local unsigned insert_depth=0;
struct InsertScope {InsertScope(){++insert_depth;}~InsertScope(){--insert_depth;}};
constexpr std::size_t table_capacity=131072,event_capacity=8192;
struct Slot {std::uintptr_t pointer=0;std::size_t bytes=0,sequence=0,query=0;bool live=false,in_insert=false;};
struct Event {std::uintptr_t pointer;std::size_t bytes,sequence,query;unsigned phase,depth;bool allocation;};
struct Stats {
 std::size_t allocations=0,frees=0,bytes=0,reused_addresses=0,reused_different_size=0,insert_allocations=0,insert_frees=0,insert_bytes=0,insert_32_allocations=0,insert_32_same_scope_frees=0,unknown_frees=0,overflow=0,double_live=0,peak_live=0;
 std::array<std::size_t,32> allocation_bins{},free_bins{},insert_bins{},event_lifetime_bins{};
 std::array<std::size_t,3> phase_allocations{},phase_frees{};
};
inline std::array<Slot,table_capacity> table{};
inline std::array<Event,event_capacity> events{};
inline Stats stats{};
inline bool active=false;
inline unsigned phase=0;
inline std::size_t query=0,sequence=0,live_bytes=0,event_count=0,event_dropped=0;
inline std::size_t bin(std::size_t bytes){std::size_t b=0;while(bytes>1&&b<31){bytes=(bytes+1)/2;++b;}return b;}
inline void observe(void *pointer,std::size_t bytes,bool allocation) noexcept {
 if(!active||!pointer)return;
 ++sequence;const auto address=reinterpret_cast<std::uintptr_t>(pointer);const auto begin=(address>>4)%table_capacity;Slot *slot=nullptr;
 for(std::size_t i=0;i<table_capacity;++i){auto &s=table[(begin+i)%table_capacity];if(s.pointer==address||s.pointer==0){slot=&s;break;}}
 if(event_count<event_capacity)events[event_count++]={address,bytes,sequence,query,phase,insert_depth,allocation};else ++event_dropped;
 if(allocation){
  ++stats.allocations;stats.bytes+=bytes;++stats.allocation_bins[bin(bytes)];++stats.phase_allocations[phase];
  if(insert_depth){++stats.insert_allocations;stats.insert_bytes+=bytes;++stats.insert_bins[bin(bytes)];if(bytes==32)++stats.insert_32_allocations;}
  if(!slot){++stats.overflow;return;}
  if(slot->pointer==address){++stats.reused_addresses;if(slot->bytes!=bytes)++stats.reused_different_size;if(slot->live){++stats.double_live;return;}}
  *slot={address,bytes,sequence,query,true,insert_depth!=0};live_bytes+=bytes;if(live_bytes>stats.peak_live)stats.peak_live=live_bytes;
 }else{
  ++stats.frees;++stats.phase_frees[phase];
  if(!slot||slot->pointer!=address||!slot->live){++stats.unknown_frees;return;}
  ++stats.free_bins[bin(slot->bytes)];if(insert_depth)++stats.insert_frees;
  const auto age=sequence-slot->sequence;++stats.event_lifetime_bins[bin(age)];
  if(insert_depth&&slot->in_insert&&slot->bytes==32)++stats.insert_32_same_scope_frees;
  if(live_bytes>=slot->bytes)live_bytes-=slot->bytes;else ++stats.double_live;
  slot->live=false;
 }
}
}
