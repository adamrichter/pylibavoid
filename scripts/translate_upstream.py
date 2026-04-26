"""Translate upstream libavoid C++ tests into Python equivalents.

The upstream tests under ``vendor/adaptagrams/cola/libavoid/tests/``
are written in a constrained subset of C++. This script parses each
``.cpp`` file and emits a Python test under ``tests/upstream/`` that
mirrors the scenario against the :mod:`libavoid_py` wrapper.

The translation strategy is documented in
``docs/decisions/0002-phase3-golden-strategy.md``. In short: each test
replays the scenario with ``Router.process_transaction()`` and carries
the same pass/fail signal the upstream test used (crash-only, one of
the ``exists*`` queries, or an inline assertion).

Running the script is idempotent: re-running it on a bumped libavoid
submodule commit regenerates the Python tests in place, and the diff
shows what upstream changed.

Usage::

    python scripts/translate_upstream.py            # regenerate all
    python scripts/translate_upstream.py inline     # one test
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_TESTS = (
    REPO_ROOT / "vendor" / "adaptagrams" / "cola" / "libavoid" / "tests"
)
OUTPUT_DIR = REPO_ROOT / "tests" / "upstream"

# Tests from docs/research/phase0.md that can run against the phase-2
# public API. Blocked tests live in TRANSLATABLE_PARTIAL below; they
# become skipped stubs.
TRANSLATABLE_TESTS: tuple[str, ...] = (
    "finalSegmentNudging1",
    "finalSegmentNudging2",
    "freeFloatingDirection01",
    "infinity",
    "inline",
    "inlineoverlap01",
    "inlineoverlap02",
    "inlineoverlap03",
    "inlineoverlap04",
    "inlineoverlap05",
    "inlineoverlap06",
    "inlineoverlap07",
    "inlineoverlap08",
    "inlineOverlap09",
    "junction02",
    "junction03",
    "lineSegWrapperCrash1",
    "lineSegWrapperCrash2",
    "lineSegWrapperCrash3",
    "lineSegWrapperCrash4",
    "lineSegWrapperCrash5",
    "lineSegWrapperCrash6",
    "lineSegWrapperCrash7",
    "lineSegWrapperCrash8",
    "nudgeintobug",
    "nudgeold",
    "orderassertion",
    "orthordering01",
    "orthordering02",
    "overlappingRects",
    "penaltyRerouting01",
    "performance01",
    "restrictedNudging",
    "slowrouting",
    "tjunct",
    "vertlineassertion",
)

# Tests that need phase-4 features. Keyed by test name, the value is
# the feature gap surfaced as the pytest.skip reason. Sourced from
# docs/research/phase0.md's per-test inventory.
TRANSLATABLE_PARTIAL: dict[str, str] = {
    "2junctions": "connection pins",
    "buildOrthogonalChannelInfo1": "connection pins",
    "checkpointNudging1": "checkpoints",
    "checkpointNudging2": "checkpoints",
    "checkpointNudging3": "checkpoints",
    "checkpoints01": "checkpoints",
    "checkpoints02": "checkpoints",
    "checkpoints03": "checkpoints",
    "complex": "callbacks",
    "connectionpin01": "connection pins",
    "connectionpin02": "connection pins",
    "connectionpin03": "connection pins",
    "connendmove": "connection pins",
    "endlessLoop01": "hyperedges",
    "example": "callbacks",
    "finalSegmentNudging3": "checkpoints",
    "forwardFlowingConnectors01": "connection pins",
    "hola01": "connection pins",
    "hyperedge01": "hyperedges",
    "hyperedge02": "hyperedges",
    "hyperedgeLoop1": "connection pins",
    "hyperedgeRerouting01": "hyperedges",
    "improveHyperedge01": "hyperedges",
    "improveHyperedge02": "hyperedges",
    "improveHyperedge03": "hyperedges",
    "improveHyperedge04": "hyperedges",
    "improveHyperedge05": "hyperedges",
    "improveHyperedge06": "hyperedges",
    "inlineOverlap10": "connection pins",
    "inlineOverlap11": "hyperedges",
    "inlineShapes": "connection pins",
    "junction01": "connection pins",
    "junction04": "connection pins",
    "latesetup": "callbacks",
    "multiconnact": "callbacks",
    "node1": "connection pins",
    "nudgeCrossing01": "checkpoints",
    "nudgingSkipsCheckpoint01": "checkpoints",
    "nudgingSkipsCheckpoint02": "checkpoints",
    "removeJunctions01": "connection pins",
    "treeRootCrash01": "hyperedges",
    "treeRootCrash02": "hyperedges",
    "validPaths01": "connection pins",
    "validPaths02": "connection pins",
}

# Tests upstream disabled in Makefile.am; we mirror the decision.
DISABLED_UPSTREAM: tuple[str, ...] = (
    "corneroverlap01",
    "reallyslowrouting",
    "unsatisfiableRangeAssertion",
)

# Names in libavoid's RoutingParameter/Avoid namespace, in value order.
ROUTING_PARAMETERS = [
    "segmentPenalty",
    "anglePenalty",
    "crossingPenalty",
    "clusterCrossingPenalty",
    "fixedSharedPathPenalty",
    "portDirectionPenalty",
    "shapeBufferDistance",
    "idealNudgingDistance",
    "reverseDirectionPenalty",
]
ROUTING_OPTIONS = [
    "nudgeOrthogonalSegmentsConnectedToShapes",
    "improveHyperedgeRoutesMovingJunctions",
    "penaliseOrthogonalSharedPathsAtConnEnds",
    "nudgeOrthogonalTouchingColinearSegments",
    "performUnifyingNudgingPreprocessingStep",
    "improveHyperedgeRoutesMovingAddingAndDeletingJunctions",
    "nudgeSharedPathsWithCommonEndPoint",
]
ROUTER_FLAGS = {
    "PolyLineRouting": "RouterFlag.PolyLineRouting",
    "OrthogonalRouting": "RouterFlag.OrthogonalRouting",
}
CONN_DIR_FLAGS = {
    "ConnDirNone": "ConnDirFlag.ConnDirNone",
    "ConnDirUp": "ConnDirFlag.ConnDirUp",
    "ConnDirDown": "ConnDirFlag.ConnDirDown",
    "ConnDirLeft": "ConnDirFlag.ConnDirLeft",
    "ConnDirRight": "ConnDirFlag.ConnDirRight",
    "ConnDirAll": "ConnDirFlag.ConnDirAll",
}


# ---------------------------------------------------------------------------
# C++ → statement stream
# ---------------------------------------------------------------------------


def strip_comments(src: str) -> str:
    # block comments first so they do not contaminate line-comment detection.
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"//[^\n]*", "", src)
    return src


_MAIN_RE = re.compile(
    r"int\s+main\s*\([^)]*\)\s*\{(?P<body>.*)\}\s*;?\s*\Z", re.DOTALL
)


def extract_main_body(src: str) -> str:
    src = strip_comments(src)
    # drop #include, using, and the "using namespace Avoid;" line.
    src = re.sub(r"^\s*#.*$", "", src, flags=re.MULTILINE)
    src = re.sub(r"^\s*using\s+[^;]+;\s*$", "", src, flags=re.MULTILINE)

    # Find `int main(...)` and extract the balanced brace block manually
    # (a regex cannot balance braces reliably).
    m = re.search(r"int\s+main\s*\([^)]*\)\s*\{", src)
    if m is None:
        raise ValueError("no main() found")
    start = m.end()
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise ValueError("unbalanced braces in main()")
    return src[start : i - 1]


def split_statements(body: str) -> list[str]:
    """Split a C++ function body into semicolon-terminated statements."""
    out: list[str] = []
    buf: list[str] = []
    depth = 0
    paren = 0
    for c in body:
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "(":
            paren += 1
        elif c == ")":
            paren -= 1
        elif c == ";" and depth == 0 and paren == 0:
            s = "".join(buf).strip()
            if s:
                out.append(" ".join(s.split()))
            buf = []
            continue
        buf.append(c)
    tail = "".join(buf).strip()
    if tail:
        out.append(" ".join(tail.split()))
    return out


# ---------------------------------------------------------------------------
# Expression translation
# ---------------------------------------------------------------------------


def translate_expression(expr: str) -> str:
    """Translate a C++ expression fragment to Python.

    Only the patterns that appear in the upstream tests are handled:
    ``Avoid::X`` prefixes, named routing parameter / option / direction
    constants, ``true``/``false``, ``Point(x, y)``, and integer/double
    literals with the usual arithmetic.
    """
    # drop Avoid:: prefix
    expr = re.sub(r"\bAvoid::", "", expr)
    expr = re.sub(r"\btrue\b", "True", expr)
    expr = re.sub(r"\bfalse\b", "False", expr)
    # Substitute bare names before the cast-by-value forms so we don't
    # end up with ``RoutingParameter.RoutingParameter.segmentPenalty``
    # (the cast-by-value emits the full enum member name, which would
    # otherwise get re-prefixed by the bare-name loop below). The
    # negative-lookbehind ``(?<![.])`` guards against substituting a
    # bare identifier that already sits on a dotted access path.
    for name in ROUTING_PARAMETERS:
        expr = re.sub(
            rf"(?<![.\w]){name}\b", f"RoutingParameter.{name}", expr
        )
    for name in ROUTING_OPTIONS:
        expr = re.sub(
            rf"(?<![.\w]){name}\b", f"RoutingOption.{name}", expr
        )
    for name, replacement in ROUTER_FLAGS.items():
        expr = re.sub(rf"(?<![.\w]){name}\b", replacement, expr)
    for name, replacement in CONN_DIR_FLAGS.items():
        expr = re.sub(rf"(?<![.\w]){name}\b", replacement, expr)
    # ``(PenaltyType)N`` (and the RoutingParameter / RoutingOption /
    # ConnType equivalents) keep the cast's numeric value; the helper
    # maps it to the named enum member. These run last so the
    # substitutions above do not hit the emitted enum names.
    expr = re.sub(r"\(\s*PenaltyType\s*\)\s*(\d+)", _param_by_value, expr)
    expr = re.sub(r"\(\s*RoutingParameter\s*\)\s*(\d+)", _param_by_value, expr)
    expr = re.sub(r"\(\s*RoutingOption\s*\)\s*(\d+)", _option_by_value, expr)
    expr = re.sub(r"\(\s*ConnType\s*\)\s*(\d+)", _conntype_by_value, expr)
    # collapse multiple spaces
    expr = " ".join(expr.split())
    return expr


def _param_by_value(m: re.Match[str]) -> str:
    idx = int(m.group(1))
    if 0 <= idx < len(ROUTING_PARAMETERS):
        return f"RoutingParameter.{ROUTING_PARAMETERS[idx]}"
    return m.group(0)


def _conntype_by_value(m: re.Match[str]) -> str:
    idx = int(m.group(1))
    mapping = {1: "PolyLine", 2: "Orthogonal"}
    if idx in mapping:
        return f"ConnType.{mapping[idx]}"
    return m.group(0)


def _option_by_value(m: re.Match[str]) -> str:
    idx = int(m.group(1))
    if 0 <= idx < len(ROUTING_OPTIONS):
        return f"RoutingOption.{ROUTING_OPTIONS[idx]}"
    return m.group(0)


# ---------------------------------------------------------------------------
# Statement classifier
# ---------------------------------------------------------------------------


@dataclass
class TestIR:
    name: str
    router_flags: str = ""
    body_lines: list[str] = field(default_factory=list)
    assertions: list[str] = field(default_factory=list)
    bool_vars: dict[str, str] = field(default_factory=dict)
    int_vars: dict[str, str] = field(default_factory=dict)
    connend_decls: set[str] = field(default_factory=set)
    connref_decls: set[str] = field(default_factory=set)
    shape_decls: set[str] = field(default_factory=set)
    polygon_decls: set[str] = field(default_factory=set)

    def emit(self, line: str) -> None:
        self.body_lines.append(line)


def _pyname(cname: str) -> str:
    """Upstream variable names (``connRef100850179``) are legal Python.

    Return ``snake_case`` where it reads more naturally for the reader
    (``srcPt`` → ``src_pt``) while preserving suffixes intact so that
    variables that share an origin keep the same suffix.
    """
    # Convert camelCase to snake_case.
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", cname).lower()
    return s


def classify(ir: TestIR, stmt: str) -> None:
    # Router *router = new Router(FLAGS);  or  Avoid::Router *router = ...
    m = re.match(
        r"(?:Avoid::)?Router\s*\*\s*router\s*=\s*new\s+(?:Avoid::)?Router\s*\((?P<flags>.*)\)",
        stmt,
    )
    if m:
        flags = translate_expression(m.group("flags").strip())
        ir.router_flags = flags
        ir.emit(f"router = Router({flags})")
        return

    # router->setRoutingPenalty(...);
    m = re.match(r"router->setRoutingPenalty\s*\((?P<args>.*)\)", stmt)
    if m:
        args = translate_expression(m.group("args"))
        ir.emit(f"router.set_routing_penalty({args})")
        return
    m = re.match(r"router->setRoutingParameter\s*\((?P<args>.*)\)", stmt)
    if m:
        args = translate_expression(m.group("args"))
        ir.emit(f"router.set_routing_parameter({args})")
        return
    m = re.match(r"router->setRoutingOption\s*\((?P<args>.*)\)", stmt)
    if m:
        args = translate_expression(m.group("args"))
        ir.emit(f"router.set_routing_option({args})")
        return

    # Polygon polyN(count);  / Polygon polyN;  (default-constructed)
    # PolyLine newRoute;  — PolyLine is a typedef for Polygon; treat the
    # same so the body reads like a mechanical mirror of upstream.
    m = re.match(
        r"(?:Avoid::)?(?:Polygon|PolyLine)\s+(?P<name>\w+)(?:\s*\((?P<args>[^)]*)\))?$",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        args = m.group("args")
        if args is not None:
            args = translate_expression(args)
            ir.emit(f"{name} = Polygon({args})")
        else:
            ir.emit(f"{name} = Polygon()")
        ir.polygon_decls.add(name)
        return

    # polygon = Polygon(N);   / polygon = PolyLine(N);  (reassignment)
    m = re.match(
        r"(?P<name>\w+)\s*=\s*(?:Avoid::)?(?:Polygon|PolyLine)\s*\((?P<args>[^)]*)\)$",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        args = translate_expression(m.group("args"))
        ir.emit(f"{name} = Polygon({args})")
        return

    # polyN.ps.resize(N);  -- the ps setter replaces the list; building
    # a fresh list of zero Points gives the same size-N starting state
    # that C++ resize() does.
    m = re.match(r"(?P<name>\w+)\.ps\.resize\s*\(\s*(?P<n>\d+)\s*\)$", stmt)
    if m:
        name = _pyname(m.group("name"))
        n = m.group("n")
        ir.emit(
            f"{name}.ps = [Point(0.0, 0.0) for _ in range({n})]"
        )
        return

    # polyN._id = N;   -- expose as the Python `id` attribute.
    m = re.match(r"(?P<name>\w+)\._id\s*=\s*(?P<v>[^$]+)$", stmt)
    if m:
        name = _pyname(m.group("name"))
        v = translate_expression(m.group("v").strip())
        ir.emit(f"{name}.id = {v}")
        return

    # polyN.ps[i] = Point(x, y);
    m = re.match(
        r"(?P<name>\w+)\.ps\s*\[\s*(?P<idx>\d+)\s*\]\s*=\s*(?:Avoid::)?Point\s*\((?P<pt>[^)]*)\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        idx = m.group("idx")
        pt = translate_expression(m.group("pt"))
        ir.emit(f"{name}.set_point({idx}, Point({pt}))")
        return

    # Rectangle rectN(Point(a,b), Point(c,d));
    m = re.match(
        r"(?:Avoid::)?Rectangle\s+(?P<name>\w+)\s*\(\s*(?:Avoid::)?Point\s*\((?P<p1>[^)]*)\)\s*,\s*(?:Avoid::)?Point\s*\((?P<p2>[^)]*)\)\s*\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        p1 = translate_expression(m.group("p1"))
        p2 = translate_expression(m.group("p2"))
        ir.polygon_decls.add(name)
        ir.emit(f"{name} = Rectangle(Point({p1}), Point({p2}))")
        return

    # Rectangle rectN(Point(cx,cy), w, h);
    m = re.match(
        r"(?:Avoid::)?Rectangle\s+(?P<name>\w+)\s*\(\s*(?:Avoid::)?Point\s*\((?P<p>[^)]*)\)\s*,\s*(?P<w>[^,]+),\s*(?P<h>[^)]+)\s*\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        p = translate_expression(m.group("p"))
        w = translate_expression(m.group("w").strip())
        h = translate_expression(m.group("h").strip())
        ir.polygon_decls.add(name)
        ir.emit(f"{name} = Rectangle(Point({p}), {w}, {h})")
        return

    # new ShapeRef(router, polyN, id);
    m = re.match(
        r"new\s+(?:Avoid::)?ShapeRef\s*\(\s*router\s*,\s*(?P<poly>\w+)\s*(?:,\s*(?P<id>[^)]+))?\s*\)",
        stmt,
    )
    if m:
        poly = _pyname(m.group("poly"))
        id_ = m.group("id")
        if id_ is not None:
            ir.emit(f"ShapeRef(router, {poly}, {id_.strip()})")
        else:
            ir.emit(f"ShapeRef(router, {poly})")
        return

    # ConnEnd name;   (default-constructed placeholder)
    m = re.match(r"(?:Avoid::)?ConnEnd\s+(?P<name>\w+)$", stmt)
    if m:
        name = _pyname(m.group("name"))
        ir.connend_decls.add(name)
        ir.emit(f"{name} = ConnEnd()")
        return

    # ConnEnd name(Point(x,y));
    # ConnEnd name(Point(x,y), flags);
    m = re.match(
        r"(?:Avoid::)?ConnEnd\s+(?P<name>\w+)\s*\(\s*(?:Avoid::)?Point\s*\((?P<pt>[^)]*)\)\s*(?:,\s*(?P<flags>[^)]+))?\s*\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        pt = translate_expression(m.group("pt"))
        flags = m.group("flags")
        ir.connend_decls.add(name)
        if flags is not None:
            flags = translate_expression(flags.strip())
            ir.emit(f"{name} = ConnEnd(Point({pt}), {flags})")
        else:
            ir.emit(f"{name} = ConnEnd(Point({pt}))")
        return

    # ConnEnd name(junctionVar);   -- single-arg ctor whose argument is
    # a bare identifier (a JunctionRef variable). Must come AFTER the
    # Point-constructor pattern above, otherwise that pattern would
    # leave nothing to disambiguate.
    m = re.match(
        r"(?:Avoid::)?ConnEnd\s+(?P<name>\w+)\s*\(\s*(?P<jname>\w+)\s*\)$",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        jname = _pyname(m.group("jname"))
        ir.connend_decls.add(name)
        ir.emit(f"{name} = ConnEnd({jname})")
        return

    # ConnRef *name = nullptr;  -- a forward declaration; the real
    # assignment comes later. Emit None so the Python scope sees the
    # binding as well.
    m = re.match(
        r"(?:Avoid::)?ConnRef\s*\*\s*(?P<name>\w+)\s*=\s*nullptr$", stmt
    )
    if m:
        name = _pyname(m.group("name"))
        ir.connref_decls.add(name)
        ir.emit(f"{name} = None")
        return

    # ConnRef *crN = new ConnRef(router, id);
    m = re.match(
        r"(?:Avoid::)?ConnRef\s*\*\s*(?P<name>\w+)\s*=\s*new\s+(?:Avoid::)?ConnRef\s*\(\s*router\s*(?:,\s*(?P<id>[^)]+))?\s*\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        id_ = m.group("id")
        ir.connref_decls.add(name)
        if id_ is not None:
            ir.emit(f"{name} = ConnRef(router, {id_.strip()})")
        else:
            ir.emit(f"{name} = ConnRef(router)")
        return

    # connRef = new ConnRef(router, id);  (reassignment without declaration)
    m = re.match(
        r"(?P<name>\w+)\s*=\s*new\s+(?:Avoid::)?ConnRef\s*\(\s*router\s*(?:,\s*(?P<id>[^)]+))?\s*\)$",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        id_ = m.group("id")
        if id_ is not None:
            ir.emit(f"{name} = ConnRef(router, {id_.strip()})")
        else:
            ir.emit(f"{name} = ConnRef(router)")
        return

    # new ConnRef(router, src, dst[, id]);
    m = re.match(
        r"new\s+(?:Avoid::)?ConnRef\s*\(\s*router\s*,\s*(?P<src>\w+)\s*,\s*(?P<dst>\w+)\s*(?:,\s*(?P<id>[^)]+))?\s*\)",
        stmt,
    )
    if m:
        src = _pyname(m.group("src"))
        dst = _pyname(m.group("dst"))
        id_ = m.group("id")
        if id_ is not None:
            ir.emit(f"ConnRef(router, {src}, {dst}, {id_.strip()})")
        else:
            ir.emit(f"ConnRef(router, {src}, {dst})")
        return

    # crN->setSourceEndpoint / setDestEndpoint / setEndpoints / setRoutingType
    m = re.match(
        r"(?P<name>\w+)->setSourceEndpoint\s*\(\s*(?P<arg>\w+)\s*\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        arg = _pyname(m.group("arg"))
        ir.emit(f"{name}.set_source_endpoint({arg})")
        return
    m = re.match(
        r"(?P<name>\w+)->setDestEndpoint\s*\(\s*(?P<arg>\w+)\s*\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        arg = _pyname(m.group("arg"))
        ir.emit(f"{name}.set_dest_endpoint({arg})")
        return
    m = re.match(
        r"(?P<name>\w+)->setEndpoints\s*\(\s*(?P<src>\w+)\s*,\s*(?P<dst>\w+)\s*\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        src = _pyname(m.group("src"))
        dst = _pyname(m.group("dst"))
        ir.emit(f"{name}.set_endpoints({src}, {dst})")
        return
    m = re.match(
        r"(?P<name>\w+)->setRoutingType\s*\(\s*(?P<arg>.+?)\s*\)\s*$",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        arg = translate_expression(m.group("arg"))
        ir.emit(f"{name}.set_routing_type({arg})")
        return

    # crN->setFixedRoute(route);
    m = re.match(
        r"(?P<name>\w+)->setFixedRoute\s*\(\s*(?P<arg>\w+)\s*\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        arg = _pyname(m.group("arg"))
        ir.emit(f"{name}.set_fixed_route({arg})")
        return

    # dstPt = Avoid::ConnEnd(Point(x,y), flags);  (reassignment)
    m = re.match(
        r"(?P<name>\w+)\s*=\s*(?:Avoid::)?ConnEnd\s*\(\s*(?:Avoid::)?Point\s*\((?P<pt>[^)]*)\)\s*(?:,\s*(?P<flags>[^)]+))?\s*\)$",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        pt = translate_expression(m.group("pt"))
        flags = m.group("flags")
        if flags is not None:
            flags = translate_expression(flags.strip())
            ir.emit(f"{name} = ConnEnd(Point({pt}), {flags})")
        else:
            ir.emit(f"{name} = ConnEnd(Point({pt}))")
        return

    # dstPt = Avoid::ConnEnd(junctionVar);  (junction-form reassignment)
    m = re.match(
        r"(?P<name>\w+)\s*=\s*(?:Avoid::)?ConnEnd\s*\(\s*(?P<jname>\w+)\s*\)$",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        jname = _pyname(m.group("jname"))
        ir.emit(f"{name} = ConnEnd({jname})")
        return

    # JunctionRef *jr = new JunctionRef(router, Point(x, y) [, id]);
    m = re.match(
        r"(?:Avoid::)?JunctionRef\s*\*\s*(?P<name>\w+)\s*=\s*new\s+(?:Avoid::)?JunctionRef\s*\(\s*router\s*,\s*(?:Avoid::)?Point\s*\((?P<pt>[^)]*)\)\s*(?:,\s*(?P<id>[^)]+))?\s*\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        pt = translate_expression(m.group("pt"))
        id_ = m.group("id")
        if id_ is not None:
            ir.emit(f"{name} = JunctionRef(router, Point({pt}), {id_.strip()})")
        else:
            ir.emit(f"{name} = JunctionRef(router, Point({pt}))")
        return

    # router->moveJunction(jr, Point(x, y));
    m = re.match(
        r"router->moveJunction\s*\(\s*(?P<name>\w+)\s*,\s*(?:Avoid::)?Point\s*\((?P<pt>[^)]*)\)\s*\)$",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        pt = translate_expression(m.group("pt"))
        ir.emit(f"router.move_junction({name}, Point({pt}))")
        return

    # router->moveJunction(jr, dx, dy);
    m = re.match(
        r"router->moveJunction\s*\(\s*(?P<name>\w+)\s*,\s*(?P<dx>[^,]+)\s*,\s*(?P<dy>[^)]+)\s*\)$",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        dx = translate_expression(m.group("dx").strip())
        dy = translate_expression(m.group("dy").strip())
        ir.emit(f"router.move_junction({name}, {dx}, {dy})")
        return

    # router->deleteJunction(jr);
    m = re.match(r"router->deleteJunction\s*\(\s*(?P<name>\w+)\s*\)$", stmt)
    if m:
        name = _pyname(m.group("name"))
        ir.emit(f"router.delete_junction({name})")
        return

    # router->processTransaction();
    if re.match(r"router->processTransaction\s*\(\s*\)$", stmt):
        ir.emit("router.process_transaction()")
        return

    # router->outputDiagram("name");  — we drop output in the Python
    # translation since there is no golden-file comparison; keeping the
    # call would just scatter artefacts across the working directory.
    if re.match(r"router->outputDiagram\s*\(", stmt):
        return

    # bool x = true|false;   int x = literal;
    m = re.match(r"bool\s+(?P<name>\w+)\s*=\s*(?P<val>true|false)$", stmt)
    if m:
        name = _pyname(m.group("name"))
        val = "True" if m.group("val") == "true" else "False"
        ir.bool_vars[name] = val
        ir.emit(f"{name} = {val}")
        return

    # bool overlap = router->existsX(args);
    m = re.match(
        r"bool\s+(?P<name>\w+)\s*=\s*router->(?P<meth>exists\w+)\s*\((?P<args>.*)\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        method = _cpp_to_python_method(m.group("meth"))
        args = translate_expression(m.group("args"))
        # Substitute known bool vars captured above.
        args = _apply_local_bindings(args, ir.bool_vars)
        args = args.strip()
        if args:
            ir.emit(f"{name} = router.{method}({args})")
        else:
            ir.emit(f"{name} = router.{method}()")
        ir.bool_vars[name] = ""  # mark declared; actual value at runtime
        return

    # int crossings = router->existsCrossings(args);
    m = re.match(
        r"int\s+(?P<name>\w+)\s*=\s*router->(?P<meth>exists\w+)\s*\((?P<args>.*)\)",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        method = _cpp_to_python_method(m.group("meth"))
        args = translate_expression(m.group("args"))
        args = _apply_local_bindings(args, ir.bool_vars)
        args = args.strip()
        if args:
            ir.emit(f"{name} = router.{method}({args})")
        else:
            ir.emit(f"{name} = router.{method}()")
        ir.int_vars[name] = ""
        return

    # delete router;  -- we leave lifetime to Python GC; no-op.
    if re.match(r"delete\s+router$", stmt):
        return

    # return 0;  -- the C++ canonical "no crash".
    if re.match(r"return\s+0$", stmt):
        return

    # return (<bool>) ? 1 : 0;
    m = re.match(r"return\s*\(\s*(?P<expr>.+?)\s*\)\s*\?\s*1\s*:\s*0$", stmt)
    if m:
        expr = m.group("expr")
        # If the condition is "crossings > 0", flatten to
        # `assert crossings == 0` for clearer pytest output.
        cross = re.match(r"(?P<name>\w+)\s*>\s*0$", expr)
        if cross is not None:
            ir.assertions.append(
                f"assert {_pyname(cross.group('name'))} == 0"
            )
            return
        # "overlap || touching" → assert not (overlap or touching)
        py_expr = expr.replace("||", "or").replace("&&", "and")
        py_expr = re.sub(r"\s+", " ", py_expr).strip()
        py_expr = _apply_name_translation(py_expr)
        ir.assertions.append(f"assert not ({py_expr})")
        return

    # assert(connRef239->displayRoute().size() == 4);
    m = re.match(
        r"assert\s*\(\s*(?P<name>\w+)->displayRoute\s*\(\s*\)\s*\.\s*size\s*\(\s*\)\s*(?P<op>==|<=|>=|<|>|!=)\s*(?P<n>\d+)\s*\)$",
        stmt,
    )
    if m:
        name = _pyname(m.group("name"))
        op = m.group("op")
        n = m.group("n")
        ir.assertions.append(
            f"assert len({name}.display_route()) {op} {n}"
        )
        return

    raise ValueError(f"unrecognised statement: {stmt!r}")


def _cpp_to_python_method(cpp: str) -> str:
    """camelCase method name → snake_case."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", cpp).lower()


def _apply_name_translation(expr: str) -> str:
    """Rename identifiers inside an arithmetic/bool expression.

    Variables declared in the C++ body use camelCase; the Python
    translation uses snake_case. We substitute any bare identifier
    following ``_pyname`` so the final expression compiles.
    """

    def repl(m: re.Match[str]) -> str:
        tok = m.group(0)
        if tok in ("or", "and", "not", "True", "False"):
            return tok
        return _pyname(tok)

    return re.sub(r"\b[A-Za-z_][A-Za-z_0-9]*\b", repl, expr)


_RESERVED = frozenset(
    {"or", "and", "not", "True", "False", "None"}
)


def _apply_local_bindings(expr: str, bindings: dict[str, str]) -> str:
    """Rewrite bare camelCase identifiers so they line up with the
    snake_case names emitted by the translator.

    The translator stores locals under their Python-style name
    (``at_ends``); a C++ call site references the original camelCase
    name (``atEnds``). Snake-case every bare word that is not already
    a known Python keyword / bool literal / dotted enum member.
    """

    def repl(m: re.Match[str]) -> str:
        token = m.group(0)
        if token in _RESERVED:
            return token
        return _pyname(token)

    # Skip tokens that sit on a dotted path (e.g. ``RoutingOption.foo``),
    # those are already the final emitted form.
    return re.sub(r"(?<![.\w])[A-Za-z_][A-Za-z_0-9]*(?![\w.])", repl, expr)


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------


FILE_HEADER = '''\
"""Translation of upstream ``cola/libavoid/tests/{cpp_name}``.

Auto-generated by ``scripts/translate_upstream.py`` from
``vendor/adaptagrams/cola/libavoid/tests/{cpp_name}`` at the commit
pinned by ``vendor/adaptagrams``. Regenerate rather than hand-edit.

Pass/fail signal mirrors upstream: {pass_fail}.
"""

from libavoid_py import (
    ConnDirFlag,
    ConnEnd,
    ConnRef,
    ConnType,
    JunctionRef,
    Point,
    Polygon,
    Rectangle,
    Router,
    RouterFlag,
    RoutingOption,
    RoutingParameter,
    ShapeRef,
)


def test_{pytest_name}() -> None:
'''


SKIP_TEMPLATE = '''\
"""Upstream ``cola/libavoid/tests/{cpp_name}``.

Phase 0's inventory flagged this test as needing {missing_feature};
that is a phase-4 feature per ``CLAUDE.md`` §5. The stub records the
translation target so later phases can unskip it by porting the body.
"""

import pytest

pytest.skip(
    "libavoid_py does not yet wrap {missing_feature}; "
    "tracked in docs/api-coverage.md.",
    allow_module_level=True,
)
'''


def emit_test(ir: TestIR, cpp_name: str, pass_fail: str) -> str:
    pytest_name = _safe_pytest_name(ir.name)
    lines = [FILE_HEADER.format(
        cpp_name=cpp_name,
        pass_fail=pass_fail,
        pytest_name=pytest_name,
    )]
    for body in ir.body_lines:
        lines.append("    " + body)
    if ir.assertions:
        lines.append("")
        for a in ir.assertions:
            lines.append("    " + a)
    else:
        # Every test has an implicit "router processed without crashing"
        # assertion; pytest will fail on any exception from the body.
        pass
    text = "\n".join(lines).rstrip() + "\n"
    return text


def _safe_pytest_name(name: str) -> str:
    # pytest test function names are identifiers. Upstream names like
    # `inlineOverlap09` start with a lowercase letter already, so they
    # are already valid; we just snake-case them for consistency.
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _describe_pass_fail(stmts: list[str]) -> str:
    """Inspect the raw statements to describe what the test checks."""
    for s in stmts:
        if "existsOrthogonalFixedSegmentOverlap" in s:
            return "exists_orthogonal_fixed_segment_overlap() must be False"
        if "existsOrthogonalTouchingPaths" in s:
            return "exists_orthogonal_touching_paths() must be False"
        if "existsCrossings" in s:
            return "exists_crossings() must be 0"
        if "displayRoute" in s:
            return "inline assert on display_route().size()"
    return "process_transaction() must complete without raising"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def translate_file(cpp_path: Path, out_path: Path) -> None:
    src = cpp_path.read_text()
    body = extract_main_body(src)
    stmts = split_statements(body)
    ir = TestIR(name=cpp_path.stem)
    for stmt in stmts:
        classify(ir, stmt)
    pass_fail = _describe_pass_fail(stmts)
    text = emit_test(ir, cpp_path.name, pass_fail)
    out_path.write_text(text)


def write_skip_stub(name: str, missing_feature: str) -> None:
    out = OUTPUT_DIR / f"test_{_safe_pytest_name(name)}.py"
    out.write_text(
        SKIP_TEMPLATE.format(
            cpp_name=f"{name}.cpp",
            missing_feature=missing_feature,
        )
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "only",
        nargs="?",
        help="Translate just this one test (without .cpp).",
    )
    args = ap.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    init_file = OUTPUT_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    targets = TRANSLATABLE_TESTS
    if args.only:
        targets = (args.only,)
    for name in targets:
        cpp = UPSTREAM_TESTS / f"{name}.cpp"
        if not cpp.exists():
            print(f"! missing upstream source: {cpp}", file=sys.stderr)
            continue
        out = OUTPUT_DIR / f"test_{_safe_pytest_name(name)}.py"
        try:
            translate_file(cpp, out)
        except Exception as exc:
            print(f"! failed to translate {name}: {exc}", file=sys.stderr)
            raise
        print(f"  wrote {out.relative_to(REPO_ROOT)}")

    if not args.only:
        for name, feature in TRANSLATABLE_PARTIAL.items():
            write_skip_stub(name, feature)
            print(
                f"  wrote skip stub tests/upstream/"
                f"test_{_safe_pytest_name(name)}.py  "
                f"(needs {feature})"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
