// SPDX-License-Identifier: Apache-2.0
#include "bmssp/symbolic_label.hpp"
#include "bmssp/profile.hpp"
#include <mutex>
namespace bmssp {
struct LabelArena {
    std::mutex mutex;
    std::vector<std::unique_ptr<LabelNode>> nodes;
    const LabelNode *allocate(LabelNode value) {
        ProfileScope scope(ProfilePart::labels);
        auto node = std::make_unique<LabelNode>(std::move(value));
        const auto *result = node.get();
        std::lock_guard<std::mutex> lock(mutex);
        nodes.push_back(std::move(node));
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
SymbolicLabel SymbolicLabel::extend(const Edge &edge) const {
    if (!node_ || node_->vertex != edge.from)
        throw std::invalid_argument("label/edge endpoint mismatch");
    return SymbolicLabel(arena_, arena_->allocate(LabelNode{
                                     checked_distance_add(node_->distance, edge.weight),
                                     checked_size_add(node_->hops, 1), edge.to, edge.id, node_}));
}
int compare(const SymbolicLabel &a, const SymbolicLabel &b) {
    ProfileScope scope(ProfilePart::comparison);
    if (a.node_ == b.node_)
        return 0;
    if (!a.node_)
        return 1;
    if (!b.node_)
        return -1;
    const auto scalar = [](auto x, auto y) { return x < y ? -1 : (y < x ? 1 : 0); };
    if (const auto c = scalar(a.node_->distance, b.node_->distance); c != 0)
        return c;
    if (const auto c = scalar(a.node_->hops, b.node_->hops); c != 0)
        return c;
    auto x = a.node_, y = b.node_;
    while (x && y && x != y) {
        if (const auto c = scalar(x->vertex, y->vertex); c != 0)
            return c;
        x = x->parent;
        y = y->parent;
    }
    // Parallel edges are a deterministic final refinement after the paper's vertex order.
    x = a.node_;
    y = b.node_;
    while (x && y && x != y) {
        if (const auto c = scalar(x->edge, y->edge); c != 0)
            return c;
        x = x->parent;
        y = y->parent;
    }
    return 0;
}
} // namespace bmssp
