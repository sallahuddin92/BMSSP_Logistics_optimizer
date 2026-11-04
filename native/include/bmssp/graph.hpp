// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/engine_contract.hpp"
#include <cstdint>
#include <memory>
#include <span>
#include <vector>

namespace bmssp {
using ExternalVertexId = std::int64_t;
using VertexIndex = std::size_t;
using EdgeId = std::uint64_t;
struct InputEdge {
    EdgeId id;
    ExternalVertexId from;
    ExternalVertexId to;
    Weight weight;
};
struct Edge {
    EdgeId id;
    VertexIndex from;
    VertexIndex to;
    Weight weight;
};

// Shared immutable storage: copies are O(1); concurrent read-only queries are safe.
class Graph {
  public:
    Graph(std::vector<ExternalVertexId> vertices, std::vector<InputEdge> edges);
    [[nodiscard]] std::size_t vertex_count() const noexcept;
    [[nodiscard]] std::size_t edge_count() const noexcept;
    [[nodiscard]] VertexIndex vertex_index(ExternalVertexId id) const;
    [[nodiscard]] ExternalVertexId external_id(VertexIndex vertex) const;
    [[nodiscard]] std::span<const Edge> outgoing(VertexIndex vertex) const;
    [[nodiscard]] const Edge &edge(EdgeId id) const;
    [[nodiscard]] bool same_storage(const Graph &other) const noexcept;

  private:
    struct Storage;
    std::shared_ptr<const Storage> storage_;
};
} // namespace bmssp
