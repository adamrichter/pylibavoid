#include "bindings.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <climits>

#include "libavoid/connectionpin.h"
#include "libavoid/geomtypes.h"
#include "libavoid/junction.h"
#include "libavoid/shape.h"

namespace py = pybind11;

namespace pylibavoid {

void register_connection_pin(py::module_& m) {
    // Module-level constants. Kept as flat int / float attributes
    // to match upstream — promoting them to an enum would change
    // their type and break bare-int / bare-float use sites. See
    // ADR 0004.
    m.attr("CONNECTIONPIN_UNSET") = py::int_(Avoid::CONNECTIONPIN_UNSET);
    m.attr("CONNECTIONPIN_CENTRE") = py::int_(Avoid::CONNECTIONPIN_CENTRE);
    m.attr("ATTACH_POS_TOP") = py::float_(Avoid::ATTACH_POS_TOP);
    m.attr("ATTACH_POS_BOTTOM") = py::float_(Avoid::ATTACH_POS_BOTTOM);
    m.attr("ATTACH_POS_CENTRE") = py::float_(Avoid::ATTACH_POS_CENTRE);
    m.attr("ATTACH_POS_LEFT") = py::float_(Avoid::ATTACH_POS_LEFT);
    m.attr("ATTACH_POS_RIGHT") = py::float_(Avoid::ATTACH_POS_RIGHT);
    m.attr("ATTACH_POS_MIN_OFFSET") = py::float_(Avoid::ATTACH_POS_MIN_OFFSET);
    m.attr("ATTACH_POS_MAX_OFFSET") = py::float_(Avoid::ATTACH_POS_MAX_OFFSET);

    // Lifetime contract mirrors ShapeRef / ConnRef / JunctionRef:
    // the parent shape (or junction) owns every ShapeConnectionPin.
    // py::nodelete prevents Python GC from freeing the C++ object,
    // and py::keep_alive<1, 2> on each constructor ties the pin's
    // wrapper lifetime to its parent. See ADR 0004 §Lifetime.
    py::class_<Avoid::ShapeConnectionPin, std::unique_ptr<Avoid::ShapeConnectionPin, py::nodelete>>(
            m, "ShapeConnectionPin",
        "A fixed attachment point on a shape (or junction) that "
        "connectors can route to by class ID.\n"
        "\n"
        "Pin positions move with their parent shape. Connectors "
        "constructed with ``ConnEnd(shape, class_id)`` will attach "
        "to a pin on ``shape`` whose class ID matches.\n"
        "\n"
        "Like :class:`ShapeRef` and :class:`JunctionRef`, ownership "
        "belongs to the parent — do not hold a Python "
        "ShapeConnectionPin past its parent's lifetime, and do not "
        "expect a destructor call to do anything.")
        .def(py::init([](Avoid::ShapeRef* shape, unsigned int classId,
                         double xOffset, double yOffset, bool proportional,
                         double insideOffset, unsigned int visDirs) {
                return new Avoid::ShapeConnectionPin(
                    shape, classId, xOffset, yOffset, proportional,
                    insideOffset,
                    static_cast<Avoid::ConnDirFlags>(visDirs));
            }),
            py::arg("shape"), py::arg("class_id"),
            py::arg("x_offset"), py::arg("y_offset"),
            py::arg("proportional"), py::arg("inside_offset"),
            py::arg("visibility_directions"),
            py::keep_alive<1, 2>(),
            "Construct a pin on ``shape``.\n"
            "\n"
            "If ``proportional`` is True the offsets are fractions of "
            "the shape's width/height (use the ``ATTACH_POS_*`` "
            "constants for readability); otherwise they are absolute "
            "distances from the shape's lower-X / lower-Y border.\n"
            "\n"
            "``inside_offset`` shifts the pin inward from a boundary "
            "position (useful for orthogonal routing). "
            "``visibility_directions`` is a bitwise-OR of "
            ":class:`ConnDirFlag` values; pass "
            "``ConnDirFlag.ConnDirNone`` to have libavoid pick a "
            "direction based on the pin's location.")
        .def(py::init([](Avoid::JunctionRef* junction, unsigned int classId,
                         unsigned int visDirs) {
                return new Avoid::ShapeConnectionPin(
                    junction, classId,
                    static_cast<Avoid::ConnDirFlags>(visDirs));
            }),
            py::arg("junction"), py::arg("class_id"),
            py::arg("visibility_directions") =
                static_cast<unsigned int>(Avoid::ConnDirNone),
            py::keep_alive<1, 2>(),
            "Construct a pin on ``junction``. The :class:`JunctionRef` "
            "constructor already creates four pins (up/down/left/right) "
            "automatically; this overload is rarely needed from user "
            "code, exposed mainly for parity with the C++ API.")
        .def("set_connection_cost",
            &Avoid::ShapeConnectionPin::setConnectionCost,
            py::arg("cost"),
            "Bias pin selection. When several pins share a class ID, "
            "lower-cost pins are preferred over higher-cost ones, "
            "before libavoid falls back to picking the pin that "
            "produces the cheapest route.")
        .def("position",
            [](const Avoid::ShapeConnectionPin& pin, py::object new_poly) {
                if (new_poly.is_none()) {
                    return pin.position();
                }
                return pin.position(new_poly.cast<const Avoid::Polygon&>());
            },
            py::arg("new_poly") = py::none(),
            "Return the pin's current absolute position. Pass "
            "``new_poly`` to compute the position the pin *would* "
            "have if its parent shape's boundary were replaced; "
            "the default uses the shape's current boundary.")
        .def("directions",
            [](const Avoid::ShapeConnectionPin& pin) {
                return static_cast<unsigned int>(pin.directions());
            },
            "The pin's visibility-direction bitmask, as a plain int "
            "so callers can ``value & ConnDirFlag.ConnDirLeft`` the "
            "usual way.")
        .def_property("exclusive",
            &Avoid::ShapeConnectionPin::isExclusive,
            &Avoid::ShapeConnectionPin::setExclusive,
            "Whether at most one connector may attach to this pin. "
            "Defaults: True for pins with a specific visibility "
            "direction, False for pins visible in all directions.")
        .def("ids",
            [](const Avoid::ShapeConnectionPin& pin) {
                auto ids = pin.ids();
                return py::make_tuple(ids.first, ids.second);
            },
            "Return ``(containing_object_id, class_id)``.");
}

}  // namespace pylibavoid
