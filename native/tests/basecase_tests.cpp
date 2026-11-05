// SPDX-License-Identifier: Apache-2.0
#include "../test_support/allocation_tracking.hpp"
#include "bmssp/detail/basecase_heap.hpp"
#include "bmssp_oracle.hpp"
#include <future>
#include <queue>
#include <random>
using namespace bmssp;
namespace {
// Literal Task 9 mini-Dijkstra container/control-flow model (5c42a3f).
// Full-vector Bellman-Ford below is independent of both this model and the engine.
struct Reference {
    std::vector<SymbolicLabel> labels;
    std::vector<VertexIndex> sequence;
    std::size_t stale = 0, duplicates = 0, equal = 0, updates = 0, scans = 0;
    BoundedResult result;
};
Reference task9(const Graph &g, std::vector<SymbolicLabel> labels, std::size_t k,
                const SymbolicLabel &bound, VertexIndex source) {
    Reference r;
    struct Item {
        VertexIndex key;
        SymbolicLabel value;
    };
    const auto greater = [](const Item &a, const Item &b) { return b.value < a.value; };
    std::priority_queue<Item, std::vector<Item>, decltype(greater)> heap(greater);
    heap.push({source, labels[source]});
    std::unordered_set<VertexIndex> extracted;
    std::vector<VertexIndex> completed;
    while (!heap.empty() && completed.size() < checked_size_add(k, 1)) {
        const auto item = heap.top();
        heap.pop();
        if (!(item.value == labels[item.key])) {
            ++r.stale;
            continue;
        }
        if (!extracted.insert(item.key).second) {
            ++r.duplicates;
            continue;
        }
        completed.push_back(item.key);
        for (const auto &edge : g.outgoing(item.key)) {
            ++r.scans;
            const auto candidate = labels[edge.from].extend(edge);
            if (!(candidate < bound))
                continue;
            const auto c = compare(candidate, labels[edge.to]);
            if (c > 0)
                continue;
            if (c < 0) {
                labels[edge.to] = candidate;
                ++r.updates;
            } else
                ++r.equal;
            if (!extracted.contains(edge.to))
                heap.push({edge.to, labels[edge.to]});
        }
    }
    r.sequence = completed;
    if (completed.size() <= k)
        r.result = {bound, std::move(completed)};
    else {
        auto boundary = labels[completed[0]];
        for (const auto v : completed)
            if (boundary < labels[v])
                boundary = labels[v];
        std::erase_if(completed, [&](auto v) { return !(labels[v] < boundary); });
        r.result = {boundary, std::move(completed)};
    }
    r.labels = std::move(labels);
    return r;
}
void same(const Reference &r, const BoundedResult &actual, const std::vector<SymbolicLabel> &labels,
          const SymbolicLabel &input_bound) {
    CHECK(actual.bound == r.result.bound);
    CHECK(actual.completed == r.result.completed);
    auto sequence = actual.completed;
    // Distinct extracted vertices have distinct symbolic labels; a partial
    // return removes exactly its final (maximum) extracted label.
    if (!(actual.bound == input_bound))
        sequence.push_back(actual.bound.node()->vertex);
    CHECK(sequence == r.sequence);
    CHECK(labels.size() == r.labels.size());
    for (std::size_t v = 0; v < labels.size(); ++v)
        CHECK(independent::compare(independent::view(labels[v]), independent::view(r.labels[v])) ==
              0);
}
Graph chain(std::size_t n) {
    std::vector<ExternalVertexId> ids;
    std::vector<InputEdge> edges;
    for (std::size_t i = 0; i < n; ++i) {
        ids.push_back(static_cast<ExternalVertexId>(i));
        if (i)
            edges.push_back({static_cast<EdgeId>(i), ids[i - 1], ids[i], 0});
    }
    return {ids, edges};
}
void check(const Graph &g, VertexIndex s, std::size_t k, SymbolicLabel bound = {}) {
    BMSSPWorkspace w(g, g.external_id(s), k, 2);
    const auto r = task9(g, w.labels(), k, bound, s);
    const auto actual = w.base_case(bound, {s});
    same(r, actual, w.labels(), bound);
    CHECK(w.diagnostics().relaxed_edges == r.scans);
    CHECK(w.diagnostics().equality_relaxations == r.equal);
    CHECK(w.diagnostics().label_updates == r.updates);
    const auto exact = independent::truth(g, s);
    independent::bounded_contract({0,
                                   0,
                                   bound,
                                   {s},
                                   [&] {
                                       std::vector<SymbolicLabel> x(g.vertex_count());
                                       x[s] = SymbolicLabel::root(s);
                                       return x;
                                   }(),
                                   w.labels(),
                                   actual},
                                  exact);
}
} // namespace
int main() {
    test::run("task9_bounds_k1_large_stale_ties_zero_sinks", [] {
        const Graph g({0, 1, 2, 3, 4, 5}, {{0, 0, 1, 10},
                                           {1, 0, 2, 1},
                                           {2, 2, 1, 1},
                                           {3, 1, 3, 0},
                                           {4, 2, 4, 1},
                                           {5, 3, 4, 0},
                                           {6, 4, 3, 0}});
        BMSSPWorkspace w(g, 0, 20, 1);
        const auto r = task9(g, w.labels(), 20, {}, 0);
        CHECK(r.stale > 0);
        for (VertexIndex s = 0; s < g.vertex_count(); ++s)
            for (std::size_t k : {1U, 2U, 20U}) {
                check(g, s, k);
                check(g, s, k, SymbolicLabel::root(s, 2));
            }
        const auto z = chain(12);
        auto symbolic = SymbolicLabel::root(0);
        for (VertexIndex v = 1; v < 5; ++v)
            symbolic = symbolic.extend(z.outgoing(v - 1).front());
        check(z, 0, 1, symbolic);
        check(z, 0, 20, symbolic);
    });
    test::run("equality_valid_and_returned_ownership_reset", [] {
        const auto g = chain(80);
        BMSSPWorkspace w(g, 0, 4, 2);
        CHECK(w.relax(g.outgoing(0).front()));
        const auto r = task9(g, w.labels(), 4, {}, 0);
        CHECK(r.equal > 0);
        const auto first = w.base_case({}, {0});
        same(r, first, w.labels(), {});
        CHECK(w.diagnostics().equality_relaxations == r.equal);
        const auto saved = first.completed;
        const auto saved_bound = first.bound;
        for (std::size_t i = 0; i < 400; ++i) {
            w.reset(0);
            const auto next = w.base_case({}, {0});
            CHECK(next.completed == saved);
            CHECK(first.completed == saved);
            CHECK(first.bound == saved_bound);
        }
        w.reset(79);
        CHECK(w.base_case({}, {79}).completed == std::vector<VertexIndex>{79});
        w.reset(0);
        test::throws<std::invalid_argument>([&] { (void)w.base_case({}, {0, 0}); });
        CHECK(w.base_case({}, {0}).completed == saved);
    });
    test::run("heap_order_duplicates_unbounded_growth_failure_cleanup", [] {
        detail::BaseCaseHeap h;
        const auto root = SymbolicLabel::root(0);
        std::priority_queue<detail::BaseCaseHeap::Item, std::vector<detail::BaseCaseHeap::Item>,
                            detail::BaseCaseHeap::Greater>
            old;
        {
            detail::BaseCaseHeap::Use use(h);
            for (VertexIndex i = 0; i < 300; ++i) {
                const auto value =
                    root.extend({static_cast<EdgeId>(i), 0, i, static_cast<double>(i % 7)});
                h.push({i, value});
                old.push({i, value});
                h.push({i, value});
                old.push({i, value});
            }
            CHECK(h.size() == 600);
            CHECK(h.capacity() >= 600);
            detail::DenseMarks<> extracted(300);
            std::size_t unique = 0, duplicates = 0;
            while (!old.empty()) {
                CHECK(h.top().key == old.top().key);
                CHECK(h.top().value == old.top().value);
                if (extracted.insert(h.top().key))
                    ++unique;
                else
                    ++duplicates;
                h.pop();
                old.pop();
            }
            CHECK(unique == 300);
            CHECK(duplicates == 300);
        }
        const auto capacity = h.capacity();
        CHECK(h.empty());
        {
            detail::BaseCaseHeap::Use use(h);
            h.push({0, root});
            CHECK(h.capacity() == capacity);
        }
        // Force vector allocation, with no label creation in the failing region.
        detail::BaseCaseHeap fresh;
        bool failed = false;
        try {
            detail::BaseCaseHeap::Use use(fresh);
            fresh.push({0, root});
            allocation_probe::FailAfter fail(0);
            for (std::size_t i = 0; i < 10000; ++i)
                fresh.push({0, root});
        } catch (const std::bad_alloc &) {
            failed = true;
        }
        CHECK(failed);
        CHECK(fresh.empty());
        {
            detail::BaseCaseHeap::Use use(fresh);
            fresh.push({0, root});
            CHECK(fresh.top().value == root);
        }
        CHECK(fresh.empty());
    });
    test::run("workspace_failure_recovery_and_dense_epoch_wrap", [] {
        const auto g = chain(120);
        std::size_t failures = 0;
        for (std::size_t fail = 0; fail < 30; ++fail) {
            BMSSPWorkspace w(g, 0, 20, 2);
            const std::vector<VertexIndex> frontier{0};
            bool failed = false;
            try {
                allocation_probe::FailAfter inject(fail);
                (void)w.base_case({}, frontier);
            } catch (const std::bad_alloc &) {
                failed = true;
            }
            if (failed)
                ++failures;
            w.reset(0);
            const auto r = task9(g, w.labels(), 20, {}, 0);
            same(r, w.base_case({}, frontier), w.labels(), {});
        }
        CHECK(failures >= 4);
        detail::DenseMarks<std::uint8_t> m(4);
        for (std::size_t i = 0; i < 1024; ++i) {
            m.begin();
            CHECK(!m.contains(3));
            CHECK(m.insert(3));
            CHECK(m.contains(3));
            CHECK(!m.insert(3));
        }
        test::throws<std::out_of_range>([&] { (void)m.contains(4); });
        test::throws<std::out_of_range>([&] { (void)m.insert(4); });
        m.resize(2);
        CHECK(m.size() == 2);
        CHECK(!m.contains(1));
    });
    test::run("recursive_leaf_task9_differential_random_independent_oracle", [] {
        std::mt19937 random(10025);
        std::size_t leaves = 0, deep = 0;
        for (std::size_t round = 0; round < 30; ++round) {
            std::vector<ExternalVertexId> ids;
            std::vector<InputEdge> edges;
            for (ExternalVertexId i = 0; i < 12; ++i)
                ids.push_back(i);
            for (EdgeId i = 0; i < 36; ++i)
                edges.push_back({i, static_cast<ExternalVertexId>(random() % 12),
                                 static_cast<ExternalVertexId>(random() % 12),
                                 static_cast<double>(random() % 4)});
            const Graph original(ids, edges);
            const auto reduced = reduce_degree(original);
            for (VertexIndex s = 0; s < 3; ++s) {
                const auto source = reduced.representative[s];
                const auto &g = reduced.graph;
                const auto exact = independent::truth(g, source);
                BMSSPOptions options;
                options.validate_frontier_operations = true;
                options.observer = [&](const BoundedTrace &e) {
                    independent::bounded_contract(e, exact);
                    if (e.level == 0 && !e.frontier.empty()) {
                        same(task9(g, e.before, 2, e.input_bound, e.frontier[0]), e.result, e.after,
                             e.input_bound);
                        ++leaves;
                    }
                    deep = std::max(deep, e.depth);
                };
                BMSSPWorkspace w(g, g.external_id(source), 2, 2, options);
                const auto r = w.run(4, {}, {source});
                CHECK(!r.bound.finite());
                for (VertexIndex v = 0; v < g.vertex_count(); ++v)
                    CHECK(independent::compare(independent::view(w.labels()[v]), exact[v]) == 0);
            }
        }
        CHECK(leaves > 100);
        CHECK(deep >= 3);
        std::cout << "task9_leaf_comparisons=" << leaves << " max_observed_depth=" << deep << "\n";
    });
    test::run("deep_repeated_concurrent_independent_workspaces", [] {
        const auto g = chain(2500);
        std::array<std::future<void>, 4> jobs;
        for (auto &job : jobs)
            job = std::async(std::launch::async, [&] {
                BMSSPWorkspace w(g, 0, 32, 2);
                for (std::size_t repeat = 0; repeat < 4; ++repeat) {
                    w.reset(0);
                    const auto r = w.run(6, {}, {0});
                    CHECK(r.completed.size() == 2500);
                    CHECK(!r.bound.finite());
                    CHECK(w.labels().back().node()->hops == 2499);
                }
            });
        for (auto &job : jobs)
            job.get();
    });
    return test::finish();
}
