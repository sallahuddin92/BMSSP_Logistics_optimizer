// SPDX-License-Identifier: Apache-2.0
#include "bmssp/bounded_frontier.hpp"
#include "test_support.hpp"
#include <map>
#include <random>
using namespace bmssp;
int main() {
    test::run("empty_and_bound_checks", [] {
        FrontierCounters c;
        BoundedFrontier d(2, SymbolicLabel::root(0, 5), c, true);
        CHECK(d.pull().entries.empty());
        test::throws<std::invalid_argument>([&] { d.insert(1, SymbolicLabel::root(1, 6)); });
    });
    test::run("block_splits_duplicates_and_prepend", [] {
        FrontierCounters c;
        BoundedFrontier d(3, {}, c, true);
        std::map<VertexIndex, SymbolicLabel> reference;
        for (VertexIndex i = 0; i < 30; ++i) {
            const auto v = SymbolicLabel::root(i, 100 + static_cast<double>(i % 7));
            d.insert(i, v);
            reference[i] = v;
        }
        d.insert(5, SymbolicLabel::root(5, 200));
        CHECK(d.size() == 30);
        std::vector<FrontierEntry> batch;
        for (VertexIndex i = 0; i < 40; ++i) {
            const auto v = SymbolicLabel::root(i, static_cast<double>(i % 4));
            batch.push_back({i, v});
            reference[i] = v;
        }
        batch.push_back({0, SymbolicLabel::root(0, 0)});
        d.batch_prepend(batch);
        while (!reference.empty()) {
            auto pulled = d.pull();
            CHECK(pulled.entries.size() == std::min(std::size_t{3}, reference.size()));
            std::vector<std::pair<VertexIndex, SymbolicLabel>> sorted(reference.begin(),
                                                                      reference.end());
            std::sort(sorted.begin(), sorted.end(),
                      [](const auto &a, const auto &b) { return a.second < b.second; });
            for (const auto &e : pulled.entries) {
                CHECK(e.value == reference.at(e.key));
                CHECK(e.value < pulled.bound);
                CHECK(std::find_if(sorted.begin(),
                                   sorted.begin() +
                                       static_cast<std::ptrdiff_t>(pulled.entries.size()),
                                   [&](const auto &x) { return x.first == e.key; }) !=
                      sorted.begin() + static_cast<std::ptrdiff_t>(pulled.entries.size()));
                reference.erase(e.key);
            }
            if (reference.empty())
                CHECK(!pulled.bound.finite());
            else {
                auto minimum = reference.begin()->second;
                for (const auto &[key, value] : reference) {
                    (void)key;
                    if (value < minimum)
                        minimum = value;
                }
                CHECK(pulled.bound == minimum);
            }
        }
        CHECK(c.splits > 0);
        CHECK(c.batches == 1);
        CHECK(c.selection_work > 0);
        d.validate();
    });
    test::run("randomized_ordered_model", [] {
        for (const std::size_t m : {1U, 2U, 5U, 16U}) {
            FrontierCounters c;
            BoundedFrontier d(m, {}, c, true);
            std::map<VertexIndex, SymbolicLabel> model;
            std::mt19937_64 rng(17033 + m);
            for (std::size_t step = 0; step < 1200; ++step) {
                if (step == 400) {
                    d.initialize(m, {});
                    model.clear();
                }
                if (step % 11 == 0) {
                    const auto key = static_cast<VertexIndex>(rng() % 100);
                    d.discard(key);
                    model.erase(key);
                } else if (step % 7 == 0) {
                    std::vector<FrontierEntry> batch;
                    for (std::size_t j = 0; j < 7; ++j) {
                        const auto key = static_cast<VertexIndex>(rng() % 100);
                        const auto value =
                            SymbolicLabel::root(key, 5000.0 - static_cast<double>(step) * 2 +
                                                         static_cast<double>(j) / 8);
                        batch.push_back({key, value});
                        if (!model.contains(key) || value < model[key])
                            model[key] = value;
                    }
                    d.batch_prepend(std::move(batch));
                } else if (rng() % 4 != 0 || model.empty()) {
                    const auto key = static_cast<VertexIndex>(rng() % 100);
                    const auto value =
                        SymbolicLabel::root(key, 10000.0 + static_cast<double>(rng() % 1000));
                    d.insert(key, value);
                    if (!model.contains(key) || value < model[key])
                        model[key] = value;
                } else {
                    std::vector<std::pair<VertexIndex, SymbolicLabel>> sorted(model.begin(),
                                                                              model.end());
                    std::sort(sorted.begin(), sorted.end(),
                              [](const auto &a, const auto &b) { return a.second < b.second; });
                    const auto pulled = d.pull();
                    const auto count = std::min(m, model.size());
                    CHECK(pulled.entries.size() == count);
                    for (const auto &e : pulled.entries) {
                        CHECK(e.value == model.at(e.key));
                        CHECK(e.value < pulled.bound);
                        bool expected = false;
                        for (std::size_t i = 0; i < count; ++i)
                            if (sorted[i].first == e.key)
                                expected = true;
                        CHECK(expected);
                        model.erase(e.key);
                    }
                }
                CHECK(model.size() == d.size());
                d.validate();
            }
        }
    });
    test::run("invalid_prepend_precondition", [] {
        FrontierCounters c;
        BoundedFrontier d(2, {}, c, true);
        d.insert(0, SymbolicLabel::root(0, 1));
        test::throws<std::invalid_argument>(
            [&] { d.batch_prepend({{1, SymbolicLabel::root(1, 2)}}); });
    });
    test::run("terminal_fence_recreation", [] {
        FrontierCounters c;
        BoundedFrontier d(1, {}, c, true);
        d.insert(0, SymbolicLabel::root(0, 1));
        d.insert(1, SymbolicLabel::root(1, 3));
        d.discard(1);
        d.insert(2, SymbolicLabel::root(2, 4));
        CHECK(d.pull().entries[0].key == 0);
        CHECK(d.pull().entries[0].key == 2);
        d.initialize(3, {});
        CHECK(d.empty());
    });
    return test::finish();
}
