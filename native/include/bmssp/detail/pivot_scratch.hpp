// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/detail/dense_marks.hpp"
#include <stdexcept>
namespace bmssp::detail {
// FindPivots completes before children/observers execute. Only its membership is
// reusable; returned W/P vectors and live recursive completed sets remain owned.
template <class Epoch = std::uint32_t> class PivotScratch {
    bool active_ = false;

  public:
    DenseMarks<Epoch> visited, round;
    class Use {
        PivotScratch &scratch_;

      public:
        explicit Use(PivotScratch &scratch) : scratch_(scratch) {
            if (scratch_.active_)
                throw std::logic_error("FindPivots workspace is not reentrant");
            scratch_.active_ = true;
        }
        Use(const Use &) = delete;
        Use &operator=(const Use &) = delete;
        ~Use() {
            scratch_.active_ = false;
        }
    };
};
} // namespace bmssp::detail
