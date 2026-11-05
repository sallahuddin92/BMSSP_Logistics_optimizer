// SPDX-License-Identifier: Apache-2.0
#pragma once
// Executable-only instrumentation; no production include or timing path.
#include "bmssp/graph.hpp"
#include <array>
#include <chrono>
#include <unordered_map>
#include <utility>
#include <vector>
namespace pivot_measurement {
enum class Part : std::size_t {
    cumulative,
    round,
    current_next,
    forest,
    owned_results,
    other,
    count
};
constexpr std::size_t count = static_cast<std::size_t>(Part::count);
struct Stats {
    double seconds = 0;
    std::size_t allocations = 0, bytes = 0, frees = 0, live = 0, peak_live = 0, attempts = 0,
                unique = 0, duplicates = 0, constructions = 0;
};
struct Round {
    std::size_t current, next, visited;
};
struct Invocation {
    std::size_t frontier = 0, pivots = 0, visited = 0;
    bool early = false;
    std::vector<Round> rounds;
    std::array<std::size_t, count> live{}, retained{};
    double seconds = 0;
};
struct Record {
    std::size_t bytes, call;
    Part part;
};
struct Metrics {
    std::array<Stats, count> parts{};
    std::vector<Invocation> calls;
    std::unordered_map<void *, Record> pointers;
    std::size_t current = static_cast<std::size_t>(-1), scratch_bytes = 0, live = 0, peak_live = 0;
    Part part = Part::other;
    bool failed = false;
};
extern thread_local Metrics *active;
// Disables the observer AND ordinary counts while recording instrumentation data.
class Pause {
    void *counters_;
    void (*observer_)(void *, std::size_t, bool) noexcept;

  public:
    Pause();
    ~Pause();
    Pause(const Pause &) = delete;
    Pause &operator=(const Pause &) = delete;
};
void observe(void *, std::size_t, bool) noexcept;
class Scope {
    using Clock = std::chrono::steady_clock;
    Part previous_, part_;
    bool timed_;
    Clock::time_point start_{};

  public:
    explicit Scope(Part part)
        : previous_(active ? active->part : Part::other), part_(part),
          timed_(active && part != previous_) {
        if (active)
            active->part = part;
        if (timed_)
            start_ = Clock::now();
    }
    ~Scope() {
        if (active) {
            if (timed_)
                active->parts[static_cast<std::size_t>(part_)].seconds +=
                    std::chrono::duration<double>(Clock::now() - start_).count();
            active->part = previous_;
        }
    }
};
template <class F> decltype(auto) measure(Part part, F &&f) {
    Scope scope(part);
    return std::forward<F>(f)();
}
template <class Set> auto insert(Set &set, bmssp::VertexIndex v, Part part) {
    Scope scope(part);
    auto result = set.insert(v);
    if (!active)
        return result;
    auto &s = active->parts[static_cast<std::size_t>(part)];
    ++s.attempts;
    bool unique;
    if constexpr (requires { result.second; })
        unique = result.second;
    else
        unique = result;
    if (unique)
        ++s.unique;
    else
        ++s.duplicates;
    return result;
}
inline void constructed(Part part) {
    if (active)
        ++active->parts[static_cast<std::size_t>(part)].constructions;
}
inline void seeded(std::size_t n) {
    if (active) {
        auto &s = active->parts[static_cast<std::size_t>(Part::cumulative)];
        s.attempts += n;
        s.unique += n;
    }
}
class Call {
    using Clock = std::chrono::steady_clock;
    Clock::time_point start_ = Clock::now();
    std::size_t id_ = 0;
    bool measured_ = active != nullptr;

  public:
    explicit Call(std::size_t frontier) {
        if (!measured_)
            return;
        Pause pause;
        id_ = active->calls.size();
        active->calls.emplace_back();
        active->calls.back().frontier = frontier;
        active->current = id_;
        active->part = Part::other;
    }
    void round(std::size_t current) {
        if (!measured_)
            return;
        Pause pause;
        active->calls[id_].rounds.push_back({current, 0, 0});
    }
    void sizes(std::size_t next, std::size_t visited) {
        if (!measured_)
            return;
        auto &r = active->calls[id_].rounds.back();
        r.next = next;
        r.visited = visited;
    }
    void returned(bool early, std::size_t pivots, std::size_t visited) {
        if (!measured_)
            return;
        auto &c = active->calls[id_];
        c.early = early;
        c.pivots = pivots;
        c.visited = visited;
    }
    ~Call() {
        if (!measured_)
            return;
        auto &c = active->calls[id_];
        c.seconds = std::chrono::duration<double>(Clock::now() - start_).count();
        c.retained = c.live;
        active->current = static_cast<std::size_t>(-1);
        active->part = Part::other;
    }
};
} // namespace pivot_measurement
