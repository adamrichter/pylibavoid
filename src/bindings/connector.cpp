#include "bindings.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "libavoid/connector.h"
#include "libavoid/connend.h"
#include "libavoid/router.h"

namespace py = pybind11;

namespace pylibavoid {

void register_connector(py::module_& m) {
    py::enum_<Avoid::ConnDirFlag>(m, "ConnDirFlag", py::arithmetic(),
        "Visibility direction flags for a :class:`ConnEnd` that is "
        "located inside a shape. Values are powers of two so they may "
        "be combined with ``|``; ``ConnDirAll`` is the pre-combined "
        "value for all four directions.")
        .value("ConnDirNone", Avoid::ConnDirNone)
        .value("ConnDirUp", Avoid::ConnDirUp)
        .value("ConnDirDown", Avoid::ConnDirDown)
        .value("ConnDirLeft", Avoid::ConnDirLeft)
        .value("ConnDirRight", Avoid::ConnDirRight)
        .value("ConnDirAll", Avoid::ConnDirAll);

    // libavoid's ConnType enum values are named ConnType_None,
    // ConnType_PolyLine, ConnType_Orthogonal. In Python we drop the
    // redundant prefix; the None sentinel is used only inside the
    // router's default-arg handling (not part of the user-facing
    // routing types) so we omit it here.
    py::enum_<Avoid::ConnType>(m, "ConnType",
        "The style of routing for a :class:`ConnRef`.")
        .value("PolyLine", Avoid::ConnType_PolyLine,
            "Shortest-path poly-line route that avoids obstacles. "
            "Requires :py:attr:`RouterFlag.PolyLineRouting`.")
        .value("Orthogonal", Avoid::ConnType_Orthogonal,
            "Shortest-path orthogonal (axis-aligned) route that "
            "avoids obstacles. Requires "
            ":py:attr:`RouterFlag.OrthogonalRouting`.");

    py::enum_<Avoid::ConnEndType>(m, "ConnEndType",
        "What a :class:`ConnEnd` attaches to. Returned by "
        ":py:meth:`ConnEnd.type`.")
        .value("Point", Avoid::ConnEndPoint,
            "A free-floating point.")
        .value("ShapePin", Avoid::ConnEndShapePin,
            "Attached to a shape via a connection pin (phase-4 "
            "feature; not constructible from Python yet).")
        .value("Junction", Avoid::ConnEndJunction,
            "Attached to a junction (phase-4 feature; not "
            "constructible from Python yet).")
        .value("Empty", Avoid::ConnEndEmpty,
            "The default-constructed, not-yet-specified state.");

    py::class_<Avoid::ConnEnd>(m, "ConnEnd",
        "An endpoint for a :class:`ConnRef`. The point-based "
        "constructors are the ones usable today; shape-pin and "
        "junction attachment are phase-4 features.")
        .def(py::init<>(),
            "Empty ConnEnd. Its :py:meth:`type` is "
            ":py:attr:`ConnEndType.Empty`; use one of the other "
            "constructors for an endpoint the router can reach.")
        .def(py::init<const Avoid::Point&>(), py::arg("point"),
            "Free-floating endpoint at ``point``.")
        .def(py::init<const Avoid::Point&, Avoid::ConnDirFlags>(),
            py::arg("point"), py::arg("visibility_directions"),
            "Free-floating endpoint with preferred visibility "
            "directions used when the point lies inside a shape's "
            "bounding box. Pass a combination of "
            ":class:`ConnDirFlag` values.")
        .def("type", &Avoid::ConnEnd::type,
            "What kind of endpoint this is (:class:`ConnEndType`).")
        .def("position", &Avoid::ConnEnd::position,
            "The point this endpoint represents.")
        .def("directions",
            [](const Avoid::ConnEnd& e) {
                return static_cast<unsigned int>(e.directions());
            },
            "The visibility-direction bitmask. Returned as a plain "
            "int so callers can ``value & ConnDirFlag.ConnDirLeft`` "
            "the usual way.");

    // Lifetime contract is the same as ShapeRef: Router owns every
    // ConnRef, so we use py::nodelete and keep the Python Router
    // alive as long as any ConnRef references it. Router::deleteConnector
    // frees the C++ object immediately (unlike deleteShape, which queues);
    // after that call the Python ConnRef is invalid.
    py::class_<Avoid::ConnRef, std::unique_ptr<Avoid::ConnRef, py::nodelete>>(m, "ConnRef",
        "A connector that the router will route around obstacles. "
        "Owned by the Router it was constructed with; remove it with "
        ":py:meth:`Router.delete_connector`.")
        .def(py::init([](Avoid::Router* router, unsigned int id) {
                return new Avoid::ConnRef(router, id);
            }),
            py::arg("router"), py::arg("id") = 0,
            py::keep_alive<1, 2>(),
            "Construct a connector with no endpoints yet. Set them "
            "via :py:meth:`set_endpoints` (or the individual setters) "
            "before calling :py:meth:`Router.process_transaction`.")
        .def(py::init([](Avoid::Router* router, const Avoid::ConnEnd& src,
                         const Avoid::ConnEnd& dst, unsigned int id) {
                return new Avoid::ConnRef(router, src, dst, id);
            }),
            py::arg("router"), py::arg("src"), py::arg("dst"),
            py::arg("id") = 0,
            py::keep_alive<1, 2>(),
            "Construct a connector with source and destination "
            "endpoints supplied up front.")
        .def("id", &Avoid::ConnRef::id,
            "The connector's integer ID.")
        .def("set_endpoints", &Avoid::ConnRef::setEndpoints,
            py::arg("src"), py::arg("dst"),
            "Replace both endpoints in one call.")
        .def("set_source_endpoint", &Avoid::ConnRef::setSourceEndpoint,
            py::arg("src"),
            "Replace the source endpoint.")
        .def("set_dest_endpoint", &Avoid::ConnRef::setDestEndpoint,
            py::arg("dst"),
            "Replace the destination endpoint.")
        .def("needs_repaint", &Avoid::ConnRef::needsRepaint,
            "Return ``True`` if the route has been recomputed since "
            "the last read of :py:meth:`display_route`.")
        .def("display_route",
            [](Avoid::ConnRef& c) { return c.displayRoute(); },
            py::return_value_policy::copy,
            "Return the user-facing routed path as a :class:`PolyLine` "
            "(a :class:`Polygon`). Returns a copy; the underlying "
            "libavoid route may be replaced on the next "
            ":py:meth:`Router.process_transaction`.")
        .def("routing_type", &Avoid::ConnRef::routingType,
            "The connector's current :class:`ConnType`.")
        .def("set_routing_type", &Avoid::ConnRef::setRoutingType,
            py::arg("type"),
            "Switch this connector between poly-line and orthogonal "
            "routing. The router must have been constructed with the "
            "corresponding :class:`RouterFlag`.")
        .def("endpoint_conn_ends",
            [](const Avoid::ConnRef& c) {
                auto ends = const_cast<Avoid::ConnRef&>(c).endpointConnEnds();
                return py::make_tuple(ends.first, ends.second);
            },
            "Return the current ``(src, dst)`` :class:`ConnEnd` pair "
            "as a tuple.\n"
            "\n"
            "Note: endpoints set by the constructor or by "
            ":py:meth:`set_endpoints` / :py:meth:`set_source_endpoint` "
            "/ :py:meth:`set_dest_endpoint` are queued; they do not "
            "become readable here until the next "
            ":py:meth:`Router.process_transaction` runs. Calling this "
            "method before the transaction processes emits a libavoid "
            "warning to stderr and returns empty ConnEnds.");
}

}  // namespace pylibavoid
