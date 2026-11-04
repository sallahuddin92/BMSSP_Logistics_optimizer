// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/graph.hpp"
#include <memory>
#include <optional>

namespace bmssp {
// Immutable path snapshots keep saved frontier boundaries stable as labels improve.
struct LabelNode {
    Distance distance;
    std::size_t hops;
    VertexIndex vertex;
    std::optional<EdgeId> edge;
    const LabelNode *parent;
};
struct LabelArena;
class SymbolicLabel {
  public:
    SymbolicLabel() = default; // Positive infinity.
    static SymbolicLabel root(VertexIndex vertex, Distance distance = 0);
    [[nodiscard]] SymbolicLabel extend(const Edge &edge) const;
    [[nodiscard]] SymbolicLabel parent() const {
        return node_ ? SymbolicLabel(arena_, node_->parent) : SymbolicLabel{};
    }
    [[nodiscard]] bool finite() const noexcept {
        return static_cast<bool>(node_);
    }
    [[nodiscard]] Distance distance() const noexcept {
        return node_ ? node_->distance : unreachable;
    }
    [[nodiscard]] const LabelNode *node() const noexcept {
        return node_;
    }
    friend int compare(const SymbolicLabel &a, const SymbolicLabel &b);
    friend bool operator<(const SymbolicLabel &a, const SymbolicLabel &b) {
        return compare(a, b) < 0;
    }
    friend bool operator==(const SymbolicLabel &a, const SymbolicLabel &b) {
        return compare(a, b) == 0;
    }
    friend bool operator<=(const SymbolicLabel &a, const SymbolicLabel &b) {
        return compare(a, b) <= 0;
    }

  private:
    SymbolicLabel(std::shared_ptr<LabelArena> arena, const LabelNode *node)
        : arena_(std::move(arena)), node_(node) {}
    std::shared_ptr<LabelArena> arena_;
    const LabelNode *node_ = nullptr;
};
struct LabelLess {
    bool operator()(const SymbolicLabel &a, const SymbolicLabel &b) const {
        return a < b;
    }
};
} // namespace bmssp
