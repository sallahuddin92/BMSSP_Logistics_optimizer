// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/result.hpp"
#include "bmssp/symbolic_label.hpp"
namespace bmssp {
struct DegreeReduction {
    Graph original;
    Graph graph;
    std::vector<VertexIndex> representative;
    std::vector<VertexIndex> original_vertex;
    std::vector<std::optional<EdgeId>> original_edge;
    void validate() const;
};
[[nodiscard]] DegreeReduction reduce_degree(const Graph &graph);
// Projects a concrete transformed path, removing synthetic edges only.
[[nodiscard]] Path project_path(const DegreeReduction &reduction, const SymbolicLabel &label);
} // namespace bmssp
