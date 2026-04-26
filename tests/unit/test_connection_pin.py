"""ShapeConnectionPin wrapper tests.

Phase 4 PR 2. Pins are owned by their parent shape (or junction),
not by the router directly; the binding mirrors that with
py::keep_alive on every constructor and the same nodelete holder
pattern as ShapeRef / ConnRef / JunctionRef. Also covers the new
ConnEnd(ShapeRef, class_id) overload and the shape() /
pin_class_id() accessors.
"""

from __future__ import annotations

import gc
import weakref

from libavoid_py import (
    ATTACH_POS_BOTTOM,
    ATTACH_POS_CENTRE,
    ATTACH_POS_LEFT,
    ATTACH_POS_RIGHT,
    ATTACH_POS_TOP,
    CONNECTIONPIN_CENTRE,
    CONNECTIONPIN_UNSET,
    ConnDirFlag,
    ConnEnd,
    ConnEndType,
    ConnRef,
    JunctionRef,
    Point,
    Rectangle,
    Router,
    RouterFlag,
    ShapeConnectionPin,
    ShapeRef,
)


def _make_router() -> Router:
    return Router(RouterFlag.OrthogonalRouting)


class TestConstants:
    def test_alias_pairs(self) -> None:
        assert ATTACH_POS_LEFT == ATTACH_POS_TOP == 0.0
        assert ATTACH_POS_RIGHT == ATTACH_POS_BOTTOM == 1.0
        assert ATTACH_POS_CENTRE == 0.5

    def test_pin_id_sentinels(self) -> None:
        # CONNECTIONPIN_CENTRE is INT_MAX - 1 and CONNECTIONPIN_UNSET
        # is INT_MAX; make sure the relationship is preserved across
        # the binding boundary.
        assert CONNECTIONPIN_UNSET == CONNECTIONPIN_CENTRE + 1


class TestConstruction:
    def _shape(self, r: Router) -> ShapeRef:
        return ShapeRef(r, Rectangle(Point(0.0, 0.0), Point(10.0, 10.0)))

    def test_proportional_centre_pin(self) -> None:
        r = _make_router()
        s = self._shape(r)
        pin = ShapeConnectionPin(
            s, 1, ATTACH_POS_CENTRE, ATTACH_POS_CENTRE,
            proportional=True, inside_offset=0.0,
            visibility_directions=ConnDirFlag.ConnDirNone,
        )
        assert pin.position() == Point(5.0, 5.0)

    def test_absolute_offset_pin(self) -> None:
        r = _make_router()
        s = self._shape(r)
        # Absolute offsets land at (xOff, yOff) relative to the
        # shape's lower-X / lower-Y border, i.e. (3, 7).
        pin = ShapeConnectionPin(
            s, 2, 3.0, 7.0,
            proportional=False, inside_offset=0.0,
            visibility_directions=ConnDirFlag.ConnDirNone,
        )
        assert pin.position() == Point(3.0, 7.0)

    def test_pin_on_junction(self) -> None:
        # JunctionRef already auto-creates four pins; this overload
        # adds an extra one for parity with the C++ API.
        r = _make_router()
        j = JunctionRef(r, Point(0.0, 0.0))
        pin = ShapeConnectionPin(j, 99)
        # Position of a junction pin tracks the junction itself.
        assert pin.position() == Point(0.0, 0.0)


class TestProperties:
    def _pin(self, dirs: ConnDirFlag) -> ShapeConnectionPin:
        r = _make_router()
        s = ShapeRef(r, Rectangle(Point(0, 0), Point(10, 10)))
        return ShapeConnectionPin(
            s, 1, ATTACH_POS_CENTRE, ATTACH_POS_CENTRE,
            proportional=True, inside_offset=0.0,
            visibility_directions=dirs,
        )

    def test_exclusive_round_trips(self) -> None:
        pin = self._pin(ConnDirFlag.ConnDirRight)
        # Pins with a specific direction default to exclusive.
        assert pin.exclusive is True
        pin.exclusive = False
        assert pin.exclusive is False

    def test_directions_returns_int_bitmask(self) -> None:
        pin = self._pin(ConnDirFlag.ConnDirLeft)
        d = pin.directions()
        assert isinstance(d, int)
        assert d & int(ConnDirFlag.ConnDirLeft)

    def test_ids_tuple(self) -> None:
        pin = self._pin(ConnDirFlag.ConnDirNone)
        ids = pin.ids()
        assert isinstance(ids, tuple)
        assert len(ids) == 2
        # Class id is the second element; we passed 1 above.
        assert ids[1] == 1


class TestConnEndShapePin:
    def _setup(self) -> tuple[Router, ShapeRef, ShapeRef]:
        r = _make_router()
        a = ShapeRef(r, Rectangle(Point(0, 0), Point(10, 10)))
        b = ShapeRef(r, Rectangle(Point(40, 20), Point(50, 30)))
        ShapeConnectionPin(
            a, 1, ATTACH_POS_CENTRE, ATTACH_POS_CENTRE,
            proportional=True, inside_offset=0.0,
            visibility_directions=ConnDirFlag.ConnDirNone,
        )
        ShapeConnectionPin(
            b, 1, ATTACH_POS_CENTRE, ATTACH_POS_CENTRE,
            proportional=True, inside_offset=0.0,
            visibility_directions=ConnDirFlag.ConnDirNone,
        )
        return r, a, b

    def test_connend_round_trip(self) -> None:
        _, a, _ = self._setup()
        ce = ConnEnd(a, 1)
        assert ce.type() == ConnEndType.ShapePin
        assert ce.shape() is a
        assert ce.pin_class_id() == 1

    def test_connend_with_centre_sentinel(self) -> None:
        r = _make_router()
        s = ShapeRef(r, Rectangle(Point(0, 0), Point(10, 10)))
        ShapeConnectionPin(
            s, CONNECTIONPIN_CENTRE,
            ATTACH_POS_CENTRE, ATTACH_POS_CENTRE,
            proportional=True, inside_offset=0.0,
            visibility_directions=ConnDirFlag.ConnDirNone,
        )
        ce = ConnEnd(s, CONNECTIONPIN_CENTRE)
        assert ce.pin_class_id() == CONNECTIONPIN_CENTRE

    def test_point_connend_has_no_shape(self) -> None:
        ce = ConnEnd(Point(5.0, 5.0))
        assert ce.shape() is None

    def test_connref_routes_through_pins(self) -> None:
        r, a, b = self._setup()
        c = ConnRef(r, ConnEnd(a, 1), ConnEnd(b, 1))
        r.process_transaction()
        route = c.display_route()
        # The exact route length is libavoid's choice; just confirm
        # we got an actual path back.
        assert route.size() >= 2


class TestLifetime:
    def test_dropping_python_pin_keeps_router_intact(self) -> None:
        r = _make_router()
        s = ShapeRef(r, Rectangle(Point(0, 0), Point(10, 10)))
        pin = ShapeConnectionPin(
            s, 1, ATTACH_POS_CENTRE, ATTACH_POS_CENTRE,
            proportional=True, inside_offset=0.0,
            visibility_directions=ConnDirFlag.ConnDirNone,
        )
        del pin
        gc.collect()
        # The pin is still inside the shape's pin set; processing
        # the router must not crash.
        r.process_transaction()

    def test_pin_keeps_shape_alive(self) -> None:
        r = _make_router()
        s = ShapeRef(r, Rectangle(Point(0, 0), Point(10, 10)))
        pin = ShapeConnectionPin(
            s, 1, ATTACH_POS_CENTRE, ATTACH_POS_CENTRE,
            proportional=True, inside_offset=0.0,
            visibility_directions=ConnDirFlag.ConnDirNone,
        )
        shape_weakref = weakref.ref(s)
        del s
        gc.collect()
        # keep_alive<1, 2> should hold the shape via the pin.
        assert shape_weakref() is not None
        assert pin.position() == Point(5.0, 5.0)
