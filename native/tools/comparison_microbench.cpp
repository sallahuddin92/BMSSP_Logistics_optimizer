// SPDX-License-Identifier: Apache-2.0
// Diagnostic only: compile against matching variant headers/library; never query latency.
#include "bmssp/profile.hpp"
#include "bmssp/symbolic_label.hpp"
#include <chrono>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>
using namespace bmssp;
static int plain(const LabelNode *a, const LabelNode *b) {
    if (a == b)
        return 0;
    if (!a)
        return 1;
    if (!b)
        return -1;
    const auto scalar = [](auto x, auto y) { return x < y ? -1 : (y < x ? 1 : 0); };
    if (auto c = scalar(a->distance, b->distance); c)
        return c;
    if (auto c = scalar(a->hops, b->hops); c)
        return c;
    auto x = a, y = b;
    while (x && y && x != y) {
        if (auto c = scalar(x->vertex, y->vertex); c)
            return c;
        x = x->parent;
        y = y->parent;
    }
    x = a;
    y = b;
    while (x && y && x != y) {
        if (auto c = scalar(x->edge, y->edge); c)
            return c;
        x = x->parent;
        y = y->parent;
    }
    return 0;
}
int main(int argc, char **argv) {
    const bool stripped = argc > 1 && std::string(argv[1]) == "no_scope";
    std::vector<SymbolicLabel> a, b;
    std::vector<std::string> names;
    auto root = SymbolicLabel::root(0);
    auto add = [&](std::string n, SymbolicLabel x, SymbolicLabel y) {
        names.push_back(n);
        a.push_back(x);
        b.push_back(y);
    };
    add("same", root, root);
    add("infinity", root, {});
    add("distance", SymbolicLabel::root(0, 1), SymbolicLabel::root(0, 2));
    add("hops", root.extend({1, 0, 1, 0}), root);
    add("equivalent", root.extend({1, 0, 1, 0}), root.extend({1, 0, 1, 0}));
    auto low = SymbolicLabel::root(0).extend({1, 0, 1, 0}),
         high = SymbolicLabel::root(0).extend({2, 0, 1, 0});
    for (VertexIndex v = 2; v < 32; ++v) {
        low = low.extend({v, v - 1, v, 0});
        high = high.extend({v, v - 1, v, 0});
    }
    add("parallel_deep", low, high);
    std::cout << "{\"rows\":[";
    bool first = true;
    for (int trial = 0; trial < 3; ++trial)
        for (std::size_t cat = 0; cat < names.size(); ++cat)
            for (int mode = 0; mode < 3; ++mode) {
                const bool enabled = mode == 1, reference = mode == 2;
                const std::size_t n = enabled ? 100000 : 1000000;
                QueryProfile profile;
                std::int64_t checksum = 0;
                auto start = std::chrono::steady_clock::now();
                {
                    ProfileSession session(enabled ? &profile : nullptr);
                    for (std::size_t i = 0; i < n; ++i) {
                        const bool flip = (i & 1) != 0;
                        const auto &x = flip ? b[cat] : a[cat];
                        const auto &y = flip ? a[cat] : b[cat];
                        const SymbolicLabel *volatile left = &x;
                        const SymbolicLabel *volatile right = &y;
                        const auto &lx = *left;
                        const auto &ry = *right;
                        const int c = reference ? plain(lx.node(), ry.node()) : compare(lx, ry);
                        checksum += c;
                    }
                }
                const double elapsed =
                    std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
                if (checksum != 0)
                    return 2;
                auto calls = profile.calls[static_cast<std::size_t>(ProfilePart::comparison)];
                if (calls != (enabled && !stripped ? n : 0))
                    return 3;
                if (!first)
                    std::cout << ',';
                first = false;
                std::cout << "{\"trial\":" << trial << ",\"category\":\"" << names[cat]
                          << "\",\"mode\":\""
                          << (enabled     ? "enabled"
                              : reference ? "inline_reference"
                                          : "disabled")
                          << "\",\"iterations\":" << n << ",\"seconds\":" << elapsed
                          << ",\"ns_per_compare\":" << elapsed * 1e9 / static_cast<double>(n)
                          << ",\"profile_calls\":" << calls << ",\"checksum\":" << checksum << '}';
            }
    std::cout << "]}\n";
}
