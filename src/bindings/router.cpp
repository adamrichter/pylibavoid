#include "bindings.h"

#include <pybind11/pybind11.h>

#include <string>

#include "libavoid/connector.h"
#include "libavoid/junction.h"
#include "libavoid/router.h"
#include "libavoid/shape.h"

namespace py = pybind11;

namespace pylibavoid {

void register_router(py::module_& m) {
    py::enum_<Avoid::RouterFlag>(m, "RouterFlag", py::arithmetic(),
        "Flags passed to the Router constructor to select which routing "
        "data structures to maintain. Values may be combined with ``|``.")
        .value("PolyLineRouting", Avoid::PolyLineRouting,
            "Maintain the data structures needed for poly-line routes.")
        .value("OrthogonalRouting", Avoid::OrthogonalRouting,
            "Maintain the data structures needed for orthogonal routes.");

    py::enum_<Avoid::RoutingParameter>(m, "RoutingParameter",
        "Penalties and parameters that shape the routes libavoid produces. "
        "Mirrors ``Avoid::RoutingParameter`` (``Avoid::PenaltyType`` in the "
        "pre-3.0 header names) exactly: every value the C++ enum defines is "
        "present here, even ones that are only meaningful once phase-4 "
        "features (clusters, hyperedges, pins) are in scope.")
        .value("segmentPenalty", Avoid::segmentPenalty)
        .value("anglePenalty", Avoid::anglePenalty)
        .value("crossingPenalty", Avoid::crossingPenalty)
        .value("clusterCrossingPenalty", Avoid::clusterCrossingPenalty)
        .value("fixedSharedPathPenalty", Avoid::fixedSharedPathPenalty)
        .value("portDirectionPenalty", Avoid::portDirectionPenalty)
        .value("shapeBufferDistance", Avoid::shapeBufferDistance)
        .value("idealNudgingDistance", Avoid::idealNudgingDistance)
        .value("reverseDirectionPenalty", Avoid::reverseDirectionPenalty);

    py::enum_<Avoid::RoutingOption>(m, "RoutingOption",
        "Boolean routing options. Mirrors ``Avoid::RoutingOption``.")
        .value("nudgeOrthogonalSegmentsConnectedToShapes",
            Avoid::nudgeOrthogonalSegmentsConnectedToShapes)
        .value("improveHyperedgeRoutesMovingJunctions",
            Avoid::improveHyperedgeRoutesMovingJunctions)
        .value("penaliseOrthogonalSharedPathsAtConnEnds",
            Avoid::penaliseOrthogonalSharedPathsAtConnEnds)
        .value("nudgeOrthogonalTouchingColinearSegments",
            Avoid::nudgeOrthogonalTouchingColinearSegments)
        .value("performUnifyingNudgingPreprocessingStep",
            Avoid::performUnifyingNudgingPreprocessingStep)
        .value("improveHyperedgeRoutesMovingAddingAndDeletingJunctions",
            Avoid::improveHyperedgeRoutesMovingAddingAndDeletingJunctions)
        .value("nudgeSharedPathsWithCommonEndPoint",
            Avoid::nudgeSharedPathsWithCommonEndPoint);

    m.attr("zeroParamValue") = py::float_(Avoid::zeroParamValue);
    m.attr("chooseSensibleParamValue") = py::float_(Avoid::chooseSensibleParamValue);

    py::class_<Avoid::Router>(m, "Router",
        "A libavoid router instance. Owns the shapes and connectors "
        "registered against it; destroying the Router deletes them all, "
        "so do not hold Python references to shapes or connectors past "
        "the Router's lifetime. "
        "(Shape and connector wrappers land in the next PRs; this PR "
        "exposes the router's configuration surface only.)")
        .def(py::init<unsigned int>(), py::arg("flags"),
            "Construct a router. ``flags`` is a bitwise-OR of "
            ":class:`RouterFlag` values (or their integer equivalents). "
            "Passing 0 produces a router that cannot route anything.")
        .def("process_transaction", &Avoid::Router::processTransaction,
            "Process any pending shape/connector changes, recomputing "
            "affected routes. Returns ``True`` if anything was done and "
            "``False`` if there was nothing pending. Call this after each "
            "batch of edits when :py:meth:`transaction_use` is ``True`` "
            "(the default).")
        .def("set_transaction_use", &Avoid::Router::setTransactionUse,
            py::arg("use"),
            "Enable or disable transactional behaviour. With transactions "
            "on (the default) changes are queued until "
            ":py:meth:`process_transaction` is called; with them off, "
            "every change is processed immediately.")
        .def("transaction_use", &Avoid::Router::transactionUse,
            "Current transactional behaviour — see :py:meth:`set_transaction_use`.")
        .def("set_routing_parameter",
            [](Avoid::Router& r, Avoid::RoutingParameter param, double value) {
                r.setRoutingParameter(param, value);
            },
            py::arg("parameter"), py::arg("value") = Avoid::chooseSensibleParamValue,
            "Set a routing penalty or parameter. Passing "
            ":data:`chooseSensibleParamValue` (the default) asks libavoid "
            "to pick a sensible default for that parameter.")
        .def("routing_parameter",
            [](const Avoid::Router& r, Avoid::RoutingParameter param) {
                // routingParameter is not const-qualified upstream; the
                // const_cast lets Python callers read values without
                // triggering a needless non-const method. Safe: reading a
                // parameter does not mutate the router.
                return const_cast<Avoid::Router&>(r).routingParameter(param);
            }, py::arg("parameter"),
            "Return the current value of a routing parameter.")
        .def("set_routing_option", &Avoid::Router::setRoutingOption,
            py::arg("option"), py::arg("value"),
            "Set a boolean routing option.")
        .def("routing_option",
            [](const Avoid::Router& r, Avoid::RoutingOption opt) {
                return const_cast<Avoid::Router&>(r).routingOption(opt);
            }, py::arg("option"),
            "Return the current value of a routing option.")
        .def("set_routing_penalty",
            [](Avoid::Router& r, Avoid::RoutingParameter param, double value) {
                r.setRoutingPenalty(param, value);
            },
            py::arg("parameter"), py::arg("value") = Avoid::chooseSensibleParamValue,
            "Convenience alias for :py:meth:`set_routing_parameter`; "
            "provided because libavoid's own documentation uses the "
            "two names interchangeably for penalty-style parameters.")
        .def("exists_invalid_orthogonal_paths",
            &Avoid::Router::existsInvalidOrthogonalPaths,
            "Return ``True`` if any orthogonal connector in the current "
            "layout fails internal validity checks. Used by a handful of "
            "upstream tests as their sole pass/fail signal.")
        .def("exists_orthogonal_segment_overlap",
            &Avoid::Router::existsOrthogonalSegmentOverlap,
            py::arg("at_ends") = false,
            "Return ``True`` if any two orthogonal connector segments "
            "overlap. Upstream test helper; pass ``at_ends=True`` to only "
            "flag overlaps at endpoints.")
        .def("exists_orthogonal_fixed_segment_overlap",
            &Avoid::Router::existsOrthogonalFixedSegmentOverlap,
            py::arg("at_ends") = false,
            "Return ``True`` if any pair of fixed orthogonal connector "
            "segments overlap. Used by the `inlineoverlap` family of "
            "upstream regression tests as their pass/fail signal.")
        .def("exists_orthogonal_touching_paths",
            &Avoid::Router::existsOrthogonalTouchingPaths,
            "Return ``True`` if any two orthogonal connector paths "
            "touch along a common segment. Used by the `inlineoverlap01` "
            "and `restrictedNudging` regression tests.")
        .def("exists_crossings",
            &Avoid::Router::existsCrossings,
            py::arg("optimised_for_connector_type") = false,
            "Return the number of times connectors cross one another in "
            "the current layout. When ``optimised_for_connector_type`` is "
            "true the count is computed by the faster path used for "
            "orthogonal-only routing. Used by the `orthordering`, "
            "`penaltyRerouting01`, and `finalSegmentNudging1` regression "
            "tests.")
        .def("delete_shape", &Avoid::Router::deleteShape, py::arg("shape"),
            "Queue the removal of ``shape`` from the router. When the "
            "next :py:meth:`process_transaction` runs, the shape's "
            "underlying C++ object is freed; after that the Python "
            "ShapeRef wrapper is invalid and must not be touched. "
            "This mirrors libavoid's C++ semantics — the router, not "
            "the caller, owns shapes.\n"
            "\n"
            "Important: call :py:meth:`process_transaction` between "
            "adding a shape and deleting it. libavoid's action queue "
            "sorts so that a pending ShapeAdd and ShapeRemove for the "
            "same object execute in an order that dereferences the "
            "freed pointer. A ``COLA_ASSERT`` in libavoid warns of "
            "this but it is compiled out of release builds, so the "
            "failure mode is a silent use-after-free rather than an "
            "exception.")
        .def("move_shape",
            [](Avoid::Router& r, Avoid::ShapeRef* shape, const Avoid::Polygon& newPoly) {
                r.moveShape(shape, newPoly);
            },
            py::arg("shape"), py::arg("new_polygon"),
            "Replace a shape's polygon boundary, marking affected "
            "connectors as needing rerouting. Call "
            ":py:meth:`process_transaction` to actually reroute them "
            "when transactions are enabled (the default).")
        .def("move_shape",
            [](Avoid::Router& r, Avoid::ShapeRef* shape, double dx, double dy) {
                r.moveShape(shape, dx, dy);
            },
            py::arg("shape"), py::arg("dx"), py::arg("dy"),
            "Translate a shape by (``dx``, ``dy``). Same rerouting "
            "semantics as the polygon-form overload.")
        .def("delete_connector", &Avoid::Router::deleteConnector,
            py::arg("connector"),
            "Remove and free ``connector``. Unlike "
            ":py:meth:`delete_shape`, this deletes the underlying "
            "C++ object immediately; the Python ConnRef wrapper is "
            "invalid from this point and must not be touched.")
        .def("delete_junction", &Avoid::Router::deleteJunction,
            py::arg("junction"),
            "Queue the removal of ``junction`` from the router. The "
            "underlying C++ object is freed during the next "
            ":py:meth:`process_transaction`; after that the Python "
            "JunctionRef wrapper is invalid and must not be "
            "touched. Connectors attached to the junction are "
            "marked for rerouting.")
        .def("move_junction",
            [](Avoid::Router& r, Avoid::JunctionRef* junction, const Avoid::Point& newPosition) {
                r.moveJunction(junction, newPosition);
            },
            py::arg("junction"), py::arg("new_position"),
            "Move ``junction`` to ``new_position``, marking attached "
            "connectors as needing rerouting. Call "
            ":py:meth:`process_transaction` to actually reroute "
            "them when transactions are enabled (the default).")
        .def("move_junction",
            [](Avoid::Router& r, Avoid::JunctionRef* junction, double dx, double dy) {
                r.moveJunction(junction, dx, dy);
            },
            py::arg("junction"), py::arg("dx"), py::arg("dy"),
            "Translate ``junction`` by (``dx``, ``dy``). Same "
            "rerouting semantics as the position-form overload.")
        .def("output_diagram",
            [](Avoid::Router& r, const std::string& name) {
                r.outputDiagram(name);
            },
            py::arg("name") = std::string(),
            "Write a text transcript (``<name>.txt``) of the router's "
            "current state to disk. Useful for reproducing upstream test "
            "scenarios.\n"
            "\n"
            "Note: libavoid's ``outputDiagram`` also writes an SVG when "
            "compiled with ``SVG_OUTPUT`` defined; upstream does not "
            "define it by default and neither do we, so only the .txt "
            "file is produced. A dedicated SVG-emitting method can be "
            "added later if needed.");
}

}  // namespace pylibavoid
