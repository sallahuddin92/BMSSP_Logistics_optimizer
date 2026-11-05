// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <algorithm>
#include <cstdint>
#include <limits>
#include <type_traits>
#include <vector>
namespace bmssp::detail {
// Scratch membership for one completed, non-nested validation operation. Not a
// live recursion-frame set. Each workspace owns its own marks; no global state.
template <class Epoch = std::uint32_t> class DenseMarks {
    static_assert(std::is_integral_v<Epoch> && std::is_unsigned_v<Epoch> &&
                  !std::is_same_v<Epoch, bool>);
    std::vector<Epoch> marks_;
    Epoch epoch_ = 1;

  public:
    explicit DenseMarks(std::size_t size = 0) : marks_(size, 0) {}
    void resize(std::size_t size) {
        marks_.assign(size, 0);
        epoch_ = 1;
    }
    void begin() {
        if (epoch_ == std::numeric_limits<Epoch>::max()) {
            std::fill(marks_.begin(), marks_.end(), Epoch{0});
            epoch_ = 1;
        } else
            ++epoch_;
    }
    [[nodiscard]] bool insert(std::size_t index) {
        auto &mark = marks_.at(index);
        if (mark == epoch_)
            return false;
        mark = epoch_;
        return true;
    }
};
} // namespace bmssp::detail
