// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <cstddef>
namespace profile_test {
inline thread_local std::size_t *comparisons = nullptr;
struct Count {
    std::size_t *previous;
    explicit Count(std::size_t &target) : previous(comparisons) {
        comparisons = &target;
    }
    ~Count() {
        comparisons = previous;
    }
    Count(const Count &) = delete;
    Count &operator=(const Count &) = delete;
};
inline void compared() {
    if (comparisons)
        ++*comparisons;
}
} // namespace profile_test
