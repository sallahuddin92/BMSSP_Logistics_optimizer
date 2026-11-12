// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <cerrno>
#include <cstdint>
#include <iostream>
#include <time.h>
namespace e3 {
constexpr clockid_t wall_clock_id=CLOCK_MONOTONIC_RAW;
constexpr const char *label="EXPLORATORY_BMSSP_HARDWARE_ATTRIBUTION";
struct Read { std::int64_t ns=0; int rc=0,error=0; };
inline Read clock(clockid_t id) {
    timespec t{};const int rc=clock_gettime(id,&t);return {rc==0?static_cast<std::int64_t>(t.tv_sec)*1000000000+t.tv_nsec:0,rc,rc==0?0:errno};
}
struct Endpoint {Read before,cpu,after;};
inline Endpoint endpoint(){const auto a=clock(wall_clock_id);const auto c=clock(CLOCK_THREAD_CPUTIME_ID);const auto b=clock(wall_clock_id);return {a,c,b};}
inline bool good(const Endpoint &e){return e.before.rc==0&&e.cpu.rc==0&&e.after.rc==0&&e.after.ns>=e.before.ns;}
inline void prefix(const char *kind){std::cout<<"{\"label\":\""<<label<<"\",\"kind\":\""<<kind<<'"';}
inline void timing(const Endpoint &a,const Endpoint &b){
    std::cout<<",\"wall_ns\":"<<b.before.ns-a.after.ns<<",\"cpu_ns\":"<<b.cpu.ns-a.cpu.ns
             <<",\"wall_envelope_ns\":"<<b.after.ns-a.before.ns<<",\"off_estimate_ns\":"<<(b.before.ns-a.after.ns)-(b.cpu.ns-a.cpu.ns)
             <<",\"off_upper_aperture_ns\":"<<(b.after.ns-a.before.ns)-(b.cpu.ns-a.cpu.ns)
             <<",\"start_aperture_ns\":"<<a.after.ns-a.before.ns<<",\"end_aperture_ns\":"<<b.after.ns-b.before.ns;
    std::cout<<",\"raw_ns\":["<<a.before.ns<<','<<a.cpu.ns<<','<<a.after.ns<<','<<b.before.ns<<','<<b.cpu.ns<<','<<b.after.ns<<"],\"clock_rc\":["<<a.before.rc<<','<<a.cpu.rc<<','<<a.after.rc<<','<<b.before.rc<<','<<b.cpu.rc<<','<<b.after.rc<<"],\"clock_errno\":["<<a.before.error<<','<<a.cpu.error<<','<<a.after.error<<','<<b.before.error<<','<<b.cpu.error<<','<<b.after.error<<']';
}
}
