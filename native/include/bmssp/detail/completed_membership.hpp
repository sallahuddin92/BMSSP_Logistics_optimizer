// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/detail/dense_marks.hpp"
#include "bmssp/graph.hpp"
#include <array>
#include <memory>
#include <utility>
namespace bmssp::detail {
template <class Epoch> class DenseCompletedStorage {
    DenseMarks<Epoch> marks_;
    std::size_t vertices_ = 0;

  public:
    void begin(std::size_t vertices) {
        vertices_ = vertices;
        marks_.begin();
    }
    bool contains(VertexIndex v) const {
        return marks_.size() == vertices_ && marks_.contains(v);
    }
    bool insert(VertexIndex v) {
        if (marks_.size() != vertices_)
            marks_.resize(vertices_);
        return marks_.insert(v);
    }
    std::size_t bytes() const noexcept {
        return marks_.size() * sizeof(Epoch);
    }
};
// Deterministic exact epochs in lazily allocated 512-index blocks. No graph-size
// cap: every validated index maps to one directory entry and one marker.
template <class Epoch> class PagedCompletedStorage {
    static constexpr std::size_t width = 512;
    using Page = std::array<Epoch, width>;
    std::vector<std::unique_ptr<Page>> pages_;
    std::size_t vertices_ = 0, allocated_ = 0;
    Epoch epoch_ = 1;

  public:
    void begin(std::size_t vertices) {
        if (vertices != vertices_) {
            pages_.clear();
            allocated_ = 0;
            vertices_ = vertices;
        }
        if (epoch_ == std::numeric_limits<Epoch>::max()) {
            for (auto &p : pages_)
                if (p)
                    p->fill(0);
            epoch_ = 1;
        } else
            ++epoch_;
    }
    bool contains(VertexIndex v) const {
        if (pages_.empty())
            return false;
        const auto &page = pages_.at(v / width);
        return page && page->at(v % width) == epoch_;
    }
    bool insert(VertexIndex v) {
        if (pages_.empty())
            pages_.resize(vertices_ / width + (vertices_ % width != 0));
        auto &page = pages_.at(v / width);
        if (!page) {
            page = std::make_unique<Page>();
            ++allocated_;
        }
        auto &mark = page->at(v % width);
        if (mark == epoch_)
            return false;
        mark = epoch_;
        return true;
    }
    std::size_t bytes() const noexcept {
        return pages_.capacity() * sizeof(std::unique_ptr<Page>) + allocated_ * sizeof(Page);
    }
};
template <template <class> class Storage, std::size_t Small, class Epoch = std::uint32_t>
class CompletedFrames {
    static_assert(std::is_unsigned_v<Epoch> && !std::is_same_v<Epoch, bool>);
    class Membership {
        Storage<Epoch> storage_;
        std::array<VertexIndex, Small> small_{};
        std::size_t vertices_ = 0, size_ = 0;
        bool promoted_ = Small == 0;
        void check(VertexIndex v) const {
            if (v >= vertices_)
                throw std::out_of_range("completed membership vertex");
        }

      public:
        void begin(std::size_t vertices) {
            vertices_ = vertices;
            size_ = 0;
            promoted_ = Small == 0;
            storage_.begin(vertices);
        }
        bool contains(VertexIndex v) const {
            check(v);
            if (promoted_)
                return storage_.contains(v);
            return std::find(small_.begin(), small_.begin() + static_cast<std::ptrdiff_t>(size_),
                             v) != small_.begin() + static_cast<std::ptrdiff_t>(size_);
        }
        bool insert(VertexIndex v) {
            check(v);
            if (promoted_) {
                const bool unique = storage_.insert(v);
                size_ += unique;
                return unique;
            }
            if (contains(v))
                return false;
            if (size_ < Small) {
                small_[size_++] = v;
                return true;
            }
            // Allocation failure leaves inline answers intact; retry or unwind is
            // safe. A newly leased frame starts another epoch, ignoring remnants.
            for (auto key : small_)
                (void)storage_.insert(key);
            (void)storage_.insert(v);
            promoted_ = true;
            ++size_;
            return true;
        }
        std::size_t size() const noexcept {
            return size_;
        }
        bool promoted() const noexcept {
            return promoted_;
        }
        std::size_t bytes() const noexcept {
            return storage_.bytes();
        }
    };
    struct Slot {
        Membership membership;
        bool active = false;
    };
    std::vector<std::unique_ptr<Slot>> slots_;

  public:
    // Membership was frame-local before this cache existed. Copies keep the same
    // workspace labels/options but start with empty caches, even inside a reader.
    CompletedFrames() = default;
    CompletedFrames(const CompletedFrames &) noexcept {}
    CompletedFrames &operator=(const CompletedFrames &other) {
        if (this != &other) {
            if (active_count() != 0)
                throw std::logic_error("assigning active completed frames");
            slots_.clear();
        }
        return *this;
    }
    CompletedFrames(CompletedFrames &&) = default;
    CompletedFrames &operator=(CompletedFrames &&) = default;
    class Lease {
        CompletedFrames *pool_;
        Slot *slot_;
        friend class CompletedFrames;
        Lease(CompletedFrames &pool, Slot &slot) : pool_(&pool), slot_(&slot) {}
        Slot &slot() const {
            if (!slot_)
                throw std::logic_error("released completed frame");
            return *slot_;
        }
        void release() noexcept {
            if (slot_) {
                slot_->active = false;
                slot_ = nullptr;
            }
        }

      public:
        Lease(const Lease &) = delete;
        Lease &operator=(const Lease &) = delete;
        Lease(Lease &&other) noexcept
            : pool_(other.pool_), slot_(std::exchange(other.slot_, nullptr)) {}
        Lease &operator=(Lease &&other) noexcept {
            if (this != &other) {
                release();
                pool_ = other.pool_;
                slot_ = std::exchange(other.slot_, nullptr);
            }
            return *this;
        }
        ~Lease() {
            release();
        }
        bool contains(VertexIndex v) const {
            return slot().membership.contains(v);
        }
        bool insert(VertexIndex v) {
            return slot().membership.insert(v);
        }
        std::size_t size() const {
            return slot().membership.size();
        }
        bool promoted() const {
            return slot().membership.promoted();
        }
        const void *identity() const noexcept {
            return slot_;
        }
        std::size_t pool_retained_bytes() const noexcept {
            return pool_->retained_bytes();
        }
        std::size_t pool_active_bytes() const noexcept {
            return pool_->active_bytes();
        }
    };
    Lease acquire(std::size_t depth, std::size_t vertices) {
        if (depth >= slots_.size())
            slots_.resize(checked_size_add(depth, 1));
        auto &handle = slots_[depth];
        if (!handle)
            handle = std::make_unique<Slot>();
        auto &slot = *handle;
        if (slot.active)
            throw std::logic_error("completed membership frame already active");
        slot.membership.begin(vertices);
        slot.active = true;
        return Lease(*this, slot);
    }
    std::size_t active_count() const noexcept {
        std::size_t n = 0;
        for (const auto &p : slots_)
            n += p && p->active;
        return n;
    }
    std::size_t retained_bytes() const noexcept {
        std::size_t n = slots_.capacity() * sizeof(std::unique_ptr<Slot>);
        for (const auto &p : slots_)
            if (p)
                n += sizeof(Slot) + p->membership.bytes();
        return n;
    }
    std::size_t active_bytes() const noexcept {
        std::size_t n = 0;
        for (const auto &p : slots_)
            if (p && p->active)
                n += sizeof(Slot) + p->membership.bytes();
        return n;
    }
};
using DenseCompletedFrames = CompletedFrames<DenseCompletedStorage, 0>;
using AdaptiveCompletedFrames = CompletedFrames<PagedCompletedStorage, 8>;
} // namespace bmssp::detail
