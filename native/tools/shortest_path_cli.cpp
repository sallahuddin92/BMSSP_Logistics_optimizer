// SPDX-License-Identifier: Apache-2.0
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include <charconv>
#include <iomanip>
#include <iostream>
#include <string>
#include <string_view>

namespace {
template <class T> T integer(std::string_view text) {
    T value{};
    const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value);
    if (error != std::errc{} || end != text.data() + text.size())
        throw std::invalid_argument("invalid integer token");
    return value;
}
std::string token() {
    std::string value;
    if (!(std::cin >> value))
        throw std::invalid_argument("truncated graph input");
    return value;
}
bmssp::Graph read_graph() {
    const auto n = integer<std::size_t>(token()), m = integer<std::size_t>(token());
    bmssp::check_allocation_count<bmssp::ExternalVertexId>(n);
    bmssp::check_allocation_count<bmssp::InputEdge>(m);
    std::vector<bmssp::ExternalVertexId> vertices;
    vertices.reserve(n);
    std::vector<bmssp::InputEdge> edges;
    edges.reserve(m);
    for (std::size_t i = 0; i < n; ++i)
        vertices.push_back(integer<bmssp::ExternalVertexId>(token()));
    for (std::size_t i = 0; i < m; ++i) {
        const auto id = integer<bmssp::EdgeId>(token());
        const auto u = integer<bmssp::ExternalVertexId>(token()),
                   v = integer<bmssp::ExternalVertexId>(token());
        const auto text = token();
        double weight = 0;
        const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), weight,
                                                  std::chars_format::general);
        if (error != std::errc{} || end != text.data() + text.size())
            throw std::invalid_argument("invalid or out-of-range weight token");
        edges.push_back({id, u, v, weight});
    }
    std::string extra;
    if (std::cin >> extra)
        throw std::invalid_argument("unexpected trailing input");
    if (std::cin.bad())
        throw std::runtime_error("input read failure");
    return {std::move(vertices), std::move(edges)};
}
void print(const bmssp::Graph &graph, bmssp::ExternalVertexId source,
           bmssp::ExternalVertexId target, bool genuine = false) {
    std::optional<bmssp::BMSSPDiagnostics> diagnostics;
    const auto result = [&] {
        if (genuine) {
            auto actual = bmssp::bmssp_2025(graph, source);
            diagnostics = actual.diagnostics;
            return std::move(actual.shortest_paths);
        }
        return bmssp::reference_dijkstra(graph, source);
    }();
    const auto path = bmssp::reconstruct_path(graph, result, target);
    std::cout << std::setprecision(17)
              << "algorithm=" << (genuine ? "bmssp_2025" : "reference_dijkstra")
              << " reachable=" << (path.status == bmssp::PathStatus::reachable ? "true" : "false")
              << " distance=" << path.distance << "\nvertices";
    for (const auto id : path.vertices)
        std::cout << ' ' << id;
    std::cout << "\nedges";
    for (const auto id : path.edges)
        std::cout << ' ' << id;
    std::cout << '\n';
    if (diagnostics)
        std::cout << "recursive_calls=" << diagnostics->recursive_calls
                  << " max_depth=" << diagnostics->max_recursion_depth
                  << " pivots=" << diagnostics->pivots_selected
                  << " pulls=" << diagnostics->frontier.pulls
                  << " equality_relaxations=" << diagnostics->equality_relaxations << '\n';
}
} // namespace
int main(int argc, char **argv) {
    try {
        if (argc == 2 && (std::string_view(argv[1]) == "--demo" ||
                          std::string_view(argv[1]) == "--bmssp-demo")) {
            const bmssp::Graph graph(
                {0, 1, 2, 3, 4},
                {{10, 0, 1, 9}, {11, 0, 2, 2}, {12, 2, 1, 1}, {13, 1, 3, 4}, {14, 2, 3, 20}});
            print(graph, 0, 3, std::string_view(argv[1]) == "--bmssp-demo");
        } else if (argc == 5 && std::string_view(argv[1]) == "--algorithm") {
            const auto algorithm = std::string_view(argv[2]);
            if (algorithm != "bmssp" && algorithm != "dijkstra")
                throw std::invalid_argument("algorithm must be bmssp or dijkstra");
            const auto graph = read_graph();
            print(graph, integer<bmssp::ExternalVertexId>(argv[3]),
                  integer<bmssp::ExternalVertexId>(argv[4]), algorithm == "bmssp");
        } else if (argc == 3) {
            const auto source = integer<bmssp::ExternalVertexId>(argv[1]),
                       target = integer<bmssp::ExternalVertexId>(argv[2]);
            const auto graph = read_graph();
            print(graph, source, target);
        } else {
            std::cerr << "usage: shortest_path_cli --demo | --bmssp-demo | "
                         "[--algorithm bmssp|dijkstra] SOURCE TARGET < graph.txt\n";
            return 2;
        }
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
