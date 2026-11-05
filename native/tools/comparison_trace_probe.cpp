// SPDX-License-Identifier: Apache-2.0
// Matched-header/library process oracle; --full emits complete comparison evidence.
#include "bmssp/bmssp_2025.hpp"
#include "bmssp_oracle.hpp"
#include <bit>
#include <random>
using namespace bmssp;
namespace {
bool full = false;
std::size_t cases = 0, traces = 0, compared_labels = 0;
void label(const SymbolicLabel &value) {
    if (!full)
        return;
    std::cout << '[' << std::bit_cast<std::uint64_t>(value.distance()) << ',';
    if (value.finite())
        std::cout << value.node()->hops;
    else
        std::cout << "null";
    std::cout << ",[";
    bool first = true;
    for (auto *node = value.node(); node; node = node->parent) {
        if (!first)
            std::cout << ',';
        first = false;
        std::cout << '[' << node->vertex << ',';
        if (node->edge)
            std::cout << *node->edge;
        else
            std::cout << "null";
        std::cout << ']';
    }
    std::cout << "]]";
}
void keys(const std::vector<VertexIndex> &values) {
    if (!full)
        return;
    std::cout << '[';
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i)
            std::cout << ',';
        std::cout << values[i];
    }
    std::cout << ']';
}
void labels(const std::vector<SymbolicLabel> &values) {
    if (!full)
        return;
    std::cout << '[';
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i)
            std::cout << ',';
        label(values[i]);
    }
    std::cout << ']';
}
void trace(const BoundedTrace &e, const std::vector<independent::Label> &truth) {
    independent::bounded_contract(e, truth);
    ++traces;
    compared_labels += e.before.size() + e.after.size();
    if (!full)
        return;
    std::cout << "[" << e.level << ',' << e.depth << ',';
    label(e.input_bound);
    std::cout << ',';
    keys(e.frontier);
    std::cout << ',';
    labels(e.before);
    std::cout << ',';
    labels(e.after);
    std::cout << ',';
    label(e.result.bound);
    std::cout << ',';
    keys(e.result.completed);
    std::cout << "],";
}
void execute(const Graph &g, ExternalVertexId source, std::size_t method, bool profiled,
             bool finite_bound) {
    const auto s = g.vertex_index(source);
    const auto truth = independent::truth(g, s);
    BMSSPOptions options;
    options.validate_frontier_operations = true;
    options.observer = [&](const BoundedTrace &e) { trace(e, truth); };
    BMSSPWorkspace w(g, source, 2, 2, options);
    const auto before = w.labels();
    const auto bound = finite_bound ? SymbolicLabel::root(s, 1) : SymbolicLabel{};
    QueryProfile profile;
    if (full)
        std::cout << "[" << cases << ',' << method << ',' << profiled << ',' << finite_bound
                  << ",[";
    {
        ProfileSession session(profiled ? &profile : nullptr);
        if (method < 3) {
            const auto level = method == 0 ? 0U : method == 1 ? 1U : 4U;
            const auto result = w.run(level, bound, {s});
            if (full) {
                std::cout << "null],";
                label(result.bound);
                std::cout << ',';
                keys(result.completed);
            }
        } else if (method == 3) {
            const auto result = w.base_case(bound, {s});
            independent::bounded_contract({0, 0, bound, {s}, before, w.labels(), result}, truth);
            if (full) {
                std::cout << "null],";
                label(result.bound);
                std::cout << ',';
                keys(result.completed);
            }
        } else {
            const auto result = w.find_pivots(bound, {s});
            if (full) {
                std::cout << "null]," << result.early << ',';
                keys(result.pivots);
                std::cout << ',';
                keys(result.visited);
            }
        }
    }
    CHECK(active_profile == nullptr);
    compared_labels += w.labels().size();
    const auto &d = w.diagnostics();
    CHECK(d.label_nodes_materialized == d.label_updates + 1);
    if (full) {
        std::cout << ',';
        labels(w.labels());
        std::cout << ",[";
    }
    const std::vector<std::size_t> work{d.recursive_calls,
                                        d.base_calls,
                                        d.max_recursion_depth,
                                        d.pivot_calls,
                                        d.pivot_edge_scans,
                                        d.pivots_selected,
                                        d.pivot_early_returns,
                                        d.relaxed_edges,
                                        d.equality_relaxations,
                                        d.label_updates,
                                        d.completed_vertex_events,
                                        d.completed_vertices,
                                        d.original_reachable_vertices,
                                        d.label_nodes_created,
                                        d.label_nodes_materialized,
                                        d.transformed_vertices,
                                        d.transformed_edges,
                                        d.k,
                                        d.t,
                                        d.root_level,
                                        d.frontier.initializations,
                                        d.frontier.discards,
                                        d.frontier.inserts,
                                        d.frontier.pulls,
                                        d.frontier.batches,
                                        d.frontier.splits,
                                        d.frontier.selection_work,
                                        d.frontier.pulled_keys,
                                        d.frontier.peak_keys};
    if (full) {
        for (std::size_t i = 0; i < work.size(); ++i) {
            if (i)
                std::cout << ',';
            std::cout << work[i];
        }
        std::cout << "],[";
    }
    for (std::size_t i = 0; i < QueryProfile::size; ++i) {
        CHECK(std::isfinite(profile.inclusive[i]));
        CHECK(std::isfinite(profile.exclusive[i]));
        CHECK(profile.inclusive[i] >= 0);
        CHECK(profile.exclusive[i] >= 0);
        if (!profiled)
            CHECK(profile.calls[i] == 0);
        if (full) {
            if (i)
                std::cout << ',';
            std::cout << profile.calls[i];
        }
    }
    if (full)
        std::cout << "]],\n";
    ++cases;
}
Graph chain(std::size_t n) {
    std::vector<ExternalVertexId> ids;
    std::vector<InputEdge> edges;
    for (std::size_t i = 0; i < n; ++i) {
        ids.push_back(static_cast<ExternalVertexId>(i));
        if (i)
            edges.push_back(
                {i, static_cast<ExternalVertexId>(i - 1), static_cast<ExternalVertexId>(i), 0});
    }
    return {ids, edges};
}
} // namespace
int main(int argc, char **argv) {
    try {
        full = argc > 1 && std::string(argv[1]) == "--full";
        if (full)
            std::cout << "[\n";
        for (bool enabled : {false, true}) {
            for (auto method : {0U, 1U, 2U, 3U, 4U}) {
                execute(chain(70), 0, method, enabled, false);
                execute(chain(70), 0, method, enabled, true);
            }
            std::mt19937 random(142027);
            for (std::size_t round = 0; round < 20; ++round) {
                std::vector<ExternalVertexId> ids;
                for (ExternalVertexId i = 0; i < 8; ++i)
                    ids.push_back(i + 5000000000LL);
                std::vector<InputEdge> edges;
                for (EdgeId e = 0; e < 24; ++e)
                    edges.push_back({e + (std::uint64_t{1} << 50), ids[random() % 8],
                                     ids[random() % 8], static_cast<double>(random() % 5) / 4});
                const auto reduced = reduce_degree(Graph(ids, edges));
                for (VertexIndex source = 0; source < 2; ++source)
                    for (auto method : {2U, 3U, 4U})
                        execute(reduced.graph,
                                reduced.graph.external_id(reduced.representative[source]), method,
                                enabled, false);
            }
        }
        CHECK(cases == 260);
        CHECK(traces > 1000);
        if (full)
            std::cout << "null]\n";
        else
            std::cout << "{\"cases\":" << cases << ",\"bounded_traces\":" << traces
                      << ",\"label_values\":" << compared_labels << ",\"status\":\"PASS\"}\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
