// SPDX-License-Identifier: Apache-2.0
#pragma once
// Explicitly instrumented probe only; never included by the production library.
#include "bmssp/graph.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <queue>
#include <type_traits>
#include <unordered_set>
#include <utility>
namespace basecase_measurement {
struct Allocation {
    std::size_t calls, bytes, frees;
};
Allocation snapshot() noexcept;
struct Metrics {
    std::size_t calls = 0, allocations = 0, bytes = 0, frees = 0;
    std::size_t heap_allocations = 0, heap_bytes = 0, pushes = 0, pops = 0, peak_size = 0,
                peak_capacity = 0;
    std::size_t membership_allocations = 0, membership_bytes = 0, inserts = 0, contains = 0;
    std::size_t completed_allocations = 0, completed_bytes = 0, completed_total = 0,
                completed_max = 0;
    std::size_t stale = 0, duplicate = 0, partial = 0, exhausted = 0;
    double inclusive_seconds = 0, setup_seconds = 0, body_seconds = 0, teardown_seconds = 0;
    std::array<std::size_t, 65> completed_histogram{};
};
extern thread_local Metrics *active;
class Call {
    using Clock = std::chrono::steady_clock;
    Metrics *data_ = active;
    Allocation before_{};
    Clock::time_point start_{}, ready_{}, return_{};

  public:
    Call() {
        if (data_) {
            before_ = snapshot();
            start_ = Clock::now();
            ++data_->calls;
        }
    }
    void ready() {
        if (data_) {
            ready_ = Clock::now();
            data_->setup_seconds += std::chrono::duration<double>(ready_ - start_).count();
        }
    }
    void returned(bool partial, std::size_t size) {
        if (data_) {
            return_ = Clock::now();
            data_->body_seconds += std::chrono::duration<double>(return_ - ready_).count();
            ++(partial ? data_->partial : data_->exhausted);
            data_->completed_total += size;
            data_->completed_max = std::max(data_->completed_max, size);
            ++data_->completed_histogram[std::min(size, std::size_t{64})];
        }
    }
    ~Call() {
        if (data_) {
            const auto end = Clock::now();
            const auto after = snapshot();
            data_->allocations += after.calls - before_.calls;
            data_->bytes += after.bytes - before_.bytes;
            data_->frees += after.frees - before_.frees;
            data_->inclusive_seconds += std::chrono::duration<double>(end - start_).count();
            if (return_ != Clock::time_point{})
                data_->teardown_seconds += std::chrono::duration<double>(end - return_).count();
        }
    }
};
template <class T, class Container, class Compare>
class CapacityQueue : public std::priority_queue<T, Container, Compare> {
    using Base = std::priority_queue<T, Container, Compare>;

  public:
    using Base::Base;
    std::size_t capacity() const {
        return this->c.capacity();
    }
};
template <class Heap> class HeapView {
    Heap &heap_;

  public:
    explicit HeapView(Heap &heap) : heap_(heap) {}
    bool empty() const {
        return heap_.empty();
    }
    auto const &top() const {
        return heap_.top();
    }
    void pop() {
        heap_.pop();
        if (active)
            ++active->pops;
    }
    template <class Item> void push(Item &&item) {
        const auto before = snapshot();
        heap_.push(std::forward<Item>(item));
        if (active) {
            const auto after = snapshot();
            ++active->pushes;
            active->heap_allocations += after.calls - before.calls;
            active->heap_bytes += after.bytes - before.bytes;
            active->peak_size = std::max(active->peak_size, heap_.size());
            active->peak_capacity = std::max(active->peak_capacity, heap_.capacity());
        }
    }
    // Braced Item arguments need a concrete overload, matching priority_queue.
    using Item = std::remove_cvref_t<decltype(std::declval<Heap>().top())>;
    void push(Item item) {
        push<Item>(std::move(item));
    }
};
template <class Membership> class MembershipView {
    Membership &set_;

  public:
    explicit MembershipView(Membership &set) : set_(set) {}
    auto insert(bmssp::VertexIndex key) {
        const auto before = snapshot();
        auto result = set_.insert(key);
        if (active) {
            const auto after = snapshot();
            ++active->inserts;
            active->membership_allocations += after.calls - before.calls;
            active->membership_bytes += after.bytes - before.bytes;
        }
        return result;
    }
    bool contains(bmssp::VertexIndex key) const {
        if (active)
            ++active->contains;
        return set_.contains(key);
    }
};
inline void membership_prepared(Allocation before) {
    if (active) {
        const auto after = snapshot();
        active->membership_allocations += after.calls - before.calls;
        active->membership_bytes += after.bytes - before.bytes;
    }
}
inline void completed_prepared(Allocation before) {
    if (active) {
        const auto after = snapshot();
        active->completed_allocations += after.calls - before.calls;
        active->completed_bytes += after.bytes - before.bytes;
    }
}
template <class T> void completed_push(std::vector<T> &values, T value) {
    const auto before = snapshot();
    values.push_back(value);
    if (active) {
        const auto after = snapshot();
        active->completed_allocations += after.calls - before.calls;
        active->completed_bytes += after.bytes - before.bytes;
    }
}
} // namespace basecase_measurement
