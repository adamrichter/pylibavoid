#include "bindings.h"

#include <pybind11/operators.h>
#include <pybind11/stl.h>

#include <sstream>

#include "libavoid/geomtypes.h"

namespace py = pybind11;

namespace pylibavoid {

namespace {

std::string point_repr(const Avoid::Point& p) {
    std::ostringstream os;
    os << "Point(" << p.x << ", " << p.y << ")";
    return os.str();
}

std::string box_repr(const Avoid::Box& b) {
    std::ostringstream os;
    os << "Box(min=" << point_repr(b.min) << ", max=" << point_repr(b.max) << ")";
    return os.str();
}

std::string polygon_repr(const Avoid::Polygon& p) {
    std::ostringstream os;
    os << "Polygon(size=" << p.size() << ")";
    return os.str();
}

double point_getitem(const Avoid::Point& p, std::size_t dim) {
    if (dim > 1) {
        throw py::index_error("Point index out of range (valid: 0, 1)");
    }
    return p[dim];
}

void point_setitem(Avoid::Point& p, std::size_t dim, double value) {
    if (dim > 1) {
        throw py::index_error("Point index out of range (valid: 0, 1)");
    }
    p[dim] = value;
}

const Avoid::Point& polygon_getitem(const Avoid::Polygon& p, Py_ssize_t index) {
    const auto size = static_cast<Py_ssize_t>(p.size());
    if (index < 0) {
        index += size;
    }
    if (index < 0 || index >= size) {
        throw py::index_error("Polygon index out of range");
    }
    return p.at(static_cast<std::size_t>(index));
}

void polygon_set_point_checked(Avoid::Polygon& p, std::size_t index, const Avoid::Point& pt) {
    if (index >= p.size()) {
        throw py::index_error("Polygon index out of range");
    }
    p.setPoint(index, pt);
}

}  // namespace

void register_geometry(py::module_& m) {
    m.attr("XDIM") = py::int_(Avoid::XDIM);
    m.attr("YDIM") = py::int_(Avoid::YDIM);

    py::class_<Avoid::Point> point(m, "Point",
        "A point in the plane. Holds an x and y coordinate and an optional "
        "integer ID. Mirrors Avoid::Point from libavoid.");
    point
        .def(py::init([]() {
                // libavoid's default Avoid::Point() initialises id and vn
                // but intentionally leaves x and y uninitialised (fine in
                // C++, surfaces as random memory at the Python boundary).
                // Zero-init here so `Point()` is always safely readable.
                Avoid::Point p;
                p.x = 0.0;
                p.y = 0.0;
                return p;
            }),
            "Construct a point at (0, 0).")
        .def(py::init<double, double>(), py::arg("x"), py::arg("y"),
            "Construct a point at (x, y).")
        .def_readwrite("x", &Avoid::Point::x, "The x coordinate.")
        .def_readwrite("y", &Avoid::Point::y, "The y coordinate.")
        .def_readwrite("id", &Avoid::Point::id,
            "Optional integer ID. Not used by the router; meaningful only "
            "if the caller assigns it.")
        .def(py::self == py::self,
            "Exact equality. For tolerant comparison use :py:meth:`equals`.")
        .def(py::self != py::self)
        .def(py::self < py::self,
            "Lexicographic ordering. Provided so Point can live in sets "
            "and dicts; the ordering has no geometric meaning.")
        .def(py::self + py::self)
        .def(py::self - py::self)
        .def("equals", &Avoid::Point::equals, py::arg("other"), py::arg("epsilon") = 0.0001,
            "Approximate equality; true if |self.x - other.x| and "
            "|self.y - other.y| are both within ``epsilon``.")
        .def("__getitem__", &point_getitem,
            "Dimension access. ``p[0]`` is x, ``p[1]`` is y. "
            "Any other index raises IndexError.")
        .def("__setitem__", &point_setitem)
        .def("__len__", [](const Avoid::Point&) { return 2; })
        .def("__iter__", [](const Avoid::Point& p) {
                return py::make_iterator(&p.x, &p.x + 2);
            }, py::keep_alive<0, 1>(),
            "Iterate over (x, y), so ``tuple(point) == (point.x, point.y)``.")
        .def("__repr__", &point_repr);

    // Vector is a libavoid typedef for Point. Exposing it as a plain
    // Python alias keeps the Python surface 1:1 with the C++ headers:
    // a user reading router.py should see the same name they see in
    // geomtypes.h, not a second, identical class.
    m.attr("Vector") = point;

    py::class_<Avoid::Box>(m, "Box",
        "Axis-aligned bounding box defined by its top-left and "
        "bottom-right corners. Mirrors Avoid::Box.")
        .def(py::init<>(),
            "Construct with min and max both at (0, 0).")
        .def(py::init([](const Avoid::Point& min, const Avoid::Point& max) {
                Avoid::Box b;
                b.min = min;
                b.max = max;
                return b;
            }), py::arg("min"), py::arg("max"),
            "Construct from explicit min and max corners. "
            "libavoid's Box has no such C++ constructor; this is a Python "
            "convenience for the two-field aggregate.")
        .def_readwrite("min", &Avoid::Box::min, "Top-left corner.")
        .def_readwrite("max", &Avoid::Box::max, "Bottom-right corner.")
        .def("width", &Avoid::Box::width, "``max.x - min.x``.")
        .def("height", &Avoid::Box::height, "``max.y - min.y``.")
        .def("__repr__", &box_repr);

    py::class_<Avoid::Polygon> polygon(m, "Polygon",
        "A polygon defined by an ordered list of points. Used both for "
        "shape outlines (closed) and for connector routes (open, via the "
        ":class:`PolyLine` alias). Mirrors Avoid::Polygon.");
    polygon
        .def(py::init<>(),
            "Construct an empty polygon (zero points).")
        .def(py::init<int>(), py::arg("n"),
            "Construct a polygon with ``n`` zero-initialised points. Set "
            "each point afterwards with :py:meth:`set_point`.")
        .def_property("id",
            [](const Avoid::Polygon& p) { return p._id; },
            [](Avoid::Polygon& p, int v) { p._id = v; },
            "Optional integer ID for the polygon. Not used by the router; "
            "meaningful only if the caller assigns it.")
        .def_property("ps",
            [](const Avoid::Polygon& p) { return p.ps; },
            [](Avoid::Polygon& p, std::vector<Avoid::Point> pts) { p.ps = std::move(pts); },
            "The list of points. Reading returns a Python list copy; "
            "assigning replaces the full list. Use :py:meth:`set_point` to "
            "mutate a single position.")
        .def("empty", &Avoid::Polygon::empty, "True if the polygon has zero points.")
        .def("size", &Avoid::Polygon::size, "Number of points in the polygon.")
        .def("at", [](const Avoid::Polygon& p, std::size_t i) -> Avoid::Point {
                if (i >= p.size()) {
                    throw py::index_error("Polygon index out of range");
                }
                return p.at(i);
            }, py::arg("index"),
            "Return the point at ``index``; raises IndexError if out of range.")
        .def("set_point", &polygon_set_point_checked, py::arg("index"), py::arg("point"),
            "Replace the point at ``index``. Raises IndexError if the "
            "polygon does not already have a slot at that position; "
            "Polygon does not auto-grow.")
        .def("clear", &Avoid::Polygon::clear, "Remove all points.")
        .def("__len__", &Avoid::Polygon::size)
        .def("__getitem__", &polygon_getitem, py::return_value_policy::copy)
        .def("__iter__", [](const Avoid::Polygon& p) {
                return py::make_iterator(p.ps.begin(), p.ps.end());
            }, py::keep_alive<0, 1>())
        .def("__repr__", &polygon_repr);

    // PolyLine is a C++ typedef for Polygon; expose as a Python alias so
    // users can write PolyLine without a separate wrapper layer.
    m.attr("PolyLine") = polygon;

    py::class_<Avoid::Rectangle, Avoid::Polygon>(m, "Rectangle",
        "A four-point polygon. Convenience subclass for the common case.")
        .def(py::init<const Avoid::Point&, const Avoid::Point&>(),
            py::arg("top_left"), py::arg("bottom_right"),
            "Construct from two opposing corners.")
        .def(py::init<const Avoid::Point&, double, double>(),
            py::arg("centre"), py::arg("width"), py::arg("height"),
            "Construct from a centre point, width, and height.");
}

}  // namespace pylibavoid
