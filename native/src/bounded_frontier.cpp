// SPDX-License-Identifier: Apache-2.0
#include "bmssp/bounded_frontier.hpp"
#include <algorithm>
#include <functional>
#include <unordered_set>
namespace bmssp {
namespace {
bool less_entry(const FrontierEntry &a, const FrontierEntry &b) {
    return a.value < b.value;
}
// Deterministic median-of-medians selection, not a full frontier sort or binary heap.
void linear_select(std::vector<FrontierEntry> &a, std::size_t nth, FrontierCounters &count) {
    if (nth >= a.size())
        throw std::out_of_range("selection index");
    count.selection_work = checked_size_add(count.selection_work, a.size());
    if (a.size() <= 5) {
        std::sort(a.begin(), a.end(), less_entry);
        return;
    }
    std::vector<FrontierEntry> medians;
    for (std::size_t first = 0; first < a.size();) {
        const auto end = first + std::min(std::size_t{5}, a.size() - first);
        std::sort(a.begin() + static_cast<std::ptrdiff_t>(first),
                  a.begin() + static_cast<std::ptrdiff_t>(end), less_entry);
        medians.push_back(a[first + (end - first) / 2]);
        first = end;
    }
    linear_select(medians, medians.size() / 2, count);
    const auto pivot = medians[medians.size() / 2].value;
    std::vector<FrontierEntry> low, equal, high;
    for (auto &e : a) {
        const auto c = compare(e.value, pivot);
        (c < 0 ? low : (c == 0 ? equal : high)).push_back(std::move(e));
    }
    if (nth < low.size())
        linear_select(low, nth, count);
    else if (nth >= low.size() + equal.size())
        linear_select(high, nth - low.size() - equal.size(), count);
    a.clear();
    for (auto *group : {&low, &equal, &high})
        for (auto &e : *group)
            a.push_back(std::move(e));
}
} // namespace
BoundedFrontier::BoundedFrontier(std::size_t m, SymbolicLabel bound, FrontierCounters &counters,
                                 bool checks)
    : m_(m), bound_(std::move(bound)), counters_(counters), checks_(checks) {
    initialize(m_, bound_);
}
void BoundedFrontier::initialize(std::size_t m, SymbolicLabel bound) {
    if (m == 0)
        throw std::invalid_argument("frontier block size must be positive");
    m_ = m;
    bound_ = std::move(bound);
    locations_.clear();
    fences_.clear();
    d0_.clear();
    d1_.clear();
    d1_.push_back({{}, bound_});
    fences_.emplace(bound_, d1_.begin());
    counters_.initializations = checked_size_add(counters_.initializations, 1);
}
void BoundedFrontier::discard(VertexIndex key) {
    if (locations_.contains(key)) {
        erase(key);
        counters_.discards = checked_size_add(counters_.discards, 1);
    }
}
void BoundedFrontier::erase(VertexIndex key) {
    const auto found = locations_.find(key);
    if (found == locations_.end())
        return;
    const auto location = found->second;
    location.block->entries.erase(location.entry);
    locations_.erase(found);
    if (location.block->entries.empty()) {
        if (location.prepend)
            d0_.erase(location.block);
        else {
            fences_.erase(location.block->fence);
            d1_.erase(location.block);
        }
    }
}
void BoundedFrontier::fill(Blocks::iterator block, bool prepend,
                           std::vector<FrontierEntry> entries) {
    for (auto &e : entries) {
        block->entries.push_back(std::move(e));
        auto it = std::prev(block->entries.end());
        locations_.insert_or_assign(it->key, Location{prepend, block, it});
    }
    counters_.peak_keys = std::max(counters_.peak_keys, locations_.size());
}
void BoundedFrontier::select(std::vector<FrontierEntry> &entries, std::size_t nth) {
    linear_select(entries, nth, counters_);
}
void BoundedFrontier::split(Blocks::iterator block) {
    std::vector<FrontierEntry> entries(block->entries.begin(), block->entries.end());
    select(entries, entries.size() / 2);
    const auto half = entries.size() / 2;
    std::vector<FrontierEntry> low(entries.begin(),
                                   entries.begin() + static_cast<std::ptrdiff_t>(half));
    std::vector<FrontierEntry> high(entries.begin() + static_cast<std::ptrdiff_t>(half),
                                    entries.end());
    const auto low_fence = std::max_element(low.begin(), low.end(), less_entry)->value;
    const auto left = d1_.insert(block, Block{{}, low_fence});
    fences_.emplace(low_fence, left);
    block->entries.clear();
    fill(left, false, std::move(low));
    fill(block, false, std::move(high));
    counters_.splits = checked_size_add(counters_.splits, 1);
}
void BoundedFrontier::insert(VertexIndex key, const SymbolicLabel &value) {
    counters_.inserts = checked_size_add(counters_.inserts, 1);
    if (!value.finite() || value.node()->vertex != key || !(value < bound_))
        throw std::invalid_argument("invalid frontier key/value/bound");
    if (const auto old = locations_.find(key); old != locations_.end()) {
        if (!(value < old->second.entry->value))
            return;
        erase(key);
    }
    if (d1_.empty()) {
        d1_.push_back({{}, bound_});
        fences_.emplace(bound_, d1_.begin());
    }
    auto fence = fences_.lower_bound(value);
    // Deleting an empty rightmost block can remove the B fence while earlier
    // blocks survive. A later larger insertion needs a fresh terminal block.
    if (fence == fences_.end()) {
        d1_.push_back({{}, bound_});
        fence = fences_.emplace(bound_, std::prev(d1_.end())).first;
    }
    const auto block = fence->second;
    fill(block, false, {{key, value}});
    if (block->entries.size() > m_)
        split(block);
    if (checks_)
        validate();
}
SymbolicLabel BoundedFrontier::minimum() const {
    auto result = bound_;
    for (const auto *seq : {&d0_, &d1_})
        if (!seq->empty())
            for (const auto &e : seq->front().entries)
                if (e.value < result)
                    result = e.value;
    return result;
}
void BoundedFrontier::prepend_partition(std::vector<FrontierEntry> entries, std::size_t limit) {
    if (entries.empty())
        return;
    if (entries.size() <= limit) {
        const auto block = d0_.insert(d0_.begin(), Block{});
        fill(block, true, std::move(entries));
        return;
    }
    select(entries, entries.size() / 2);
    const auto half = entries.size() / 2;
    std::vector<FrontierEntry> low(entries.begin(),
                                   entries.begin() + static_cast<std::ptrdiff_t>(half));
    std::vector<FrontierEntry> high(entries.begin() + static_cast<std::ptrdiff_t>(half),
                                    entries.end());
    prepend_partition(std::move(high), limit);
    prepend_partition(std::move(low), limit);
}
void BoundedFrontier::batch_prepend(std::vector<FrontierEntry> batch) {
    counters_.batches = checked_size_add(counters_.batches, 1);
    std::vector<FrontierEntry> unique;
    std::unordered_map<VertexIndex, std::size_t> indices;
    for (auto &e : batch) {
        if (!e.value.finite() || e.value.node()->vertex != e.key || !(e.value < bound_))
            throw std::invalid_argument("invalid prepend entry");
        const auto [it, added] = indices.emplace(e.key, unique.size());
        if (added)
            unique.push_back(std::move(e));
        else if (e.value < unique[it->second].value)
            unique[it->second] = std::move(e);
    }
    if (checks_) {
        const auto min = minimum();
        for (const auto &e : unique)
            if (!(e.value < min))
                throw std::invalid_argument("BatchPrepend order precondition violated");
    }
    std::vector<FrontierEntry> accepted;
    for (auto &e : unique) {
        if (const auto old = locations_.find(e.key);
            old != locations_.end() && !(e.value < old->second.entry->value))
            continue;
        erase(e.key);
        accepted.push_back(std::move(e));
    }
    const auto limit = accepted.size() <= m_ ? m_ : std::max(std::size_t{1}, m_ / 2 + m_ % 2);
    prepend_partition(std::move(accepted), limit);
    if (checks_)
        validate();
}
FrontierPull BoundedFrontier::pull() {
    counters_.pulls = checked_size_add(counters_.pulls, 1);
    std::vector<FrontierEntry> candidates;
    for (const auto *seq : {&d0_, &d1_}) {
        std::size_t collected = 0;
        for (auto it = seq->begin(); it != seq->end() && collected < m_; ++it) {
            for (const auto &e : it->entries)
                candidates.push_back(e);
            collected = checked_size_add(collected, it->entries.size());
        }
    }
    if (candidates.size() > m_) {
        select(candidates, m_);
        candidates.resize(m_);
    }
    for (const auto &e : candidates)
        erase(e.key);
    counters_.pulled_keys = checked_size_add(counters_.pulled_keys, candidates.size());
    const auto bound = minimum();
    if (checks_)
        validate();
    return {bound, std::move(candidates)};
}
void BoundedFrontier::validate() const {
    std::unordered_set<VertexIndex> keys;
    for (const auto *seq : {&d0_, &d1_}) {
        SymbolicLabel previous;
        bool first = true;
        for (auto it = seq->begin(); it != seq->end(); ++it) {
            if (it->entries.size() > m_)
                throw std::logic_error("oversized block");
            auto maximum = SymbolicLabel::root(0, 0);
            bool any = false;
            for (const auto &e : it->entries) {
                if (!keys.insert(e.key).second || !(e.value < bound_))
                    throw std::logic_error("invalid frontier entries");
                if (!first && !(previous < e.value))
                    throw std::logic_error("unordered block sequence");
                if (seq == &d1_ && it->fence < e.value)
                    throw std::logic_error("value exceeds block fence");
                if (!any || maximum < e.value)
                    maximum = e.value;
                any = true;
                const auto loc = locations_.find(e.key);
                if (loc == locations_.end() || &*loc->second.block != &*it ||
                    &*loc->second.entry != &e)
                    throw std::logic_error("invalid key index");
            }
            if (any) {
                previous = maximum;
                first = false;
            }
            if (seq == &d1_) {
                const auto fence = fences_.find(it->fence);
                if (fence == fences_.end() || &*fence->second != &*it)
                    throw std::logic_error("invalid fence index");
            }
        }
    }
    if (keys.size() != locations_.size() || fences_.size() != d1_.size())
        throw std::logic_error("frontier index count mismatch");
}
} // namespace bmssp
