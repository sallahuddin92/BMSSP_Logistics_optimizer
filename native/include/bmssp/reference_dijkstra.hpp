// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/result.hpp"
namespace bmssp {
// Reference Dijkstra only. This API does not implement bounded recursive BMSSP.
[[nodiscard]] ShortestPathResult reference_dijkstra(const Graph &graph, ExternalVertexId source);
} // namespace bmssp
