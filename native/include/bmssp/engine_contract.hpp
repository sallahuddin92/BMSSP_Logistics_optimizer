// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <cfenv>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>

namespace bmssp {
static_assert(std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits == 53,
              "The numerical contract requires IEEE 754 binary64");
inline void validate_numeric_environment() {
    if (std::fegetround() != FE_TONEAREST) {
        throw std::invalid_argument("queries require round-to-nearest arithmetic");
    }
}
using Weight = double;
using Distance = double;
inline constexpr Distance unreachable = std::numeric_limits<Distance>::infinity();

inline std::size_t checked_size_add(std::size_t a, std::size_t b) {
    if (a > std::numeric_limits<std::size_t>::max() - b) {
        throw std::length_error("size addition overflow");
    }
    return a + b;
}
template <class T> void check_allocation_count(std::size_t count) {
    if (count > std::numeric_limits<std::size_t>::max() / sizeof(T) ||
        count > std::vector<T>{}.max_size()) {
        throw std::length_error("allocation count exceeds representable storage");
    }
}
inline Distance checked_distance_add(Distance a, Weight b) {
    if (!std::isfinite(a) || !std::isfinite(b) || a < 0 || b < 0) {
        throw std::invalid_argument("distance addition requires finite nonnegative operands");
    }
    if (a > std::numeric_limits<Distance>::max() - b) {
        throw std::overflow_error("distance addition overflow");
    }
    const auto sum = a + b;
    if (!std::isfinite(sum))
        throw std::overflow_error("nonfinite distance sum");
    return sum;
}
} // namespace bmssp
