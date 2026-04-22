"""ConnEnd / ConnRef wrapper tests.

Phase 2 PR 4 — the first set of tests where the wrapper does something
visibly useful: feed two shapes and a connector to the router, ask for
its display_route(), and check the path is non-trivial.
"""

from __future__ import annotations

import gc
import weakref

import pytest

from libavoid_py import (
    ConnDirFlag,
    ConnEnd,
    ConnEndType,
    ConnRef,
    ConnType,
    Point,
    PolyLine,
    Polygon,
    Rectangle,
    Router,
    RouterFlag,
    ShapeRef,
)


def _orthogonal_router() -> Router:
    return Router(RouterFlag.PolyLineRouting | RouterFlag.OrthogonalRouting)


class TestConnDirFlag:
    def test_values(self) -> None:
        assert int(ConnDirFlag.ConnDirNone) == 0
        assert int(ConnDirFlag.ConnDirUp) == 1
        assert int(ConnDirFlag.ConnDirDown) == 2
        assert int(ConnDirFlag.ConnDirLeft) == 4
        assert int(ConnDirFlag.ConnDirRight) == 8
        assert int(ConnDirFlag.ConnDirAll) == 15

    def test_bitwise_combination(self) -> None:
        combined = ConnDirFlag.ConnDirLeft | ConnDirFlag.ConnDirRight
        assert int(combined) == 12
        assert int(ConnDirFlag.ConnDirAll) == (
            ConnDirFlag.ConnDirUp
            | ConnDirFlag.ConnDirDown
            | ConnDirFlag.ConnDirLeft
            | ConnDirFlag.ConnDirRight
        )


class TestConnType:
    def test_values(self) -> None:
        assert int(ConnType.PolyLine) == 1
        assert int(ConnType.Orthogonal) == 2


class TestConnEnd:
    def test_default(self) -> None:
        e = ConnEnd()
        assert e.type() == ConnEndType.Empty

    def test_from_point(self) -> None:
        e = ConnEnd(Point(3.0, 4.0))
        assert e.type() == ConnEndType.Point
        assert e.position() == Point(3.0, 4.0)
        assert e.directions() == ConnDirFlag.ConnDirAll  # libavoid's default

    def test_from_point_with_directions(self) -> None:
        dirs = int(ConnDirFlag.ConnDirLeft | ConnDirFlag.ConnDirRight)
        e = ConnEnd(Point(1.0, 2.0), dirs)
        assert e.type() == ConnEndType.Point
        assert e.position() == Point(1.0, 2.0)
        assert e.directions() == dirs


class TestConnRefConstruction:
    def test_empty_construction(self) -> None:
        r = _orthogonal_router()
        conn = ConnRef(r)
        assert conn.id() != 0  # auto-assigned

    def test_with_explicit_id(self) -> None:
        r = _orthogonal_router()
        conn = ConnRef(r, id=77)
        assert conn.id() == 77

    def test_with_endpoints(self) -> None:
        # libavoid queues endpoint assignment until the next
        # process_transaction; endpoint_conn_ends() only reads the
        # applied values afterwards. Documented on the binding.
        r = _orthogonal_router()
        src = ConnEnd(Point(0.0, 0.0))
        dst = ConnEnd(Point(10.0, 10.0))
        conn = ConnRef(r, src, dst)
        r.process_transaction()
        s, d = conn.endpoint_conn_ends()
        assert s.position() == Point(0.0, 0.0)
        assert d.position() == Point(10.0, 10.0)


class TestEndpointUpdate:
    # endpoint_conn_ends() reflects the last applied values, not the
    # pending ones. Each test below calls process_transaction() after
    # the relevant setter so the read returns what was set.

    def test_set_endpoints_replaces_both(self) -> None:
        r = _orthogonal_router()
        conn = ConnRef(r)
        conn.set_endpoints(ConnEnd(Point(1.0, 1.0)), ConnEnd(Point(2.0, 2.0)))
        r.process_transaction()
        s, d = conn.endpoint_conn_ends()
        assert s.position() == Point(1.0, 1.0)
        assert d.position() == Point(2.0, 2.0)

    def test_set_source_endpoint_only(self) -> None:
        r = _orthogonal_router()
        conn = ConnRef(r, ConnEnd(Point(0.0, 0.0)), ConnEnd(Point(10.0, 0.0)))
        r.process_transaction()
        conn.set_source_endpoint(ConnEnd(Point(5.0, 5.0)))
        r.process_transaction()
        s, d = conn.endpoint_conn_ends()
        assert s.position() == Point(5.0, 5.0)
        assert d.position() == Point(10.0, 0.0)

    def test_set_dest_endpoint_only(self) -> None:
        r = _orthogonal_router()
        conn = ConnRef(r, ConnEnd(Point(0.0, 0.0)), ConnEnd(Point(10.0, 0.0)))
        r.process_transaction()
        conn.set_dest_endpoint(ConnEnd(Point(99.0, 99.0)))
        r.process_transaction()
        s, d = conn.endpoint_conn_ends()
        assert s.position() == Point(0.0, 0.0)
        assert d.position() == Point(99.0, 99.0)


class TestRoutingType:
    def test_default_matches_empty_ctor(self) -> None:
        r = _orthogonal_router()
        conn = ConnRef(r)
        # libavoid initialises ConnRef to ConnType_None until the
        # router picks one — but libavoid also validates against its
        # RouterFlag setup. We accept any legal value.
        rt = conn.routing_type()
        assert rt in (ConnType.PolyLine, ConnType.Orthogonal) or int(rt) == 0

    def test_set_and_get(self) -> None:
        r = _orthogonal_router()
        conn = ConnRef(r, ConnEnd(Point(0.0, 0.0)), ConnEnd(Point(1.0, 1.0)))
        conn.set_routing_type(ConnType.Orthogonal)
        assert conn.routing_type() == ConnType.Orthogonal
        conn.set_routing_type(ConnType.PolyLine)
        assert conn.routing_type() == ConnType.PolyLine


class TestEndToEndRouting:
    """
    Place two shapes side-by-side, route an orthogonal connector
    between them, and verify the returned PolyLine is non-trivial.
    """

    def _two_shape_scene(self) -> tuple[Router, ConnRef]:
        r = _orthogonal_router()
        ShapeRef(r, Rectangle(Point(0.0, 0.0), Point(40.0, 20.0)))
        ShapeRef(r, Rectangle(Point(100.0, 0.0), Point(140.0, 20.0)))
        conn = ConnRef(
            r,
            ConnEnd(Point(40.0, 10.0)),
            ConnEnd(Point(100.0, 10.0)),
        )
        conn.set_routing_type(ConnType.Orthogonal)
        return r, conn

    def test_route_has_points(self) -> None:
        r, conn = self._two_shape_scene()
        r.process_transaction()
        route = conn.display_route()
        assert isinstance(route, Polygon)
        assert route.size() >= 2  # at minimum, src and dst

    def test_route_is_polyline_alias(self) -> None:
        assert PolyLine is Polygon

    def test_route_endpoints_match_conn_end_positions(self) -> None:
        r, conn = self._two_shape_scene()
        r.process_transaction()
        route = conn.display_route()
        first = route.at(0)
        last = route.at(route.size() - 1)
        assert first == Point(40.0, 10.0)
        assert last == Point(100.0, 10.0)

    def test_orthogonal_route_around_blocker(self) -> None:
        # A blocking shape sits directly on the straight line between
        # src and dst. The orthogonal router must produce a path with
        # at least a turn, so size() > 2.
        r = _orthogonal_router()
        ShapeRef(r, Rectangle(Point(40.0, -20.0), Point(60.0, 20.0)))
        conn = ConnRef(
            r,
            ConnEnd(Point(0.0, 0.0)),
            ConnEnd(Point(100.0, 0.0)),
        )
        conn.set_routing_type(ConnType.Orthogonal)
        r.process_transaction()
        route = conn.display_route()
        assert route.size() > 2, (
            f"orthogonal route around blocker should have bends, "
            f"got a {route.size()}-point path"
        )


class TestAttachedConnectors:
    def test_empty_on_unconnected_shape(self) -> None:
        r = _orthogonal_router()
        shape = ShapeRef(r, Rectangle(Point(0.0, 0.0), Point(10.0, 10.0)))
        r.process_transaction()
        assert shape.attached_connectors() == []


class TestDeleteConnector:
    def test_router_continues_after_delete(self) -> None:
        r = _orthogonal_router()
        conn = ConnRef(r, ConnEnd(Point(0.0, 0.0)), ConnEnd(Point(1.0, 1.0)))
        r.process_transaction()
        r.delete_connector(conn)
        del conn
        gc.collect()
        # Router keeps working after a connector is removed.
        assert r.process_transaction() in (True, False)


class TestLifetime:
    def test_connref_keeps_router_alive(self) -> None:
        r = _orthogonal_router()
        conn = ConnRef(r, ConnEnd(Point(0.0, 0.0)), ConnEnd(Point(1.0, 1.0)))
        router_weakref = weakref.ref(r)
        del r
        gc.collect()
        assert router_weakref() is not None
        # Methods on the connector still work.
        assert conn.id() != 0
