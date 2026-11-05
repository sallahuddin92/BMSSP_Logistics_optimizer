// SPDX-License-Identifier: Apache-2.0
#include "bmssp/bmssp_2025.hpp"
#include "bmssp_oracle.hpp"
#include "compare_task13_symbolic.hpp"
#include "profile_test_observer.hpp"
#include "test_support.hpp"
#include <cfenv>
#include <cmath>
#include <future>
#include <random>
using namespace bmssp;
namespace {
constexpr auto cmp = static_cast<std::size_t>(ProfilePart::comparison);
constexpr auto rec = static_cast<std::size_t>(ProfilePart::recursion);
constexpr auto piv = static_cast<std::size_t>(ProfilePart::pivots);
void valid(const QueryProfile &p) {
    for (std::size_t i = 0; i < QueryProfile::size; ++i) {
        CHECK(std::isfinite(p.inclusive[i]));
        CHECK(std::isfinite(p.exclusive[i]));
        CHECK(p.inclusive[i] >= 0);
        CHECK(p.exclusive[i] >= 0);
        CHECK(p.exclusive[i] <= p.inclusive[i] + 1e-12);
    }
}
void check_equal(double x, double y) {
    CHECK(std::abs(x - y) <= 1e-10 + 1e-9 * std::max(std::abs(x), std::abs(y)));
}
} // namespace
int main() {
    test::run("frozen_Task13_all_signs_operators_ancestry_and_numeric_contract", [] {
        auto root = SymbolicLabel::root(0);
        auto reference = task13_label::SymbolicLabel::root(0);
        std::vector<SymbolicLabel> a{{}, root, root};
        std::vector<task13_label::SymbolicLabel> b{{}, reference, reference};
        std::mt19937 random(142026);
        for (std::size_t i = 0; i < 300; ++i) {
            const auto parent = 1 + random() % (a.size() - 1);
            Edge e{static_cast<EdgeId>(random()) + (std::uint64_t{1} << 50),
                   a[parent].node()->vertex,
                   static_cast<VertexIndex>(random()) +
                       static_cast<VertexIndex>(std::uint64_t{1} << 40),
                   static_cast<double>(random() % 4) / 4};
            a.push_back(a[parent].extend(e));
            b.push_back(b[parent].extend(e));
        }
        a.push_back(SymbolicLabel::root(0, std::numeric_limits<double>::max()));
        b.push_back(task13_label::SymbolicLabel::root(0, std::numeric_limits<double>::max()));
        for (std::size_t i = 0; i < a.size(); ++i)
            for (std::size_t j = 0; j < a.size(); ++j) {
                int sign = compare(a[i], a[j]);
                CHECK(sign == compare(b[i], b[j]));
                CHECK(sign ==
                      independent::compare(independent::view(a[i]), independent::view(a[j])));
                CHECK((a[i] < a[j]) == (sign < 0));
                CHECK((a[i] <= a[j]) == (sign <= 0));
                CHECK((a[i] == a[j]) == (sign == 0));
            }
        auto x = SymbolicLabel::root(0), y = SymbolicLabel::root(0);
        auto xr = task13_label::SymbolicLabel::root(0), yr = task13_label::SymbolicLabel::root(0);
        for (VertexIndex v = 1; v <= 12000; ++v) {
            Edge e{std::numeric_limits<EdgeId>::max() - v, v - 1, v, 0};
            x = x.extend(e);
            y = y.extend(e);
            xr = xr.extend(e);
            yr = yr.extend(e);
        }
        CHECK(x.node() != y.node());
        CHECK(compare(x, y) == compare(xr, yr));
        CHECK(x == y);
        auto low = SymbolicLabel::root(0).extend({1, 0, 1, 0}),
             high = SymbolicLabel::root(0).extend({2, 0, 1, 0});
        auto lr = task13_label::SymbolicLabel::root(0).extend({1, 0, 1, 0}),
             hr = task13_label::SymbolicLabel::root(0).extend({2, 0, 1, 0});
        for (VertexIndex v = 2; v < 3000; ++v) {
            Edge e{v, v - 1, v, 0};
            low = low.extend(e);
            high = high.extend(e);
            lr = lr.extend(e);
            hr = hr.extend(e);
        }
        CHECK(compare(low, high) == compare(lr, hr));
        CHECK(low < high);
        CHECK(high.parent().node()->hops == 2998);
        for (double invalid : {-1.0, unreachable, std::numeric_limits<double>::quiet_NaN()})
            test::throws<std::invalid_argument>([&] { (void)SymbolicLabel::root(0, invalid); });
        test::throws<std::overflow_error>([] {
            (void)SymbolicLabel::root(0, std::numeric_limits<double>::max())
                .extend({0, 0, 1, std::numeric_limits<double>::max()});
        });
        const int old = std::fegetround();
        CHECK(std::fesetround(FE_DOWNWARD) == 0);
        bool rejected = false;
        try {
            validate_numeric_environment();
        } catch (const std::invalid_argument &) {
            rejected = true;
        }
        CHECK(std::fesetround(old) == 0);
        CHECK(rejected);
        const auto g = test::fixture();
        BMSSPWorkspace w(g, 0, 2, 2);
        (void)w.run(3, {}, {0});
        auto saved = w.labels();
        w.reset(0);
        CHECK(saved[0].finite());
        CHECK(saved[0].node()->vertex == 0);
    });
    test::run("every_comparison_terminal_profiled_and_disabled", [] {
        const auto root = SymbolicLabel::root(0);
        const auto a = root.extend({1, 0, 1, 0});
        const auto b = SymbolicLabel::root(0).extend({1, 0, 1, 0});
        const auto high = root.extend({2, 0, 1, 0});
        const auto other = root.extend({3, 0, 2, 0});
        std::vector<SymbolicLabel> labels{{}, root, a, b, high, other, SymbolicLabel::root(0, 2)};
        QueryProfile p;
        std::size_t observed = 0;
        {
            profile_test::Count count(observed);
            ProfileSession session(&p);
            for (const auto &x : labels)
                for (const auto &y : labels) {
                    const int c = compare(x, y);
                    CHECK(c >= -1 && c <= 1);
                }
        }
        CHECK(p.calls[cmp] == labels.size() * labels.size());
        CHECK(p.calls[cmp] == observed);
        valid(p);
        const auto before = p.calls;
        {
            ProfileSession disabled(nullptr);
            for (const auto &x : labels)
                for (const auto &y : labels)
                    (void)compare(x, y);
        }
        CHECK(p.calls == before);
        CHECK(active_profile == nullptr);
    });
    test::run("nested_scopes_exclusive_attribution_early_return", [] {
        const auto root = SymbolicLabel::root(0);
        QueryProfile p;
        {
            ProfileSession session(&p);
            ProfileScope outer(ProfilePart::recursion);
            {
                ProfileScope child(ProfilePart::pivots);
                CHECK(compare(root, root) == 0);
                CHECK(compare(root, {}) < 0);
            }
        }
        CHECK(p.calls[rec] == 1);
        CHECK(p.calls[piv] == 1);
        CHECK(p.calls[cmp] == 2);
        valid(p);
        check_equal(p.inclusive[rec] - p.inclusive[piv], p.exclusive[rec]);
        check_equal(p.inclusive[piv] - p.inclusive[cmp], p.exclusive[piv]);
        check_equal(p.inclusive[cmp], p.exclusive[cmp]);
        check_equal(p.inclusive[rec], p.exclusive[rec] + p.exclusive[piv] + p.exclusive[cmp]);
    });
    test::run("nested_sessions_disabled_restoration_and_exceptions", [] {
        const auto root = SymbolicLabel::root(0);
        QueryProfile a, b;
        {
            ProfileSession first(&a);
            ProfileScope outer(ProfilePart::recursion);
            CHECK(active_profile == &a);
            (void)compare(root, root);
            try {
                ProfileSession second(&b);
                ProfileScope child(ProfilePart::pivots);
                (void)compare(root, {});
                {
                    ProfileSession off(nullptr);
                    (void)compare(root, root);
                    CHECK(active_profile == nullptr);
                }
                CHECK(active_profile == &b);
                throw std::runtime_error("intentional profiling unwind");
            } catch (const std::runtime_error &e) {
                CHECK(std::string(e.what()) == "intentional profiling unwind");
            }
            CHECK(active_profile == &a);
            (void)compare({}, root);
        }
        CHECK(active_profile == nullptr);
        CHECK(a.calls[cmp] == 2);
        CHECK(b.calls[cmp] == 1);
        CHECK(a.calls[rec] == 1);
        CHECK(b.calls[piv] == 1);
        valid(a);
        valid(b);
        check_equal(a.inclusive[rec] - b.inclusive[piv] - a.inclusive[cmp], a.exclusive[rec]);
        for (std::size_t i = 0; i < 50; ++i) {
            QueryProfile fresh;
            {
                ProfileSession repeat(&fresh);
                (void)compare(root, root);
            }
            CHECK(fresh.calls[cmp] == 1);
            CHECK(active_profile == nullptr);
        }
    });
    test::run("same_part_nesting_and_exception_parent_cleanup", [] {
        QueryProfile p;
        double inner = 0;
        const auto root = SymbolicLabel::root(0);
        {
            ProfileSession session(&p);
            ProfileScope outer(ProfilePart::comparison);
            {
                ProfileScope child(ProfilePart::comparison);
                (void)compare(root, root);
            }
            inner = p.inclusive[cmp];
        }
        CHECK(p.calls[cmp] == 3);
        valid(p);
        CHECK(p.exclusive[cmp] <= p.inclusive[cmp]);
        // Aggregate exclusive time equals the outermost interval, with nested intervals subtracted
        // once.
        check_equal(p.exclusive[cmp], p.inclusive[cmp] - inner);
        QueryProfile clean;
        {
            ProfileSession session(&clean);
            (void)compare(root, root);
        }
        CHECK(clean.calls[cmp] == 1);
        valid(clean);
    });
    test::run("solver_actual_counts_opt_in_and_parent_session_restoration", [] {
        const auto graph = test::fixture();
        BMSSP2025Engine engine(graph);
        QueryProfile outer;
        std::size_t off_calls = 0, on_calls = 0;
        std::optional<BMSSPResult> off, on;
        const auto root = SymbolicLabel::root(0);
        {
            ProfileSession session(&outer);
            (void)compare(root, root);
            {
                profile_test::Count count(off_calls);
                off = engine.solve(0);
            }
            CHECK(active_profile == &outer);
            CHECK(outer.calls[cmp] == 1);
            BMSSPOptions options;
            options.profile = true;
            {
                profile_test::Count count(on_calls);
                on = engine.solve(0, options);
            }
            CHECK(active_profile == &outer);
            CHECK(outer.calls[cmp] == 1);
            (void)compare(root, root);
        }
        CHECK(outer.calls[cmp] == 2);
        CHECK(off_calls == on_calls);
        CHECK(on_calls > 0);
        CHECK(on->diagnostics.profile.calls[cmp] == on_calls);
        valid(on->diagnostics.profile);
        for (auto n : off->diagnostics.profile.calls)
            CHECK(n == 0);
        CHECK(off->shortest_paths.distances == on->shortest_paths.distances);
        CHECK(off->shortest_paths.predecessor_edges == on->shortest_paths.predecessor_edges);
        CHECK(off->diagnostics.label_nodes_materialized ==
              on->diagnostics.label_nodes_materialized);
        CHECK(off->diagnostics.recursive_calls == on->diagnostics.recursive_calls);
        CHECK(active_profile == nullptr);
    });
    test::run("independent_threads_and_shared_arena_extensions", [] {
        const auto root = SymbolicLabel::root(0);
        std::array<std::future<QueryProfile>, 4> jobs;
        for (auto &job : jobs)
            job = std::async(std::launch::async, [root] {
                QueryProfile p;
                {
                    ProfileSession session(&p);
                    for (VertexIndex v = 1; v <= 200; ++v) {
                        auto a = root.extend({v, 0, v, 0});
                        CHECK(compare(a, root) > 0);
                        CHECK(compare(root, a) < 0);
                    }
                }
                CHECK(active_profile == nullptr);
                return p;
            });
        for (auto &job : jobs) {
            const auto p = job.get();
            CHECK(p.calls[cmp] == 400);
            CHECK(p.calls[static_cast<std::size_t>(ProfilePart::labels)] == 200);
            valid(p);
        }
        CHECK(active_profile == nullptr);
    });
    return test::finish();
}
