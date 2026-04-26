#include <pybind11/pybind11.h>

#include "bindings.h"

#ifndef LIBAVOID_COMMIT_HASH
#  error "LIBAVOID_COMMIT_HASH must be defined by the build system"
#endif

namespace py = pybind11;

PYBIND11_MODULE(_core, m) {
    m.doc() = "libavoid-py — Python bindings for libavoid.";

    m.def(
        "version",
        []() { return std::string(LIBAVOID_COMMIT_HASH); },
        "Return the upstream libavoid git commit hash this wheel was built against.\n"
        "\n"
        "The hash is resolved at build time from the vendored submodule "
        "(or from LIBAVOID_COMMIT.txt when building from an sdist) and "
        "baked into the extension. It is a 40-character hex string."
    );

    pylibavoid::register_geometry(m);
    // Register_connector declares ConnRef and ConnEnd, which Router's
    // delete_connector method and ShapeRef's attached_connectors both
    // reference; register it before the Router and ShapeRef bindings
    // so pybind11 knows about those types when building the method
    // signatures. Junction-related signatures in connector.cpp /
    // router.cpp use forward-declared JunctionRef* arguments resolved
    // at call time — register_junction below registers the type
    // before any user code can invoke those signatures.
    pylibavoid::register_connector(m);
    pylibavoid::register_router(m);
    pylibavoid::register_shape(m);
    pylibavoid::register_junction(m);
}
