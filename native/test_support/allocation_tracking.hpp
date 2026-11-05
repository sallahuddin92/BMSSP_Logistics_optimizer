// SPDX-License-Identifier: Apache-2.0
#pragma once
// Test/probe executables ONLY. Never linked into the production engine or binding.
// Counts successful ordinary and aligned C++ new/new[] requested bytes; excludes
// C malloc, allocator metadata and OS allocations. Timing runs use the real binding.
#include <array>
#include <cstdlib>
#include <limits>
#include <new>
namespace allocation_probe {
struct Counters {
    std::size_t calls = 0, bytes = 0, frees = 0;
    std::array<std::size_t, 32> size_bins{};
};
inline thread_local Counters *active = nullptr;
// Optional executable-only observer. Production libraries never include this file.
using Observer = void (*)(void *, std::size_t, bool) noexcept;
inline thread_local Observer observer = nullptr;
inline thread_local std::size_t fail_after = std::numeric_limits<std::size_t>::max();
struct FailAfter {
    std::size_t previous;
    explicit FailAfter(std::size_t n) : previous(fail_after) {
        fail_after = n;
    }
    ~FailAfter() {
        fail_after = previous;
    }
    FailAfter(const FailAfter &) = delete;
    FailAfter &operator=(const FailAfter &) = delete;
};
struct Track {
    Counters *previous;
    explicit Track(Counters &stats) : previous(active) {
        active = &stats;
    }
    ~Track() {
        active = previous;
    }
    Track(const Track &) = delete;
    Track &operator=(const Track &) = delete;
};
inline void before_allocate() {
    if (fail_after != std::numeric_limits<std::size_t>::max()) {
        if (fail_after == 0)
            throw std::bad_alloc();
        --fail_after;
    }
}
inline void record(std::size_t n) {
    if (active) {
        ++active->calls;
        active->bytes += n;
        std::size_t bin = 0, bound = 1;
        while (bound < n && bin + 1 < active->size_bins.size()) {
            ++bin;
            bound *= 2;
        }
        ++active->size_bins[bin];
    }
}
inline void *allocate(std::size_t n) {
    before_allocate();
    void *p = std::malloc(n ? n : 1);
    if (!p)
        throw std::bad_alloc();
    record(n);
    if (observer)
        observer(p, n, true);
    return p;
}
inline void *allocate_aligned(std::size_t n, std::size_t alignment) {
    before_allocate();
    void *p = nullptr;
    if (alignment < alignof(void *))
        alignment = alignof(void *);
    if (posix_memalign(&p, alignment, n ? n : 1))
        throw std::bad_alloc();
    record(n);
    if (observer)
        observer(p, n, true);
    return p;
}
inline void release(void *p) noexcept {
    if (p && active)
        ++active->frees;
    if (p && observer)
        observer(p, 0, false);
    std::free(p);
}
} // namespace allocation_probe
void *operator new(std::size_t n) {
    return allocation_probe::allocate(n);
}
void *operator new[](std::size_t n) {
    return allocation_probe::allocate(n);
}
void operator delete(void *p) noexcept {
    allocation_probe::release(p);
}
void operator delete[](void *p) noexcept {
    allocation_probe::release(p);
}
void operator delete(void *p, std::size_t) noexcept {
    allocation_probe::release(p);
}
void operator delete[](void *p, std::size_t) noexcept {
    allocation_probe::release(p);
}

void *operator new(std::size_t n, std::align_val_t alignment) {
    return allocation_probe::allocate_aligned(n, static_cast<std::size_t>(alignment));
}
void *operator new[](std::size_t n, std::align_val_t alignment) {
    return allocation_probe::allocate_aligned(n, static_cast<std::size_t>(alignment));
}
void operator delete(void *p, std::align_val_t) noexcept {
    allocation_probe::release(p);
}
void operator delete[](void *p, std::align_val_t) noexcept {
    allocation_probe::release(p);
}
void operator delete(void *p, std::size_t, std::align_val_t) noexcept {
    allocation_probe::release(p);
}
void operator delete[](void *p, std::size_t, std::align_val_t) noexcept {
    allocation_probe::release(p);
}
