// SPDX-License-Identifier: Apache-2.0
#pragma once
// Frozen Task 10 FindPivots, 62b2d0d. Container/control flow kept literally;
// only round capture, validation and the local state wrapper are test support.
#include "bmssp/bmssp_2025.hpp"
#include <queue>
#include <unordered_set>
namespace pivot_test {
using namespace bmssp;
struct Round {
    std::vector<VertexIndex> current, next, visited;
};
struct Task10Reference {
    const Graph &graph_;
    std::size_t k_;
    std::vector<SymbolicLabel> labels_;
    BMSSPDiagnostics diagnostics_;
    std::vector<Round> rounds;
    Task10Reference(const Graph &g, std::size_t k, std::vector<SymbolicLabel> labels)
        : graph_(g), k_(k), labels_(std::move(labels)) {}
    static void increment(std::size_t &n, std::size_t amount = 1) {
        n = checked_size_add(n, amount);
    }
    void validate_frontier(const SymbolicLabel &bound,
                           const std::vector<VertexIndex> &frontier) const {
        std::unordered_set<VertexIndex> seen;
        for (auto v : frontier)
            if (v >= labels_.size() || !seen.insert(v).second || !(labels_[v] < bound))
                throw std::invalid_argument("invalid bounded frontier");
    }
    bool relax(const Edge &edge, const SymbolicLabel &bound = {}) {
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
    PivotResult find_pivots(const SymbolicLabel &bound, const std::vector<VertexIndex> &frontier) {
        validate_frontier(bound, frontier);
        increment(diagnostics_.pivot_calls);
        std::vector<VertexIndex> visited = frontier, current = frontier;
        std::unordered_set<VertexIndex> membership(frontier.begin(), frontier.end());
        if (frontier.size() > std::numeric_limits<std::size_t>::max() / k_)
            throw std::length_error("pivot workload overflow");
        const auto limit = k_ * frontier.size();
        for (std::size_t round = 0; round < k_; ++round) {
            std::vector<VertexIndex> next;
            std::unordered_set<VertexIndex> next_members;
            for (const auto u : current)
                for (const auto &edge : graph_.outgoing(u)) {
                    increment(diagnostics_.pivot_edge_scans);
                    // Algorithm 1 updates even above B; only membership expansion is bounded.
                    if (relax(edge) && labels_[edge.to] < bound) {
                        if (next_members.insert(edge.to).second)
                            next.push_back(edge.to);
                    }
                }
            for (const auto v : next)
                if (membership.insert(v).second)
                    visited.push_back(v);
            rounds.push_back({current, next, visited});
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
};
} // namespace pivot_test
