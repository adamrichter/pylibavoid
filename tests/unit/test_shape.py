"""ShapeRef wrapper tests.

Phase 2 PR 3. First type with real lifetime implications: libavoid's
Router owns ShapeRef instances and deletes them on destruction, so the
Python wrapper must never delete the C++ object itself, and a Python
ShapeRef must keep the Router alive.
"""

from __future__ import annotations

import gc
import weakref

import pytest

from libavoid_py import (
    Point,
    Polygon,
    Rectangle,
    Router,
    RouterFlag,
    ShapeRef,
)


def _make_router() -> Router:
    return Router(RouterFlag.PolyLineRouting | RouterFlag.OrthogonalRouting)


class TestConstruction:
    def test_from_rectangle(self) -> None:
        r = _make_router()
        rect = Rectangle(Point(0.0, 0.0), Point(10.0, 8.0))
        shape = ShapeRef(r, rect)
        assert shape.id() != 0  # libavoid auto-assigns a positive id

    def test_from_generic_polygon(self) -> None:
        r = _make_router()
        tri = Polygon(3)
        tri.set_point(0, Point(0.0, 0.0))
        tri.set_point(1, Point(4.0, 0.0))
        tri.set_point(2, Point(2.0, 3.0))
        shape = ShapeRef(r, tri)
        assert shape.polygon().size() == 3

    def test_with_explicit_id(self) -> None:
        r = _make_router()
        rect = Rectangle(Point(0.0, 0.0), Point(1.0, 1.0))
        shape = ShapeRef(r, rect, id=123)
        assert shape.id() == 123


class TestAccessors:
    def _rect_shape(self) -> tuple[Router, ShapeRef]:
        r = _make_router()
        rect = Rectangle(Point(0.0, 0.0), Point(10.0, 4.0))
        return r, ShapeRef(r, rect)

    def test_polygon_returns_four_corners(self) -> None:
        _, shape = self._rect_shape()
        poly = shape.polygon()
        assert poly.size() == 4
        corners = {(poly.at(i).x, poly.at(i).y) for i in range(4)}
        assert corners == {(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (0.0, 4.0)}

    def test_position_is_centre(self) -> None:
        _, shape = self._rect_shape()
        pos = shape.position()
        assert pos == Point(5.0, 2.0)

    def test_routing_box_contains_shape(self) -> None:
        _, shape = self._rect_shape()
        box = shape.routing_box()
        # With the default shapeBufferDistance of 0, the routing box
        # equals the polygon bounds.
        assert box.min.x <= 0.0 and box.min.y <= 0.0
        assert box.max.x >= 10.0 and box.max.y >= 4.0

    def test_routing_polygon_has_points(self) -> None:
        _, shape = self._rect_shape()
        assert shape.routing_polygon().size() >= 4


class TestSetNewPoly:
    def test_replaces_polygon(self) -> None:
        r = _make_router()
        shape = ShapeRef(r, Rectangle(Point(0.0, 0.0), Point(2.0, 2.0)))
        shape.set_new_poly(Rectangle(Point(10.0, 10.0), Point(14.0, 16.0)))
        # Position should reflect the new centre.
        assert shape.position() == Point(12.0, 13.0)


class TestRouterShapeManagement:
    def test_move_shape_by_delta(self) -> None:
        r = _make_router()
        shape = ShapeRef(r, Rectangle(Point(0.0, 0.0), Point(2.0, 2.0)))
        r.move_shape(shape, 10.0, 20.0)
        assert shape.position() == Point(11.0, 21.0)

    def test_move_shape_by_polygon(self) -> None:
        r = _make_router()
        shape = ShapeRef(r, Rectangle(Point(0.0, 0.0), Point(2.0, 2.0)))
        r.move_shape(shape, Rectangle(Point(5.0, 5.0), Point(9.0, 11.0)))
        assert shape.position() == Point(7.0, 8.0)

    def test_delete_shape_lets_router_continue(self) -> None:
        # Realistic flow: add shape, process the add transaction,
        # later remove the shape, process again. After the second
        # process_transaction() the C++ ShapeRef is freed; the Python
        # wrapper is invalid from that point (documented) and must
        # not be touched.
        #
        # The pattern "add + delete_shape in the same transaction" is
        # unsafe: libavoid's processActions sorts ShapeRemove ahead of
        # ShapeAdd and then dereferences the freed pointer in the Add
        # loop. A COLA_ASSERT warns of this but is compiled out in
        # release builds.
        r = _make_router()
        shape = ShapeRef(r, Rectangle(Point(0.0, 0.0), Point(2.0, 2.0)))
        r.process_transaction()  # flush the pending ShapeAdd first
        r.delete_shape(shape)
        assert r.process_transaction() in (True, False)
        del shape
        gc.collect()
        # Router continues to work for further processing.
        assert r.process_transaction() in (True, False)


class TestLifetime:
    def test_dropping_python_shape_ref_does_not_destroy_c_shape(self) -> None:
        # Drop the Python handle; router should still own and report
        # the obstacle when we ask it to process a transaction.
        r = _make_router()
        shape = ShapeRef(r, Rectangle(Point(0.0, 0.0), Point(2.0, 2.0)))
        del shape
        gc.collect()
        # The router has one shape internally but no queued changes
        # that it needs to process. process_transaction must not crash.
        r.process_transaction()

    def test_shape_keeps_router_alive(self) -> None:
        # If the Python user keeps only the shape and lets the router
        # go out of scope, keep_alive must prevent the C++ router from
        # being destroyed — otherwise the shape's underlying storage is
        # freed and position() would hit freed memory.
        r = _make_router()
        shape = ShapeRef(r, Rectangle(Point(0.0, 0.0), Point(4.0, 4.0)))
        router_weakref = weakref.ref(r)
        del r
        gc.collect()
        # Router should still be alive because the shape keeps it so.
        assert router_weakref() is not None
        # And the shape's methods should keep working.
        assert shape.position() == Point(2.0, 2.0)

    def test_router_without_python_shapes_frees_its_shapes(self) -> None:
        # When no Python wrapper holds a shape, dropping the router
        # drops the whole scene. This is the normal lifecycle.
        r = _make_router()
        ShapeRef(r, Rectangle(Point(0.0, 0.0), Point(2.0, 2.0)))
        ShapeRef(r, Rectangle(Point(10.0, 10.0), Point(12.0, 12.0)))
        router_weakref = weakref.ref(r)
        del r
        gc.collect()
        assert router_weakref() is None
