// SPDX-License-Identifier: Apache-2.0
#include "bmssp/symbolic_label.hpp"
#include "bmssp/profile.hpp"
#include <algorithm>
#include <mutex>
#include <type_traits>
namespace bmssp {
struct LabelArena {
    std::mutex mutex;
    // Moving owning handles never moves the separately allocated node arrays.
    // Small initial blocks limit waste for isolated/short queries; large queries
    // amortize allocation and destruction over bounded 4096-node slabs.
    std::vector<std::unique_ptr<LabelNode[]>> blocks;
    LabelNode *current = nullptr;
    std::size_t capacity = 0, used = 0;
    const LabelNode *allocate(LabelNode value) {
        ProfileScope scope(ProfilePart::labels);
        std::lock_guard<std::mutex> lock(mutex);
        if (used == capacity) {
            const auto next =
                capacity == 0 ? std::size_t{32} : std::min(capacity * 2, std::size_t{4096});
            auto block = std::make_unique_for_overwrite<LabelNode[]>(next);
            // A failed array allocation or handle-vector growth leaves every
            // published node and the previous allocation cursor unchanged.
            blocks.push_back(std::move(block));
            current = blocks.back().get();
            capacity = next;
            used = 0;
        }
        static_assert(std::is_nothrow_copy_assignable_v<LabelNode>);
        auto *result = current + used;
        *result = value; // Publish only after complete initialization under lock.
        ++used;
        return result;
    }
};
SymbolicLabel SymbolicLabel::root(VertexIndex vertex, Distance distance) {
    if (!std::isfinite(distance) || distance < 0)
        throw std::invalid_argument("invalid root label");
    auto arena = std::make_shared<LabelArena>();
    const auto *node = arena->allocate({distance, 0, vertex, std::nullopt, nullptr});
    return SymbolicLabel(std::move(arena), node);
}
LabelNode SymbolicLabel::extension_node(const Edge &edge) const {
    if (!node_ || node_->vertex != edge.from)
        throw std::invalid_argument("label/edge endpoint mismatch");
    // Preserve distance then hop validation even when a scalar bound could reject.
    return {checked_distance_add(node_->distance, edge.weight), checked_size_add(node_->hops, 1),
            edge.to, edge.id, node_};
}
SymbolicLabel SymbolicLabel::materialize(const LabelNode &value) const {
    return SymbolicLabel(arena_, arena_->allocate(value));
}
SymbolicLabel SymbolicLabel::extend(const Edge &edge) const {
    return materialize(extension_node(edge));
}
namespace {
int compare_unprofiled(const LabelNode *a, const LabelNode *b) {
    if (a == b)
        return 0;
    if (!a)
        return 1;
    if (!b)
        return -1;
    const auto scalar = [](auto x, auto y) { return x < y ? -1 : (y < x ? 1 : 0); };
    if (const auto c = scalar(a->distance, b->distance); c != 0)
        return c;
    if (const auto c = scalar(a->hops, b->hops); c != 0)
        return c;
    auto x = a, y = b;
    while (x && y && x != y) {
        if (const auto c = scalar(x->vertex, y->vertex); c != 0)
            return c;
        x = x->parent;
        y = y->parent;
    }
    // Parallel edges are a deterministic final refinement after the paper's vertex order.
    x = a;
    y = b;
    while (x && y && x != y) {
        if (const auto c = scalar(x->edge, y->edge); c != 0)
            return c;
        x = x->parent;
        y = y->parent;
    }
    return 0;
}
// Keep timing/bookkeeping off the ordinary comparison's stack frame.
#if defined(__GNUC__) || defined(__clang__)
__attribute__((noinline))
#endif
int compare_profiled(const LabelNode *a, const LabelNode *b) {
    ProfileScope scope(ProfilePart::comparison);
    return compare_unprofiled(a, b);
}
} // namespace
int SymbolicLabel::compare_nodes(const LabelNode *a, const LabelNode *b) {
    if (!active_profile)
        return compare_unprofiled(a, b);
    return compare_profiled(a, b);
}

int compare(const SymbolicLabel &a, const SymbolicLabel &b) {
    return SymbolicLabel::compare_nodes(a.node_, b.node_);
}
} // namespace bmssp
