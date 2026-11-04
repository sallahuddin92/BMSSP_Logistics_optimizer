// SPDX-License-Identifier: Apache-2.0
#include "bmssp/bmssp_2025.hpp"
#include "bmssp/reference_dijkstra.hpp"
#include <chrono>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <tuple>
namespace py = pybind11;
using namespace bmssp;
namespace {
using Clock = std::chrono::steady_clock;
// Normalize Python integer scalars while the GIL is held; never truncate floats.
template <class T> T integer_id(py::handle value) {
    if (PyBool_Check(value.ptr()) || !PyIndex_Check(value.ptr()))
        throw py::type_error("Native vertex/edge IDs require integer scalars, excluding bool");
    auto indexed = py::reinterpret_steal<py::object>(PyNumber_Index(value.ptr()));
    if (!indexed)
        throw py::error_already_set();
    try {
        return indexed.cast<T>();
    } catch (const py::cast_error &) {
        throw py::type_error("Native ID is outside the required 64-bit integer range");
    }
}
std::vector<ExternalVertexId> vertex_ids(const py::iterable &values) {
    std::vector<ExternalVertexId> ids;
    for (const auto value : values)
        ids.push_back(integer_id<ExternalVertexId>(value));
    return ids;
}
struct Query {
    ShortestPathResult result;
    py::dict diagnostics;
    std::string algorithm;
};
struct PreparedBMSSP {
    BMSSP2025Engine engine;
    double preprocessing_seconds;
    explicit PreparedBMSSP(const Graph &graph) : engine(graph), preprocessing_seconds(0) {}
};
struct PreparedDijkstra {
    Graph graph;
};
py::dict diagnostics(const BMSSPDiagnostics &d) {
    py::dict out;
#define FIELD(name) out[#name] = d.name
    FIELD(recursive_calls);
    FIELD(base_calls);
    FIELD(max_recursion_depth);
    FIELD(pivot_calls);
    FIELD(pivot_edge_scans);
    FIELD(pivots_selected);
    FIELD(pivot_early_returns);
    FIELD(relaxed_edges);
    FIELD(equality_relaxations);
    FIELD(label_updates);
    FIELD(completed_vertex_events);
    FIELD(completed_vertices);
    FIELD(original_reachable_vertices);
    FIELD(label_nodes_created);
    FIELD(transformed_vertices);
    FIELD(transformed_edges);
    FIELD(k);
    FIELD(t);
    FIELD(root_level);
    FIELD(preprocessing_seconds);
    FIELD(query_seconds);
#undef FIELD
    py::dict frontier;
#define FIELD(name) frontier[#name] = d.frontier.name
    FIELD(initializations);
    FIELD(discards);
    FIELD(inserts);
    FIELD(pulls);
    FIELD(batches);
    FIELD(splits);
    FIELD(selection_work);
    FIELD(pulled_keys);
    FIELD(peak_keys);
#undef FIELD
    out["frontier"] = frontier;
    out["implementation"] = "BMSSP2025Engine::solve";
    return out;
}
} // namespace
PYBIND11_MODULE(bmssp_native, m) {
    m.doc() = "Independent C++20 BMSSP 2025 engine; no implicit fallback";
    m.attr("algorithm_version") = "arxiv:2504.17033v2";
    m.attr("compiler") = __VERSION__;
    m.def("_binding_roundtrip_ids", [](std::vector<ExternalVertexId> ids) { return ids; });
    py::class_<Graph>(m, "NativeGraph")
        .def(py::init([](const py::iterable &input_vertices, const py::iterable &input_edges) {
                 auto vertices = vertex_ids(input_vertices);
                 std::vector<InputEdge> edges;
                 for (const auto item : input_edges) {
                     const auto row = py::tuple(py::reinterpret_borrow<py::object>(item));
                     if (row.size() != 4)
                         throw py::value_error("Edges require (id, from, to, weight)");
                     const auto id = integer_id<EdgeId>(row[0]);
                     const auto from = integer_id<ExternalVertexId>(row[1]);
                     const auto to = integer_id<ExternalVertexId>(row[2]);
                     if (PyBool_Check(row[3].ptr()) || !PyNumber_Check(row[3].ptr()))
                         throw py::type_error(
                             "Native weights require numeric scalars, excluding bool");
                     const auto weight = py::float_(row[3]).cast<Weight>();
                     edges.push_back({id, from, to, weight});
                 }
                 py::gil_scoped_release release;
                 return Graph(std::move(vertices), std::move(edges));
             }),
             py::arg("vertices"), py::arg("edges"))
        .def_property_readonly("vertex_ids",
                               [](const Graph &g) {
                                   std::vector<ExternalVertexId> ids;
                                   for (VertexIndex i = 0; i < g.vertex_count(); ++i)
                                       ids.push_back(g.external_id(i));
                                   return ids;
                               })
        .def_property_readonly("metadata", [](const Graph &g) {
            py::dict out;
            out["vertex_count"] = g.vertex_count();
            out["edge_count"] = g.edge_count();
            out["directed"] = true;
            out["immutable"] = true;
            return out;
        });
    py::class_<Query>(m, "DistanceResult")
        .def_property_readonly("algorithm", [](const Query &q) { return q.algorithm; })
        .def_property_readonly(
            "source", [](const Query &q) { return q.result.graph.external_id(q.result.source); })
        .def_property_readonly("distances", [](const Query &q) { return q.result.distances; })
        .def_property_readonly("reachability",
                               [](const Query &q) {
                                   std::vector<bool> out;
                                   for (const auto d : q.result.distances)
                                       out.push_back(std::isfinite(d));
                                   return out;
                               })
        .def_property_readonly("diagnostics",
                               [](const Query &q) { return py::dict(q.diagnostics); })
        .def("belongs_to",
             [](const Query &q, const Graph &g) { return q.result.graph.same_storage(g); })
        .def("distance",
             [](const Query &q, py::handle target) {
                 return q.result.distances.at(
                     q.result.graph.vertex_index(integer_id<ExternalVertexId>(target)));
             })
        .def("distances_to",
             [](const Query &q, const py::iterable &input) {
                 const auto targets = vertex_ids(input);
                 py::gil_scoped_release release;
                 std::vector<Distance> out;
                 out.reserve(targets.size());
                 for (const auto t : targets)
                     out.push_back(q.result.distances.at(q.result.graph.vertex_index(t)));
                 return out;
             })
        .def("path", [](const Query &q, py::handle input) {
            const auto target = integer_id<ExternalVertexId>(input);
            const auto path = [&] {
                py::gil_scoped_release release;
                return reconstruct_path(q.result.graph, q.result, target);
            }();
            py::dict out;
            out["reachable"] = path.status == PathStatus::reachable;
            out["distance"] = path.distance;
            out["vertices"] = path.vertices;
            out["edges"] = path.edges;
            return out;
        });
    py::class_<PreparedBMSSP>(m, "BMSSP2025Engine")
        .def(py::init([](const Graph &g) {
            const auto start = Clock::now();
            auto engine = [&] {
                py::gil_scoped_release release;
                return std::make_unique<PreparedBMSSP>(g);
            }();
            engine->preprocessing_seconds =
                std::chrono::duration<double>(Clock::now() - start).count();
            return engine;
        }))
        .def_property_readonly("metadata",
                               [](const PreparedBMSSP &e) {
                                   py::dict out;
                                   out["preprocessing_seconds"] = e.preprocessing_seconds;
                                   out["preprocessing_count"] = 1;
                                   out["transformed_vertices"] =
                                       e.engine.reduction().graph.vertex_count();
                                   out["transformed_edges"] =
                                       e.engine.reduction().graph.edge_count();
                                   return out;
                               })
        .def("solve", [](const PreparedBMSSP &e, py::handle input) {
            const auto source = integer_id<ExternalVertexId>(input);
            auto result = [&] {
                py::gil_scoped_release release;
                return e.engine.solve(source);
            }();
            auto d = diagnostics(result.diagnostics);
            return Query{std::move(result.shortest_paths), std::move(d), "native_bmssp_2025"};
        });
    py::class_<PreparedDijkstra>(m, "NativeReferenceDijkstra")
        .def(py::init([](const Graph &g) { return PreparedDijkstra{g}; }))
        .def("solve", [](const PreparedDijkstra &e, py::handle input) {
            const auto source = integer_id<ExternalVertexId>(input);
            const auto start = Clock::now();
            auto result = [&] {
                py::gil_scoped_release release;
                return reference_dijkstra(e.graph, source);
            }();
            py::dict d;
            d["query_seconds"] = std::chrono::duration<double>(Clock::now() - start).count();
            d["settled_vertices"] = result.diagnostics.settled_vertices;
            d["scanned_edges"] = result.diagnostics.scanned_edges;
            d["implementation"] = "reference_dijkstra";
            return Query{std::move(result), std::move(d), "native_reference_dijkstra"};
        });
}
