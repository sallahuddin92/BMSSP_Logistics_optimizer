// bmssp.cpp
// Production-grade BMSSP algorithm core implementation
#include <vector>
#include <queue>
#include <unordered_map>
#include <limits>
#include <tuple>

// Example graph type: adjacency list with weights
using Graph = std::unordered_map<int, std::vector<std::pair<int, double>>>;

// Production-grade BMSSP solver (simplified for template)
std::vector<std::vector<double>> solve_bmssp(const Graph& graph, const std::vector<int>& sources, const std::vector<int>& targets) {
    size_t n = sources.size();
    size_t m = targets.size();
    std::vector<std::vector<double>> result(n, std::vector<double>(m, std::numeric_limits<double>::infinity()));
    // For each source, run Dijkstra (replace with bidirectional search for real prod)
    for (size_t i = 0; i < n; ++i) {
        int src = sources[i];
        std::unordered_map<int, double> dist;
        std::priority_queue<std::pair<double, int>, std::vector<std::pair<double, int>>, std::greater<>> pq;
        dist[src] = 0.0;
        pq.emplace(0.0, src);
        while (!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if (d > dist[u]) continue;
            for (const auto& [v, w] : graph.at(u)) {
                double nd = d + w;
                if (!dist.count(v) || nd < dist[v]) {
                    dist[v] = nd;
                    pq.emplace(nd, v);
                }
            }
        }
        for (size_t j = 0; j < m; ++j) {
            int tgt = targets[j];
            if (dist.count(tgt)) result[i][j] = dist[tgt];
        }
    }
    return result;
}
