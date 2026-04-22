#include "bindings.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <list>

#include "libavoid/connector.h"
#include "libavoid/router.h"
#include "libavoid/shape.h"

namespace py = pybind11;

namespace pylibavoid {

void register_shape(py::module_& m) {
    // Lifetime contract:
    //
    //   libavoid's Router owns every ShapeRef. The ShapeRef ctor
    //   registers itself with the Router, and the Router destructor
    //   walks m_obstacles and deletes each shape. ShapeRef's own
    //   header explicitly says: "Do not call this yourself, instead
    //   call Router::deleteShape(). Ownership of this object belongs
    //   to the router scene."
    //
    //   For Python that means two things:
    //
    //   1. The holder must be std::unique_ptr<ShapeRef, py::nodelete>
    //      so Python GC does not call delete and double-free.
    //   2. Any Python ShapeRef wrapper must keep its Router alive —
    //      otherwise a user who drops the Python Router reference but
    //      keeps a shape will see the underlying C++ router get
    //      destroyed (and with it the shape), leaving the Python
    //      ShapeRef pointing at freed memory. We enforce this with
    //      py::keep_alive<1, 2> on the constructor (shape keeps
    //      router alive).
    py::class_<Avoid::ShapeRef, std::unique_ptr<Avoid::ShapeRef, py::nodelete>>(m, "ShapeRef",
        "A shape registered with a Router as an obstacle that "
        "connectors must route around.\n"
        "\n"
        "The Router owns every ShapeRef; do not hold a Python ShapeRef "
        "past its Router's lifetime. To remove a shape from the Router "
        "call :py:meth:`Router.delete_shape`; after that the Python "
        "ShapeRef wrapper is invalid and must not be touched.")
        .def(py::init([](Avoid::Router* router, Avoid::Polygon& poly, unsigned int id) {
                // The ctor registers the new shape with the router; we
                // do not hold onto the raw pointer past this point.
                return new Avoid::ShapeRef(router, poly, id);
            }),
            py::arg("router"), py::arg("polygon"), py::arg("id") = 0,
            py::keep_alive<1, 2>(),
            "Create a shape with the given polygon boundary and register "
            "it with ``router``. Pass ``id`` 0 (the default) to let "
            "libavoid pick a unique ID; any positive id you supply must "
            "be unique across every object registered with that router.")
        .def("id", &Avoid::ShapeRef::id,
            "The shape's integer ID.")
        .def("polygon",
            [](const Avoid::ShapeRef& s) { return s.polygon(); },
            "Return a copy of the shape's polygon boundary.")
        .def("position", &Avoid::ShapeRef::position,
            "The shape's centre position as a :class:`Point`.")
        .def("routing_box", &Avoid::ShapeRef::routingBox,
            "The axis-aligned bounding box libavoid uses when routing "
            "around this shape (the polygon's bounds plus the router's "
            "shape buffer distance).")
        .def("routing_polygon", &Avoid::ShapeRef::routingPolygon,
            "The polygon libavoid uses as the routing obstacle. For "
            "simple shapes this matches :py:meth:`polygon` plus the "
            "configured buffer distance.")
        .def("set_new_poly", &Avoid::ShapeRef::setNewPoly, py::arg("polygon"),
            "Replace the shape's polygon boundary. The Router must "
            "reprocess affected connectors, either immediately or on "
            "the next :py:meth:`Router.process_transaction` depending "
            "on the transaction setting.")
        .def("attached_connectors",
            [](const Avoid::ShapeRef& s) {
                // Convert the ConnRefList (std::list<ConnRef*>) to a
                // std::vector, which pybind11/stl.h converts to a
                // Python list. The returned wrappers reference router-
                // owned connectors; pybind11 registers them under the
                // nodelete holder just like newly-constructed ones.
                auto conns = s.attachedConnectors();
                return std::vector<Avoid::ConnRef*>(conns.begin(), conns.end());
            },
            py::return_value_policy::reference_internal,
            "List the :class:`ConnRef` instances whose endpoints "
            "attach to this shape. Only populated after a connector "
            "with a ConnEnd on this shape has been processed.");
}

}  // namespace pylibavoid
