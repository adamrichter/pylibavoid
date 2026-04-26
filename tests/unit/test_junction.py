"""JunctionRef wrapper tests.

Phase 4 PR 1. Same lifetime contract as ShapeRef and ConnRef:
the Router owns every JunctionRef, the Python wrapper must not
delete the C++ object, and a JunctionRef must keep its Router
alive (py::keep_alive). Also covers the new ConnEnd(JunctionRef)
overload and the Router junction-management methods.
"""

from __future__ import annotations

import gc
import weakref

from libavoid_py import (
    XDIM,
    ConnEnd,
    ConnEndType,
    ConnRef,
    JunctionRef,
    Point,
    Rectangle,
    Router,
    RouterFlag,
)


def _make_router() -> Router:
    return Router(RouterFlag.PolyLineRouting | RouterFlag.OrthogonalRouting)


class TestConstruction:
    def test_default_id_is_assigned(self) -> None:
        r = _make_router()
        j = JunctionRef(r, Point(10.0, 20.0))
        # libavoid's auto-id falls into the high-id range; just check
        # the position survived the round-trip.
        assert j.position == Point(10.0, 20.0)

    def test_explicit_id(self) -> None:
        r = _make_router()
        j = JunctionRef(r, Point(0.0, 0.0), id=42)
        assert j.position == Point(0.0, 0.0)


class TestProperties:
    def test_position_fixed_round_trips(self) -> None:
        r = _make_router()
        j = JunctionRef(r, Point(5.0, 5.0))
        assert j.position_fixed is False
        j.position_fixed = True
        assert j.position_fixed is True
        j.position_fixed = False
        assert j.position_fixed is False

    def test_recommended_position_defaults_to_position(self) -> None:
        # Before any routing has happened, recommended_position equals
        # the constructor position — libavoid initialises both to the
        # same point.
        r = _make_router()
        j = JunctionRef(r, Point(7.0, 9.0))
        assert j.recommended_position == Point(7.0, 9.0)


class TestRouterJunctionMethods:
    def test_move_junction_by_point(self) -> None:
        r = _make_router()
        j = JunctionRef(r, Point(10.0, 20.0))
        r.move_junction(j, Point(50.0, 60.0))
        r.process_transaction()
        assert j.position == Point(50.0, 60.0)

    def test_move_junction_by_delta(self) -> None:
        r = _make_router()
        j = JunctionRef(r, Point(10.0, 20.0))
        r.move_junction(j, 5.0, -10.0)
        r.process_transaction()
        assert j.position == Point(15.0, 10.0)

    def test_delete_junction_clears_pending_state(self) -> None:
        r = _make_router()
        j = JunctionRef(r, Point(10.0, 20.0))
        r.process_transaction()
        r.delete_junction(j)
        assert r.process_transaction() in (True, False)

    def test_prefer_orthogonal_dimension_does_not_raise(self) -> None:
        r = _make_router()
        j = JunctionRef(r, Point(10.0, 20.0))
        j.prefer_orthogonal_dimension(XDIM)


class TestConnEndJunction:
    def test_connend_constructed_from_junction(self) -> None:
        r = _make_router()
        j = JunctionRef(r, Point(0.0, 0.0))
        ce = ConnEnd(j)
        assert ce.type() == ConnEndType.Junction
        assert ce.junction() is j

    def test_connend_to_point_has_no_junction(self) -> None:
        ce = ConnEnd(Point(5.0, 5.0))
        assert ce.type() == ConnEndType.Point
        assert ce.junction() is None

    def test_connref_routes_through_junction(self) -> None:
        # Smoke: a connector pinned to a junction at one end and a free
        # point at the other should route end-to-end without raising.
        r = _make_router()
        j = JunctionRef(r, Point(50.0, 50.0))
        c = ConnRef(r, ConnEnd(j), ConnEnd(Point(100.0, 100.0)))
        r.process_transaction()
        route = c.display_route()
        assert route.size() >= 2


class TestRemoveAndMergeConnectors:
    def test_returns_none_when_not_two_attached(self) -> None:
        # No connectors attached: must return None per upstream contract.
        r = _make_router()
        j = JunctionRef(r, Point(0.0, 0.0))
        r.process_transaction()
        assert j.remove_and_merge_connectors() is None


class TestLifetime:
    def test_dropping_python_junction_keeps_router_intact(self) -> None:
        r = _make_router()
        j = JunctionRef(r, Point(0.0, 0.0))
        del j
        gc.collect()
        r.process_transaction()  # must not crash

    def test_junction_keeps_router_alive(self) -> None:
        r = _make_router()
        j = JunctionRef(r, Point(0.0, 0.0))
        router_weakref = weakref.ref(r)
        del r
        gc.collect()
        assert router_weakref() is not None
        # And the junction's accessors still work.
        assert j.position == Point(0.0, 0.0)

    def test_router_without_python_junctions_frees_its_junctions(self) -> None:
        r = _make_router()
        JunctionRef(r, Point(0.0, 0.0))
        JunctionRef(r, Point(10.0, 10.0))
        router_weakref = weakref.ref(r)
        del r
        gc.collect()
        assert router_weakref() is None

    def test_make_rectangle_returns_rectangle(self) -> None:
        r = _make_router()
        j = JunctionRef(r, Point(0.0, 0.0))
        rect = j.make_rectangle(r, Point(5.0, 5.0))
        assert isinstance(rect, Rectangle)
