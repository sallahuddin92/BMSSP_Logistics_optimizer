// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <array>
#include <chrono>
#include <cstddef>
namespace bmssp {
// Opt-in per-thread query instrumentation. Exclusive times partition instrumented work;
// inclusive times overlap (especially recursion). Disabled queries do not read clocks.
enum class ProfilePart : std::size_t {
    labels,
    comparison,
    pivots,
    base,
    frontier,
    recursion,
    count
};
struct QueryProfile {
    static constexpr auto size = static_cast<std::size_t>(ProfilePart::count);
    std::array<double, size> inclusive{}, exclusive{};
    std::array<std::size_t, size> calls{};
};
inline thread_local QueryProfile *active_profile = nullptr;
class ProfileScope {
    using Clock = std::chrono::steady_clock;
    inline static thread_local ProfileScope *top_ = nullptr;
    QueryProfile *profile_;
    ProfileScope *parent_ = nullptr;
    ProfilePart part_;
    Clock::time_point start_{};
    double children_ = 0;

  public:
    explicit ProfileScope(ProfilePart part) : profile_(active_profile), part_(part) {
        if (profile_) {
            parent_ = top_;
            top_ = this;
            start_ = Clock::now();
        }
    }
    ~ProfileScope() {
        if (profile_) {
            const double elapsed = std::chrono::duration<double>(Clock::now() - start_).count();
            const auto i = static_cast<std::size_t>(part_);
            profile_->inclusive[i] += elapsed;
            profile_->exclusive[i] += elapsed - children_;
            ++profile_->calls[i];
            if (parent_)
                parent_->children_ += elapsed;
            top_ = parent_;
        }
    }
};
class ProfileSession {
    QueryProfile *previous_;

  public:
    explicit ProfileSession(QueryProfile *profile) : previous_(active_profile) {
        active_profile = profile;
    }
    ~ProfileSession() {
        active_profile = previous_;
    }
};
} // namespace bmssp
