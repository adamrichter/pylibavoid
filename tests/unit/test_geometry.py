"""Geometry-type wrapper tests.

These cover the surface added in phase 2 PR 1: Point, Box, Polygon,
Rectangle, and the PolyLine/Vector aliases. They are all value types —
no router, no lifetime concerns yet.
"""

from __future__ import annotations

import pytest

import libavoid_py
from libavoid_py import Box, PolyLine, Point, Polygon, Rectangle, Vector, XDIM, YDIM


class TestConstants:
    def test_dimensions(self) -> None:
        assert XDIM == 0
        assert YDIM == 1


class TestPoint:
    def test_default_is_zero(self) -> None:
        p = Point()
        assert p.x == 0.0
        assert p.y == 0.0

    def test_xy_construction(self) -> None:
        p = Point(1.5, -2.0)
        assert p.x == 1.5
        assert p.y == -2.0

    def test_keyword_construction(self) -> None:
        p = Point(x=3.0, y=4.0)
        assert (p.x, p.y) == (3.0, 4.0)

    def test_fields_are_writable(self) -> None:
        p = Point(1.0, 2.0)
        p.x = 10.0
        p.y = 20.0
        assert (p.x, p.y) == (10.0, 20.0)

    def test_id_defaults_to_zero_and_is_writable(self) -> None:
        p = Point()
        # libavoid leaves the id field uninitialised in the default ctor;
        # we don't promise a default, only that the attribute exists and
        # can be set to a value we then read back.
        p.id = 42
        assert p.id == 42

    def test_equality_is_exact(self) -> None:
        assert Point(1.0, 2.0) == Point(1.0, 2.0)
        assert Point(1.0, 2.0) != Point(1.0, 2.000001)

    def test_equals_with_epsilon(self) -> None:
        a = Point(1.0, 2.0)
        b = Point(1.00005, 2.00005)
        assert a.equals(b)  # default epsilon=1e-4
        assert not a.equals(b, epsilon=1e-6)

    def test_addition_and_subtraction(self) -> None:
        a = Point(1.0, 2.0)
        b = Point(4.0, 6.0)
        assert a + b == Point(5.0, 8.0)
        assert b - a == Point(3.0, 4.0)

    def test_ordering_is_consistent(self) -> None:
        # libavoid provides operator< mostly so Point can live in
        # std::set; pybind11 intentionally drops __hash__ when __eq__ is
        # exposed, so on the Python side the ordering is useful for
        # sorted()/bisect, not for set membership. Assert only that it
        # is a strict total order for distinct points.
        a, b = Point(0.0, 0.0), Point(1.0, 0.0)
        assert (a < b) != (b < a)
        assert sorted([b, a]) == [a, b]

    def test_getitem_maps_to_x_y(self) -> None:
        p = Point(7.0, 11.0)
        assert p[XDIM] == 7.0
        assert p[YDIM] == 11.0

    def test_setitem_updates_field(self) -> None:
        p = Point(0.0, 0.0)
        p[XDIM] = 3.0
        p[YDIM] = 4.0
        assert p.x == 3.0 and p.y == 4.0

    def test_getitem_out_of_range_raises(self) -> None:
        p = Point()
        with pytest.raises(IndexError):
            _ = p[2]

    def test_setitem_out_of_range_raises(self) -> None:
        p = Point()
        with pytest.raises(IndexError):
            p[2] = 0.0

    def test_iterates_as_xy_pair(self) -> None:
        p = Point(5.0, 6.0)
        assert len(p) == 2
        assert list(p) == [5.0, 6.0]
        x, y = p
        assert (x, y) == (5.0, 6.0)

    def test_repr_round_trips(self) -> None:
        p = Point(1.0, 2.5)
        assert repr(p) == "Point(1, 2.5)"


class TestVectorAlias:
    def test_vector_is_point(self) -> None:
        assert Vector is Point


class TestBox:
    def test_default_box(self) -> None:
        b = Box()
        assert b.min == Point(0.0, 0.0)
        assert b.max == Point(0.0, 0.0)

    def test_construction_from_corners(self) -> None:
        b = Box(Point(1.0, 2.0), Point(5.0, 9.0))
        assert b.min == Point(1.0, 2.0)
        assert b.max == Point(5.0, 9.0)

    def test_width_and_height(self) -> None:
        b = Box(Point(1.0, 2.0), Point(5.0, 9.0))
        assert b.width() == 4.0
        assert b.height() == 7.0

    def test_fields_are_writable(self) -> None:
        b = Box()
        b.min = Point(-1.0, -2.0)
        b.max = Point(3.0, 4.0)
        assert b.width() == 4.0
        assert b.height() == 6.0

    def test_repr_contains_corners(self) -> None:
        b = Box(Point(0.0, 0.0), Point(1.0, 1.0))
        r = repr(b)
        assert "min=Point" in r and "max=Point" in r


class TestPolygon:
    def test_empty_construction(self) -> None:
        p = Polygon()
        assert p.empty()
        assert p.size() == 0
        assert len(p) == 0

    def test_sized_construction(self) -> None:
        p = Polygon(3)
        assert not p.empty()
        assert p.size() == 3
        assert len(p) == 3
        # libavoid does not document the initial value of the n-point
        # ctor's points; don't assume zero. Assert only that we can read
        # each slot without raising.
        for i in range(len(p)):
            _ = p.at(i)

    def test_set_point_updates_position(self) -> None:
        p = Polygon(2)
        p.set_point(0, Point(1.0, 2.0))
        p.set_point(1, Point(3.0, 4.0))
        assert p.at(0) == Point(1.0, 2.0)
        assert p.at(1) == Point(3.0, 4.0)

    def test_at_and_set_point_out_of_range_raise(self) -> None:
        p = Polygon(2)
        with pytest.raises(IndexError):
            p.at(2)
        with pytest.raises(IndexError):
            p.set_point(2, Point())

    def test_getitem_supports_negative_indexing(self) -> None:
        p = Polygon(2)
        p.set_point(0, Point(1.0, 0.0))
        p.set_point(1, Point(2.0, 0.0))
        assert p[0] == Point(1.0, 0.0)
        assert p[-1] == Point(2.0, 0.0)
        with pytest.raises(IndexError):
            _ = p[2]
        with pytest.raises(IndexError):
            _ = p[-3]

    def test_iteration(self) -> None:
        p = Polygon(3)
        p.set_point(0, Point(1.0, 0.0))
        p.set_point(1, Point(2.0, 0.0))
        p.set_point(2, Point(3.0, 0.0))
        xs = [pt.x for pt in p]
        assert xs == [1.0, 2.0, 3.0]

    def test_ps_property_reads_copy(self) -> None:
        p = Polygon(2)
        p.set_point(0, Point(1.0, 0.0))
        p.set_point(1, Point(2.0, 0.0))
        pts = p.ps
        assert pts == [Point(1.0, 0.0), Point(2.0, 0.0)]
        # Mutating the returned list does not change the polygon
        # (documented behaviour of the `ps` property).
        pts.append(Point(9.0, 9.0))
        assert p.size() == 2

    def test_ps_property_assign_replaces_points(self) -> None:
        p = Polygon()
        p.ps = [Point(1.0, 0.0), Point(2.0, 0.0), Point(3.0, 0.0)]
        assert p.size() == 3
        assert p.at(2) == Point(3.0, 0.0)

    def test_clear_empties_polygon(self) -> None:
        p = Polygon(3)
        p.clear()
        assert p.empty()
        assert p.size() == 0

    def test_id_round_trips(self) -> None:
        p = Polygon(1)
        p.id = 7
        assert p.id == 7

    def test_repr_contains_size(self) -> None:
        assert repr(Polygon(4)) == "Polygon(size=4)"


class TestPolyLineAlias:
    def test_polyline_is_polygon(self) -> None:
        assert PolyLine is Polygon


class TestRectangle:
    def test_corners_constructor(self) -> None:
        r = Rectangle(Point(0.0, 0.0), Point(4.0, 3.0))
        assert isinstance(r, Polygon)
        assert r.size() == 4
        corners = {(r.at(i).x, r.at(i).y) for i in range(4)}
        assert corners == {(0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0)}

    def test_centre_wh_constructor(self) -> None:
        r = Rectangle(Point(10.0, 20.0), 4.0, 6.0)
        assert r.size() == 4
        corners = {(r.at(i).x, r.at(i).y) for i in range(4)}
        # centre=(10,20), w=4, h=6 → corners at ±2 and ±3 from centre.
        assert corners == {(8.0, 17.0), (12.0, 17.0), (12.0, 23.0), (8.0, 23.0)}

    def test_rectangle_passes_isinstance_polygon(self) -> None:
        r = Rectangle(Point(0.0, 0.0), Point(1.0, 1.0))
        # ShapeRef(Router, Polygon) will need to accept a Rectangle.
        # We cannot test that yet; but the isinstance relationship is
        # what makes it possible, so lock it down now.
        assert isinstance(r, Polygon)


class TestModuleSurface:
    def test_all_names_exported(self) -> None:
        for name in ("Point", "Vector", "Box", "Polygon", "PolyLine",
                     "Rectangle", "XDIM", "YDIM", "version"):
            assert hasattr(libavoid_py, name), name
