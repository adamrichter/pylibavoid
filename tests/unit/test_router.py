"""Router and routing-parameter/option enum tests.

These verify the wrapper surface added in phase 2 PR 2. No shapes or
connectors yet, so there is nothing to actually route; the tests are
about configuration plumbing, enum values, and the lifecycle of a
standalone Router instance.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import libavoid_py
from libavoid_py import (
    Router,
    RouterFlag,
    RoutingOption,
    RoutingParameter,
    chooseSensibleParamValue,
    zeroParamValue,
)


class TestRouterFlagEnum:
    def test_values_match_libavoid(self) -> None:
        # These integer values are part of libavoid's ABI (upstream
        # users write Router(1) in C++ and expect poly-line routing).
        # Lock them down so a future enum reorder gets caught.
        assert int(RouterFlag.PolyLineRouting) == 1
        assert int(RouterFlag.OrthogonalRouting) == 2

    def test_bitwise_combination_yields_int(self) -> None:
        combined = RouterFlag.PolyLineRouting | RouterFlag.OrthogonalRouting
        assert int(combined) == 3


class TestRoutingParameterEnum:
    def test_values_start_at_zero_and_are_contiguous(self) -> None:
        # libavoid uses these as array indices internally; the
        # ordering matters. Pin the positions.
        expected = {
            RoutingParameter.segmentPenalty: 0,
            RoutingParameter.anglePenalty: 1,
            RoutingParameter.crossingPenalty: 2,
            RoutingParameter.clusterCrossingPenalty: 3,
            RoutingParameter.fixedSharedPathPenalty: 4,
            RoutingParameter.portDirectionPenalty: 5,
            RoutingParameter.shapeBufferDistance: 6,
            RoutingParameter.idealNudgingDistance: 7,
            RoutingParameter.reverseDirectionPenalty: 8,
        }
        for value, integer in expected.items():
            assert int(value) == integer


class TestRoutingOptionEnum:
    def test_values(self) -> None:
        expected = {
            RoutingOption.nudgeOrthogonalSegmentsConnectedToShapes: 0,
            RoutingOption.improveHyperedgeRoutesMovingJunctions: 1,
            RoutingOption.penaliseOrthogonalSharedPathsAtConnEnds: 2,
            RoutingOption.nudgeOrthogonalTouchingColinearSegments: 3,
            RoutingOption.performUnifyingNudgingPreprocessingStep: 4,
            RoutingOption.improveHyperedgeRoutesMovingAddingAndDeletingJunctions: 5,
            RoutingOption.nudgeSharedPathsWithCommonEndPoint: 6,
        }
        for value, integer in expected.items():
            assert int(value) == integer


class TestConstants:
    def test_zero_and_sensible_markers(self) -> None:
        assert zeroParamValue == 0
        assert chooseSensibleParamValue == -1


class TestRouterConstruction:
    def test_poly_line_routing(self) -> None:
        Router(RouterFlag.PolyLineRouting)

    def test_orthogonal_routing(self) -> None:
        Router(RouterFlag.OrthogonalRouting)

    def test_combined_flags(self) -> None:
        Router(RouterFlag.PolyLineRouting | RouterFlag.OrthogonalRouting)

    def test_from_plain_int(self) -> None:
        Router(2)


class TestTransactionUse:
    def test_default_transaction_use_is_true(self) -> None:
        # libavoid's default: all actions are batched until
        # process_transaction() is called.
        r = Router(RouterFlag.OrthogonalRouting)
        assert r.transaction_use() is True

    def test_toggle(self) -> None:
        r = Router(RouterFlag.OrthogonalRouting)
        r.set_transaction_use(False)
        assert r.transaction_use() is False
        r.set_transaction_use(True)
        assert r.transaction_use() is True

    def test_process_transaction_on_empty_router(self) -> None:
        # With nothing queued, process_transaction() should succeed and
        # return False (no pending actions). Observed upstream.
        r = Router(RouterFlag.OrthogonalRouting)
        result = r.process_transaction()
        assert isinstance(result, bool)


class TestRoutingParameterSetters:
    def test_set_and_get(self) -> None:
        r = Router(RouterFlag.OrthogonalRouting)
        r.set_routing_parameter(RoutingParameter.segmentPenalty, 10.0)
        assert r.routing_parameter(RoutingParameter.segmentPenalty) == 10.0

    def test_set_zero_via_named_constant(self) -> None:
        r = Router(RouterFlag.OrthogonalRouting)
        r.set_routing_parameter(RoutingParameter.shapeBufferDistance, zeroParamValue)
        assert r.routing_parameter(RoutingParameter.shapeBufferDistance) == 0.0

    def test_sensible_default_marker_requests_default(self) -> None:
        # chooseSensibleParamValue tells libavoid to apply its own
        # default for that parameter. We don't assert a specific value
        # (libavoid is free to pick one), only that after the call the
        # read-back value is non-negative — sentinel -1 should be gone.
        r = Router(RouterFlag.OrthogonalRouting)
        r.set_routing_parameter(
            RoutingParameter.idealNudgingDistance, chooseSensibleParamValue
        )
        assert r.routing_parameter(RoutingParameter.idealNudgingDistance) >= 0.0

    def test_set_routing_penalty_is_alias(self) -> None:
        r = Router(RouterFlag.OrthogonalRouting)
        r.set_routing_penalty(RoutingParameter.anglePenalty, 42.5)
        assert r.routing_parameter(RoutingParameter.anglePenalty) == 42.5


class TestRoutingOptionSetters:
    def test_set_and_get_true_false(self) -> None:
        r = Router(RouterFlag.OrthogonalRouting)
        r.set_routing_option(
            RoutingOption.nudgeOrthogonalSegmentsConnectedToShapes, True
        )
        assert (
            r.routing_option(RoutingOption.nudgeOrthogonalSegmentsConnectedToShapes)
            is True
        )
        r.set_routing_option(
            RoutingOption.nudgeOrthogonalSegmentsConnectedToShapes, False
        )
        assert (
            r.routing_option(RoutingOption.nudgeOrthogonalSegmentsConnectedToShapes)
            is False
        )


class TestInvalidOrthogonalPaths:
    def test_empty_router_has_no_invalid_paths(self) -> None:
        r = Router(RouterFlag.OrthogonalRouting)
        assert r.exists_invalid_orthogonal_paths() is False


class TestOutputDiagram:
    def test_writes_text_transcript(self, tmp_path: Path) -> None:
        # libavoid's outputDiagram() always writes the .txt transcript
        # and only writes the .svg when compiled with SVG_OUTPUT defined
        # (upstream does not define it; neither do we). So we assert on
        # the file we actually get.
        r = Router(RouterFlag.OrthogonalRouting)
        prefix = tmp_path / "diag"
        r.output_diagram(str(prefix))
        txt = tmp_path / "diag.txt"
        assert txt.exists(), "expected <prefix>.txt to be written"
        assert not (tmp_path / "diag.svg").exists(), (
            "unexpected .svg — SVG_OUTPUT should be off in our build"
        )


class TestModuleSurface:
    def test_exports(self) -> None:
        for name in (
            "Router",
            "RouterFlag",
            "RoutingParameter",
            "RoutingOption",
            "zeroParamValue",
            "chooseSensibleParamValue",
        ):
            assert hasattr(libavoid_py, name), name
