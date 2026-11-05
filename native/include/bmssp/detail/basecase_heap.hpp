// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/symbolic_label.hpp"
#include <algorithm>
#include <utility>
#include <vector>
namespace bmssp::detail {
// One workspace owns this storage. BaseCase is a leaf: no recursive child can
// overlap its use. The lease releases labels on every exit, retaining capacity.
class BaseCaseHeap {
  public:
    struct Item {
        VertexIndex key;
        SymbolicLabel value;
    };
    struct Greater {
        bool operator()(const Item &a, const Item &b) const {
            return b.value < a.value;
        }
    };
    class Use {
        BaseCaseHeap &heap_;

      public:
        explicit Use(BaseCaseHeap &heap) : heap_(heap) {
            heap_.clear();
        }
        Use(const Use &) = delete;
        Use &operator=(const Use &) = delete;
        ~Use() {
            heap_.clear();
        }
    };
    [[nodiscard]] bool empty() const noexcept {
        return items_.empty();
    }
    [[nodiscard]] std::size_t size() const noexcept {
        return items_.size();
    }
    [[nodiscard]] std::size_t capacity() const noexcept {
        return items_.capacity();
    }
    [[nodiscard]] const Item &top() const {
        return items_.front();
    }
    void push(Item item) {
        // vector checks max_size and preserves its contents on allocation failure.
        // No k-based capacity bound: stale records also occupy queue storage.
        items_.push_back(std::move(item));
        std::push_heap(items_.begin(), items_.end(), Greater{});
    }
    void pop() {
        std::pop_heap(items_.begin(), items_.end(), Greater{});
        items_.pop_back();
    }
    void clear() noexcept {
        items_.clear();
    }

  private:
    std::vector<Item> items_;
};
} // namespace bmssp::detail
