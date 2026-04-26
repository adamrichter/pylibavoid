#include "bindings.h"

#include <pybind11/pybind11.h>

#include "libavoid/connector.h"
#include "libavoid/geomtypes.h"
#include "libavoid/junction.h"
#include "libavoid/router.h"

namespace py = pybind11;

namespace pylibavoid {

void register_junction(py::module_& m) {
    // Lifetime contract mirrors ShapeRef / ConnRef: the Router owns
    // every JunctionRef. The ctor registers itself with the router;
    // freeing happens through Router::deleteJunction() or when the
    // router is destroyed. We use py::nodelete so Python GC does not
    // call the destructor, and py::keep_alive<1, 2> on the ctor so a
    // Python JunctionRef cannot outlive its Router. See ADR 0003 for
    // the full lifetime story, including the exception around
    // remove_and_merge_connectors().
    py::class_<Avoid::JunctionRef, std::unique_ptr<Avoid::JunctionRef, py::nodelete>>(m, "JunctionRef",
        "A junction point in the router scene.\n"
        "\n"
        "Junctions can act as a meeting point for multiple connectors "
        "(forming a hyperedge) or as an intermediate waypoint for a "
        "single connector. They are obstacles in their own right; other "
        "connectors route around them.\n"
        "\n"
        "Like :class:`ShapeRef` and :class:`ConnRef`, a JunctionRef is "
        "owned by the Router it was constructed with. Remove it with "
        ":py:meth:`Router.delete_junction`; do not hold a Python "
        "JunctionRef past its Router's lifetime.")
        .def(py::init([](Avoid::Router* router, const Avoid::Point& position, unsigned int id) {
                return new Avoid::JunctionRef(router, position, id);
            }),
            py::arg("router"), py::arg("position"), py::arg("id") = 0,
            py::keep_alive<1, 2>(),
            "Create a junction at ``position`` and register it with "
            "``router``. Pass ``id`` 0 (the default) to let libavoid "
            "pick a unique ID; any positive id you supply must be "
            "unique across every object registered with that router.")
        .def_property_readonly("position", &Avoid::JunctionRef::position,
            "The junction's current position as a :class:`Point`.")
        .def_property("position_fixed",
            &Avoid::JunctionRef::positionFixed,
            &Avoid::JunctionRef::setPositionFixed,
            "Whether the router is allowed to move this junction.\n"
            "\n"
            "When ``True`` the junction's position is treated as a hard "
            "constraint. When ``False`` (the default), the router may "
            "suggest a better position via "
            ":py:attr:`recommended_position` if the "
            "``improveHyperedgeRoutesMovingJunctions`` routing option "
            "is on (it is on by default).")
        .def_property_readonly("recommended_position",
            &Avoid::JunctionRef::recommendedPosition,
            "A suggested better position for this junction computed "
            "during routing. Only meaningful when "
            ":py:attr:`position_fixed` is ``False`` and the router has "
            "processed at least one transaction with the "
            "``improveHyperedgeRoutesMovingJunctions`` option enabled.")
        .def("make_rectangle", &Avoid::JunctionRef::makeRectangle,
            py::arg("router"), py::arg("position"),
            "Construct a small :class:`Rectangle` around ``position`` "
            "for use when libavoid needs to treat the junction as a "
            "rectangular obstacle. Provided for parity with the "
            "upstream API; rarely needed from Python.")
        .def("prefer_orthogonal_dimension",
            &Avoid::JunctionRef::preferOrthogonalDimension,
            py::arg("dim"),
            "Hint that connectors leaving this junction should prefer "
            "to leave along ``dim`` (use :data:`XDIM` or :data:`YDIM`).")
        .def("remove_and_merge_connectors",
            [](Avoid::JunctionRef& j) -> Avoid::ConnRef* {
                return j.removeJunctionAndMergeConnectors();
            },
            py::return_value_policy::reference_internal,
            "If the junction has exactly two attached connectors, "
            "remove the junction from the routing scene and merge the "
            "two connectors into one. Returns the merged "
            ":class:`ConnRef`, or ``None`` if the junction had a "
            "different number of attached connectors (in which case "
            "nothing changes).\n"
            "\n"
            "Two ownership notes that mirror upstream's C++ "
            "behaviour:\n"
            "\n"
            "1. The other (consumed) connector is destroyed by this "
            "call. Any Python reference you held to it is now a "
            "dangling pointer; do not touch it.\n"
            "2. The junction itself is **removed from the scene but "
            "not freed**. You must still call "
            ":py:meth:`Router.delete_junction` on it (or let the "
            "Router go out of scope) to release the memory.");
}

}  // namespace pylibavoid
