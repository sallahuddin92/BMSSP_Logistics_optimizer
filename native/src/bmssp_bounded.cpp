// SPDX-License-Identifier: Apache-2.0
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/profile.hpp"
#include <algorithm>
#include <queue>
#include <sstream>
#include <unordered_set>
namespace bmssp {
namespace {
void increment(std::size_t &n, std::size_t amount = 1) {
    n = checked_size_add(n, amount);
}
} // namespace
BMSSPWorkspace::BMSSPWorkspace(Graph graph, ExternalVertexId source, std::size_t k, std::size_t t,
                               BMSSPOptions options)
    : graph_(std::move(graph)), k_(k), t_(t), options_(std::move(options)) {
    if (k_ == 0 || t_ == 0)
        throw std::invalid_argument("k and t must be positive");
    std::vector<std::size_t> indegree(graph_.vertex_count(), 0);
    for (VertexIndex u = 0; u < graph_.vertex_count(); ++u) {
        if (graph_.outgoing(u).size() > 2)
            throw std::invalid_argument("bounded routines require degree-reduced graph");
        for (const auto &e : graph_.outgoing(u))
            if (++indegree[e.to] > 2)
                throw std::invalid_argument("bounded routines require degree-reduced graph");
    }
    validation_seen_.resize(graph_.vertex_count());
    reset(source);
}
void BMSSPWorkspace::reset(ExternalVertexId source) {
    validate_numeric_environment();
    const auto s = graph_.vertex_index(source);
    base_heap_.clear();
    labels_.assign(graph_.vertex_count(), {});
    labels_[s] = SymbolicLabel::root(s);
    diagnostics_ = {};
    diagnostics_.k = k_;
    diagnostics_.t = t_;
    diagnostics_.label_nodes_created = 1;
    depth_ = 0;
}
void BMSSPWorkspace::validate_frontier(const SymbolicLabel &bound,
                                       const std::vector<VertexIndex> &frontier) const {
    // No mark is consumed after this validation returns. Parent/child calls may
    // therefore reuse the scratch, unlike their live completed/pivot collections.
    validation_seen_.begin();
    for (const auto v : frontier)
        if (v >= labels_.size() || !validation_seen_.insert(v) || !(labels_[v] < bound))
            throw std::invalid_argument("invalid bounded frontier");
}
bool BMSSPWorkspace::relax(const Edge &edge, const SymbolicLabel &bound) {
    increment(diagnostics_.relaxed_edges);
    if (!labels_.at(edge.from).finite())
        return false;
    const auto candidate = labels_[edge.from].extend(edge);
    increment(diagnostics_.label_nodes_created);
    if (!(candidate < bound))
        return false;
    const auto c = compare(candidate, labels_.at(edge.to));
    if (c > 0)
        return false;
    if (c < 0) {
        labels_[edge.to] = candidate;
        increment(diagnostics_.label_updates);
    } else
        increment(diagnostics_.equality_relaxations);
    return true;
}
BoundedResult BMSSPWorkspace::base_case(const SymbolicLabel &bound,
                                        const std::vector<VertexIndex> &frontier) {
    ProfileScope scope(ProfilePart::base);
    validate_frontier(bound, frontier);
    if (frontier.size() != 1)
        throw std::invalid_argument("BaseCase requires singleton frontier");
    increment(diagnostics_.base_calls);
    detail::BaseCaseHeap::Use heap_use(base_heap_);
    auto &heap = base_heap_;
    heap.push({frontier[0], labels_[frontier[0]]});
    // Allocate only when a query reaches a BaseCase.
    if (base_extracted_.size() != graph_.vertex_count())
        base_extracted_.resize(graph_.vertex_count());
    base_extracted_.begin();
    auto &extracted = base_extracted_;
    std::vector<VertexIndex> completed;
    while (!heap.empty() && completed.size() < checked_size_add(k_, 1)) {
        const auto item = heap.top();
        heap.pop();
        if (!(item.value == labels_[item.key]) || !extracted.insert(item.key))
            continue;
        completed.push_back(item.key);
        for (const auto &edge : graph_.outgoing(item.key))
            if (relax(edge, bound) && !extracted.contains(edge.to))
                heap.push({edge.to, labels_[edge.to]});
    }
    if (completed.size() <= k_)
        return {bound, std::move(completed)};
    auto boundary = labels_[completed[0]];
    for (const auto v : completed)
        if (boundary < labels_[v])
            boundary = labels_[v];
    std::erase_if(completed, [&](auto v) { return !(labels_[v] < boundary); });
    return {boundary, std::move(completed)};
}
PivotResult BMSSPWorkspace::find_pivots(const SymbolicLabel &bound,
                                        const std::vector<VertexIndex> &frontier) {
    ProfileScope scope(ProfilePart::pivots);
    detail::PivotScratch<>::Use scratch_use(pivot_scratch_);
    validate_frontier(bound, frontier);
    increment(diagnostics_.pivot_calls);
    std::vector<VertexIndex> visited = frontier, current = frontier;
    if (pivot_scratch_.visited.size() != graph_.vertex_count())
        pivot_scratch_.visited.resize(graph_.vertex_count());
    pivot_scratch_.visited.begin();
    for (const auto v : frontier)
        (void)pivot_scratch_.visited.insert(v);
    auto &membership = pivot_scratch_.visited;
    if (frontier.size() > std::numeric_limits<std::size_t>::max() / k_)
        throw std::length_error("pivot workload overflow");
    const auto limit = k_ * frontier.size();
    for (std::size_t round = 0; round < k_; ++round) {
        std::vector<VertexIndex> next;
        if (pivot_scratch_.round.size() != graph_.vertex_count())
            pivot_scratch_.round.resize(graph_.vertex_count());
        pivot_scratch_.round.begin();
        auto &next_members = pivot_scratch_.round;
        for (const auto u : current)
            for (const auto &edge : graph_.outgoing(u)) {
                increment(diagnostics_.pivot_edge_scans);
                // Algorithm 1 updates even above B; only membership expansion is bounded.
                if (relax(edge) && labels_[edge.to] < bound) {
                    if (next_members.insert(edge.to))
                        next.push_back(edge.to);
                }
            }
        for (const auto v : next)
            if (membership.insert(v))
                visited.push_back(v);
        if (visited.size() > limit) {
            increment(diagnostics_.pivot_early_returns);
            increment(diagnostics_.pivots_selected, frontier.size());
            return {frontier, std::move(visited), true};
        }
        current = std::move(next);
    }
    std::unordered_map<VertexIndex, VertexIndex> parent;
    std::unordered_map<VertexIndex, std::size_t> subtree;
    std::unordered_map<VertexIndex, std::size_t> children;
    for (const auto v : visited) {
        subtree[v] = 1;
        children.try_emplace(v, 0);
        const auto node = labels_[v].node();
        if (node->parent && membership.contains(node->parent->vertex)) {
            const auto p = node->parent->vertex;
            // The selected predecessor edge is tight only with the current parent label.
            if (labels_[v].parent() == labels_[p]) {
                parent.emplace(v, p);
                ++children[p];
            }
        }
    }
    std::queue<VertexIndex> leaves;
    for (const auto v : visited)
        if (children[v] == 0)
            leaves.push(v);
    std::size_t processed = 0;
    while (!leaves.empty()) {
        const auto v = leaves.front();
        leaves.pop();
        ++processed;
        if (const auto p = parent.find(v); p != parent.end()) {
            subtree[p->second] = checked_size_add(subtree[p->second], subtree[v]);
            if (--children[p->second] == 0)
                leaves.push(p->second);
        }
    }
    if (processed != visited.size())
        throw std::logic_error("pivot predecessor forest contains a cycle");
    std::vector<VertexIndex> pivots;
    for (const auto v : frontier)
        if (!parent.contains(v) && subtree[v] >= k_)
            pivots.push_back(v);
    increment(diagnostics_.pivots_selected, pivots.size());
    return {std::move(pivots), std::move(visited), false};
}
std::size_t BMSSPWorkspace::power(std::size_t exp) const {
    const auto cap = checked_size_add(graph_.vertex_count(), 1);
    std::size_t result = 1;
    while (exp-- != 0) {
        if (result > cap / 2)
            return cap;
        result *= 2;
    }
    return result;
}
std::size_t BMSSPWorkspace::exponent(std::size_t level) const {
    if (level > std::numeric_limits<std::size_t>::max() / t_)
        throw std::length_error("recursion exponent overflow");
    return level * t_;
}
BoundedResult BMSSPWorkspace::run(std::size_t level, const SymbolicLabel &bound,
                                  const std::vector<VertexIndex> &frontier) {
    ProfileScope scope(ProfilePart::recursion);
    validate_frontier(bound, frontier);
    if (level > std::numeric_limits<std::size_t>::digits ||
        frontier.size() > power(exponent(level)))
        throw std::invalid_argument("bounded level/cardinality violation");
    const auto before = options_.observer ? labels_ : std::vector<SymbolicLabel>{};
    increment(diagnostics_.recursive_calls);
    diagnostics_.max_recursion_depth = std::max(diagnostics_.max_recursion_depth, depth_);
    const auto call_depth = depth_;
    const auto finish = [&](BoundedResult result) {
        increment(diagnostics_.completed_vertex_events, result.completed.size());
        if (options_.observer)
            options_.observer({level, call_depth, bound, frontier, before, labels_, result});
        return result;
    };
    if (frontier.empty())
        return finish({bound, {}});
    if (level == 0)
        return finish(base_case(bound, frontier));
    auto pivots = find_pivots(bound, frontier);
    BoundedFrontier data(power(exponent(level - 1)), bound, diagnostics_.frontier,
                         options_.validate_frontier_operations);
    auto boundary = bound;
    for (const auto p : pivots.pivots) {
        data.insert(p, labels_[p]);
        if (labels_[p] < boundary)
            boundary = labels_[p];
    }
    const auto cap = checked_size_add(graph_.vertex_count(), 1), scale = power(exponent(level));
    const auto workload = k_ > cap / scale ? cap : std::min(cap, k_ * scale);
    std::vector<VertexIndex> complete;
    auto complete_members = complete_frames_.acquire(depth_, graph_.vertex_count());
    while (complete.size() < workload && !data.empty()) {
        auto pulled = data.pull();
        std::vector<VertexIndex> children;
        for (const auto &e : pulled.entries) {
            if (complete_members.contains(e.key))
                throw std::logic_error("stale completed frontier entry key=" +
                                       std::to_string(e.key));
            children.push_back(e.key);
        }
        ++depth_;
        BoundedResult child;
        try {
            child = run(level - 1, pulled.bound, children);
        } catch (...) {
            --depth_;
            throw;
        }
        --depth_;
        if (child.bound < boundary || pulled.bound < child.bound) {
            const auto show = [](const SymbolicLabel &x) {
                std::ostringstream out;
                out << x.distance();
                if (x.finite())
                    out << ":" << x.node()->hops << ":" << x.node()->vertex;
                return out.str();
            };
            throw std::logic_error("nonmonotone recursive boundary level=" + std::to_string(level) +
                                   " previous=" + show(boundary) + " child=" + show(child.bound) +
                                   " pulled=" + show(pulled.bound));
        }
        if (child.completed.empty())
            throw std::logic_error("recursive call made no progress");
        boundary = child.bound;
        for (const auto u : child.completed) {
            if (!complete_members.insert(u))
                throw std::logic_error("completed child sets overlap");
            complete.push_back(u);
            // Nested calls can settle a key still stored with an older larger
            // snapshot in this frame. Retire it using the structure's Delete.
            data.discard(u);
        }
        std::vector<FrontierEntry> prepend;
        for (const auto u : child.completed)
            for (const auto &edge : graph_.outgoing(u))
                if (relax(edge)) {
                    const auto value = labels_[edge.to];
                    if (!(value < pulled.bound) && value < bound)
                        data.insert(edge.to, value);
                    else if (!(value < child.bound) && value < pulled.bound)
                        prepend.push_back({edge.to, value});
                }
        for (const auto x : children)
            if (!(labels_[x] < child.bound) && labels_[x] < pulled.bound)
                prepend.push_back({x, labels_[x]});
        data.batch_prepend(std::move(prepend));
    }
    if (data.empty())
        boundary = bound;
    for (const auto x : pivots.visited)
        if (labels_[x] < boundary && complete_members.insert(x))
            complete.push_back(x);
    return finish({boundary, std::move(complete)});
}
} // namespace bmssp
