// SPDX-License-Identifier: Apache-2.0
#pragma once
// Executable-only instrumentation; no production include or timing path.
#include "bmssp/graph.hpp"
#include <array>
#include <chrono>
#include <unordered_map>
#include <utility>
#include <vector>
namespace frame_measurement {
enum class Part : std::size_t { membership, owned, children, prepend, other, base, pivots, count };
constexpr std::size_t count = static_cast<std::size_t>(Part::count);
struct Stats {
    double seconds = 0;
    std::size_t allocations = 0, bytes = 0, frees = 0, live = 0, peak_live = 0, attempts = 0,
                unique = 0, duplicates = 0, constructions = 0;
};
struct Invocation {
    std::size_t level = 0, depth = 0, frontier = 0, returned = 0, members = 0, rehashes = 0,
                bucket_peak = 0;
    bool constructed = false;
    std::array<std::size_t, count> live{}, retained{};
    double seconds = 0, children_seconds = 0, setup_seconds = 0, teardown_seconds = 0;
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
    std::size_t run_calls = 0, base_calls = 0, live_frames = 0, peak_frames = 0, active_members = 0,
                peak_active_members = 0;
    std::size_t lookups = 0, constructions = 0, peak_active_scratch = 0;
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
template <class Set> void scratch(const Set &set) {
    if constexpr (requires { set.pool_retained_bytes(); }) {
        if (active) {
            active->scratch_bytes = std::max(active->scratch_bytes, set.pool_retained_bytes());
            active->peak_active_scratch =
                std::max(active->peak_active_scratch, set.pool_active_bytes());
        }
    }
}
template <class Set> auto insert(Set &set, bmssp::VertexIndex v) {
    Scope scope(Part::membership);
    std::size_t buckets = 0;
    if constexpr (requires { set.bucket_count(); })
        buckets = set.bucket_count();
    auto result = set.insert(v);
    if (active) {
        auto &p = active->parts[0];
        ++p.attempts;
        const bool unique = [&] {
            if constexpr (requires { result.second; })
                return result.second;
            else
                return result;
        }();
        if (unique) {
            ++p.unique;
            ++active->calls[active->current].members;
            ++active->active_members;
            active->peak_active_members =
                std::max(active->peak_active_members, active->active_members);
        } else
            ++p.duplicates;
        if constexpr (requires { set.bucket_count(); }) {
            auto &f = active->calls[active->current];
            if (set.bucket_count() != buckets)
                ++f.rehashes;
            f.bucket_peak = std::max(f.bucket_peak, set.bucket_count());
        }
        scratch(set);
    }
    return result;
}
template <class Set> bool contains(const Set &set, bmssp::VertexIndex v) {
    Scope scope(Part::membership);
    if (active)
        ++active->lookups;
    return set.contains(v);
}
inline void constructed() {
    if (active) {
        ++active->constructions;
        ++active->parts[0].constructions;
        active->calls[active->current].constructed = true;
    }
}
class Call {
    using Clock = std::chrono::steady_clock;
    Clock::time_point start_{}, return_{};
    std::size_t previous_ = static_cast<std::size_t>(-1), id_ = static_cast<std::size_t>(-1);
    Part previous_part_ = Part::other;
    bool measured_ = active != nullptr, created_ = false;

  public:
    Call(std::size_t level, std::size_t depth, std::size_t frontier) {
        if (!measured_)
            return;
        start_ = Clock::now();
        Pause pause;
        previous_ = active->current;
        previous_part_ = active->part;
        ++active->run_calls;
        active->base_calls += level == 0;
        ++active->live_frames;
        active->peak_frames = std::max(active->peak_frames, active->live_frames);
        if (level > 0 || previous_ == static_cast<std::size_t>(-1)) {
            id_ = active->calls.size();
            active->calls.emplace_back();
            auto &f = active->calls.back();
            f.level = level;
            f.depth = depth;
            f.frontier = frontier;
            active->current = id_;
            created_ = true;
        }
        active->part = level == 0 ? Part::base : Part::other;
    }
    void ready() {
        if (measured_ && created_)
            active->calls[id_].setup_seconds =
                std::chrono::duration<double>(Clock::now() - start_).count();
    }
    void returned(std::size_t size) {
        if (measured_ && created_) {
            active->calls[id_].returned = size;
            return_ = Clock::now();
        }
    }
    ~Call() {
        if (!measured_)
            return;
        const double seconds = std::chrono::duration<double>(Clock::now() - start_).count();
        if (created_) {
            auto &f = active->calls[id_];
            f.seconds = seconds;
            if (return_ != Clock::time_point{})
                f.teardown_seconds = std::chrono::duration<double>(Clock::now() - return_).count();
            f.retained = f.live;
            active->active_members -= f.members;
        }
        if (previous_ != static_cast<std::size_t>(-1))
            active->calls[previous_].children_seconds += seconds;
        --active->live_frames;
        active->current = previous_;
        active->part = previous_part_;
    }
};
} // namespace frame_measurement
