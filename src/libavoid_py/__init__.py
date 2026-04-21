"""libavoid-py — Python bindings for libavoid.

Phase 2 progressively exposes the routing surface. Phase 2 PR 1 adds
the geometry primitives (:class:`Point`, :class:`Box`, :class:`Polygon`,
:class:`Rectangle`, and the :data:`PolyLine` / :data:`Vector` aliases).
The :class:`Router`, :class:`ShapeRef`, and :class:`ConnRef` types land
in the PRs that follow.
"""

from ._core import (
    XDIM,
    YDIM,
    Box,
    Point,
    Polygon,
    PolyLine,
    Rectangle,
    Router,
    RouterFlag,
    RoutingOption,
    RoutingParameter,
    Vector,
    chooseSensibleParamValue,
    version,
    zeroParamValue,
)

__all__ = [
    "XDIM",
    "YDIM",
    "Box",
    "Point",
    "PolyLine",
    "Polygon",
    "Rectangle",
    "Router",
    "RouterFlag",
    "RoutingOption",
    "RoutingParameter",
    "Vector",
    "chooseSensibleParamValue",
    "version",
    "zeroParamValue",
]
