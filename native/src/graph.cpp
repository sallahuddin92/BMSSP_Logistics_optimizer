// SPDX-License-Identifier: Apache-2.0
#include "bmssp/graph.hpp"
#include <algorithm>
#include <utility>

namespace bmssp {
struct Graph::Storage {
    std::vector<ExternalVertexId> vertices;
    std::vector<Edge> by_id;
    std::vector<Edge> adjacency;
    std::vector<std::size_t> offsets;
};
Graph::Graph(std::vector<ExternalVertexId> vertices, std::vector<InputEdge> edges) {
    check_allocation_count<ExternalVertexId>(vertices.size());
    check_allocation_count<Edge>(edges.size());
    check_allocation_count<std::size_t>(checked_size_add(vertices.size(), 1));
    std::sort(vertices.begin(), vertices.end());
    if (std::adjacent_find(vertices.begin(), vertices.end()) != vertices.end()) {
        throw std::invalid_argument("duplicate external vertex ID");
    }
    std::sort(edges.begin(), edges.end(), [](const auto &a, const auto &b) { return a.id < b.id; });
    auto data = std::make_shared<Storage>();
    data->vertices = std::move(vertices);
    data->by_id.reserve(edges.size());
    data->offsets.assign(checked_size_add(data->vertices.size(), 1), 0);
    const auto index = [&data](ExternalVertexId id) {
        const auto it = std::lower_bound(data->vertices.begin(), data->vertices.end(), id);
        if (it == data->vertices.end() || *it != id)
            throw std::invalid_argument("edge references unknown vertex");
        return static_cast<VertexIndex>(it - data->vertices.begin());
    };
    for (std::size_t i = 0; i < edges.size(); ++i) {
        const auto &e = edges[i];
        if (i != 0 && edges[i - 1].id == e.id)
            throw std::invalid_argument("duplicate original edge ID");
        if (!std::isfinite(e.weight) || e.weight < 0)
            throw std::invalid_argument("edge weight must be finite and nonnegative");
        const auto u = index(e.from);
        const auto v = index(e.to);
        data->by_id.push_back({e.id, u, v, e.weight == 0 ? 0.0 : e.weight});
        data->offsets[u + 1] = checked_size_add(data->offsets[u + 1], 1);
    }
    for (std::size_t i = 1; i < data->offsets.size(); ++i) {
        data->offsets[i] = checked_size_add(data->offsets[i], data->offsets[i - 1]);
    }
    data->adjacency = data->by_id;
    std::sort(data->adjacency.begin(), data->adjacency.end(), [](const Edge &a, const Edge &b) {
        return a.from < b.from || (a.from == b.from && a.id < b.id);
    });
    storage_ = std::move(data);
}
std::size_t Graph::vertex_count() const noexcept {
    return storage_->vertices.size();
}
std::size_t Graph::edge_count() const noexcept {
    return storage_->by_id.size();
}
VertexIndex Graph::vertex_index(ExternalVertexId id) const {
    const auto &ids = storage_->vertices;
    const auto it = std::lower_bound(ids.begin(), ids.end(), id);
    if (it == ids.end() || *it != id)
        throw std::out_of_range("unknown external vertex ID");
    return static_cast<VertexIndex>(it - ids.begin());
}
ExternalVertexId Graph::external_id(VertexIndex vertex) const {
    return storage_->vertices.at(vertex);
}
std::span<const Edge> Graph::outgoing(VertexIndex vertex) const {
    if (vertex >= vertex_count())
        throw std::out_of_range("invalid dense vertex index");
    return std::span<const Edge>(storage_->adjacency)
        .subspan(storage_->offsets[vertex],
                 storage_->offsets[vertex + 1] - storage_->offsets[vertex]);
}
const Edge &Graph::edge(EdgeId id) const {
    const auto &edges = storage_->by_id;
    const auto it = std::lower_bound(edges.begin(), edges.end(), id,
                                     [](const Edge &e, EdgeId key) { return e.id < key; });
    if (it == edges.end() || it->id != id)
        throw std::out_of_range("unknown original edge ID");
    return *it;
}
bool Graph::same_storage(const Graph &other) const noexcept {
    return storage_ == other.storage_;
}
} // namespace bmssp
