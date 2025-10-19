// bindings.cpp
// Production-grade pybind11 bindings for BMSSP C++ core
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "bmssp.cpp"

namespace py = pybind11;

PYBIND11_MODULE(bmssp, m) {
    m.doc() = "BMSSP Routing C++ bindings";

    m.def("solve_bmssp", &solve_bmssp,
        py::arg("graph"), py::arg("sources"), py::arg("targets"),
        "Solve the Bidirectional Multi-Source Shortest Path problem."
    );

    // Add more bindings as needed for production features
}
