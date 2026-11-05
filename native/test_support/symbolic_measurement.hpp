// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <algorithm>
#include <array>
#include <chrono>
#include <cstddef>
#include <unordered_set>
extern "C" void probe_pause();
extern "C" void probe_resume();
namespace symbolic_measurement {
using Clock = std::chrono::steady_clock;
struct Metrics {
    std::array<std::size_t, 9> categories{};
    std::size_t calls = 0, vertex_steps = 0, edge_steps = 0, max_walk = 0, attempts = 0, strict = 0,
                equal = 0, rejected = 0, bounded = 0, allocations = 0, slabs = 0, capacity = 0,
                copies = 0, moves = 0, assigns = 0, destroys = 0, arena_copies = 0, locks = 0,
                contended = 0, current_labels = 0, ancestry = 0;
    double allocation_seconds = 0, lock_seconds = 0, teardown_seconds = 0,
           label_destruction_seconds = 0;
};
inline thread_local Metrics *active = nullptr;
struct Timer {
    double *target;
    Clock::time_point start;
    explicit Timer(double *p) : target(p), start(p ? Clock::now() : Clock::time_point{}) {}
    ~Timer() {
        if (target)
            *target += std::chrono::duration<double>(Clock::now() - start).count();
    }
};
inline void count(std::size_t Metrics::*m) {
    if (active)
        ++(active->*m);
}
template <class T> auto copy(const T &t) {
    count(&Metrics::arena_copies);
    return t;
}
struct Walk {
    std::size_t steps = 0;
    ~Walk() {
        if (active)
            active->max_walk = std::max(active->max_walk, steps);
    }
};
int compare(const auto *a, const auto *b) {
    if (active)
        ++active->calls;
    auto category = [](std::size_t i, int value) {
        if (active)
            ++active->categories[i];
        return value;
    };
    if (a == b)
        return category(0, 0);
    if (!a)
        return category(1, 1);
    if (!b)
        return category(1, -1);
    const auto scalar = [](auto x, auto y) { return x < y ? -1 : (y < x ? 1 : 0); };
    if (auto c = scalar(a->distance, b->distance); c)
        return category(2, c);
    if (auto c = scalar(a->hops, b->hops); c)
        return category(3, c);
    if (active)
        ++active->categories[4];
    Walk walk;
    auto x = a, y = b;
    while (x && y && x != y) {
        ++walk.steps;
        if (active)
            ++active->vertex_steps;
        if (auto c = scalar(x->vertex, y->vertex); c)
            return category(5, c);
        x = x->parent;
        y = y->parent;
    }
    if (active)
        ++active->categories[6];
    x = a;
    y = b;
    while (x && y && x != y) {
        ++walk.steps;
        if (active)
            ++active->edge_steps;
        if (auto c = scalar(x->edge, y->edge); c)
            return category(7, c);
        x = x->parent;
        y = y->parent;
    }
    return category(8, 0);
}
} // namespace symbolic_measurement
