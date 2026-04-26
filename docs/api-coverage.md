# API coverage

A running tally of what libavoid-py wraps from the upstream public
API, plus the translation status of each upstream regression test.
Companion to `docs/research/phase0.md` (inventory) and
`docs/research/api-surface.md` (what exists upstream).

## Public wrapper surface

| Header | C++ symbol | Python symbol | Phase landed | Notes |
|--------|------------|---------------|--------------|-------|
| `geomtypes.h` | `Point` | `libavoid_py.Point` | phase 2 | |
| `geomtypes.h` | `Vector` (typedef) | `libavoid_py.Vector` | phase 2 | Python alias of `Point`. |
| `geomtypes.h` | `Box` | `libavoid_py.Box` | phase 2 | |
| `geomtypes.h` | `Polygon` | `libavoid_py.Polygon` | phase 2 | |
| `geomtypes.h` | `PolyLine` (typedef) | `libavoid_py.PolyLine` | phase 2 | Python alias of `Polygon`. |
| `geomtypes.h` | `Rectangle` | `libavoid_py.Rectangle` | phase 2 | Subclass of `Polygon`. |
| `geomtypes.h` | `XDIM`, `YDIM` | `libavoid_py.XDIM`, `YDIM` | phase 2 | |
| `router.h` | `RouterFlag` | `libavoid_py.RouterFlag` | phase 2 | IntEnum with arithmetic. |
| `router.h` | `RoutingParameter` (+ `PenaltyType` alias) | `libavoid_py.RoutingParameter` | phase 2 | The `PenaltyType` alias is not re-exported. |
| `router.h` | `RoutingOption` | `libavoid_py.RoutingOption` | phase 2 | |
| `router.h` | `zeroParamValue`, `chooseSensibleParamValue` | `libavoid_py.zeroParamValue`, `chooseSensibleParamValue` | phase 2 | |
| `router.h` | `Router` | `libavoid_py.Router` | phase 2 | Owns shapes and connectors; see below for the method surface. |
| `router.h` | `Router::existsInvalidOrthogonalPaths` | `Router.exists_invalid_orthogonal_paths` | phase 2 | |
| `router.h` | `Router::existsOrthogonalSegmentOverlap` | `Router.exists_orthogonal_segment_overlap` | phase 3 | Added while translating upstream tests. |
| `router.h` | `Router::existsOrthogonalFixedSegmentOverlap` | `Router.exists_orthogonal_fixed_segment_overlap` | phase 3 | |
| `router.h` | `Router::existsOrthogonalTouchingPaths` | `Router.exists_orthogonal_touching_paths` | phase 3 | |
| `router.h` | `Router::existsCrossings` | `Router.exists_crossings` | phase 3 | Returns `int` (crossing count). |
| `shape.h` | `ShapeRef` | `libavoid_py.ShapeRef` | phase 2 | |
| `connector.h` | `ConnType` | `libavoid_py.ConnType` | phase 2 | |
| `connector.h` | `ConnRef` | `libavoid_py.ConnRef` | phase 2 | |
| `connector.h` | `ConnRef::setFixedRoute` + related | `ConnRef.set_fixed_route`, `set_fixed_existing_route`, `has_fixed_route`, `clear_fixed_route` | phase 3 | Added for `penaltyRerouting01`. |
| `connend.h` | `ConnDirFlag` | `libavoid_py.ConnDirFlag` | phase 2 | |
| `connend.h` | `ConnEnd` | `libavoid_py.ConnEnd` | phase 2 | Point, point-with-direction-flags, junction, and shape-pin constructors all wrapped. |
| `connend.h` | `ConnEnd::junction` | `ConnEnd.junction` | phase 4 | Returns the attached :class:`JunctionRef` or ``None``. |
| `connend.h` | `ConnEnd::shape` | `ConnEnd.shape` | phase 4 | Returns the attached :class:`ShapeRef` (when type is ``ShapePin``) or ``None``. |
| `connend.h` | `ConnEnd::pinClassId` | `ConnEnd.pin_class_id` | phase 4 | Returns the connection-pin class ID this endpoint targets. |
| `connend.h` | `ConnEndType` | `libavoid_py.ConnEndType` | phase 2 | |
| `junction.h` | `JunctionRef` | `libavoid_py.JunctionRef` | phase 4 | Property-style ``position``, ``position_fixed``, ``recommended_position``; ``remove_and_merge_connectors`` (renamed from upstream's ``removeJunctionAndMergeConnectors``); see ADR 0003. |
| `router.h` | `Router::deleteJunction` | `Router.delete_junction` | phase 4 | |
| `router.h` | `Router::moveJunction` | `Router.move_junction` | phase 4 | Both Point and (dx, dy) overloads. |
| `connectionpin.h` | `ShapeConnectionPin` | `libavoid_py.ShapeConnectionPin` | phase 4 | Modern (7-arg) shape ctor and the junction ctor; ``exclusive`` property; see ADR 0004. The pre-3.0 compat ctor is deliberately not wrapped. |
| `connectionpin.h` | `CONNECTIONPIN_UNSET`, `CONNECTIONPIN_CENTRE` | module-level ints | phase 4 | |
| `connectionpin.h` | `ATTACH_POS_*` constants | module-level floats | phase 4 | ``ATTACH_POS_LEFT`` aliases ``_TOP``; ``ATTACH_POS_RIGHT`` aliases ``_BOTTOM``. |

Remaining phase-4 areas (clusters, hyperedges, checkpoints,
callbacks) are not wrapped yet. Each gets its own phase and
decision record.

## Upstream test translation status

Every enabled upstream regression test is represented by a file under
`tests/upstream/`. The table records the outcome of
`pytest tests/upstream/` at the libavoid commit pinned in
`vendor/adaptagrams` at the time of writing.

Status legend:

- **passing** — a hand-authored assertion translated from upstream
  (`exists_*` return, inline `assert`, or simply "transaction
  processed without raising") holds against libavoid-py.
- **skipped (needs X)** — the translated test file exists as a
  `pytest.skip` stub; the body cannot be ported until feature X is
  wrapped. The stub records the translation target.
- **disabled upstream** — listed in `Makefile.am`'s
  "Disabled tests" or omitted from `check_PROGRAMS`; we mirror
  upstream's decision and do not translate.

| upstream test | status | signal / blocker |
|---------------|--------|------------------|
| 2junctions | skipped | translator support for state-capture test() harnesses |
| buildOrthogonalChannelInfo1 | skipped | translator support for state-capture test() harnesses |
| checkpointNudging1 | skipped | needs checkpoints |
| checkpointNudging2 | skipped | needs checkpoints |
| checkpointNudging3 | skipped | needs checkpoints |
| checkpoints01 | skipped | needs checkpoints |
| checkpoints02 | skipped | needs checkpoints |
| checkpoints03 | skipped | needs checkpoints |
| complex | skipped | needs callbacks |
| connectionpin01 | passing | crash-only |
| connectionpin02 | skipped | ShapeRef.transformConnectionPinPositions accessor |
| connectionpin03 | passing | crash-only |
| connendmove | skipped | translator support for implicit Point→ConnEnd at call sites |
| corneroverlap01 | disabled upstream | — |
| endlessLoop01 | skipped | needs hyperedges |
| example | skipped | needs callbacks |
| finalSegmentNudging1 | passing | `exists_crossings() == 0` |
| finalSegmentNudging2 | passing | `not exists_orthogonal_fixed_segment_overlap(at_ends=True)` |
| finalSegmentNudging3 | skipped | needs checkpoints |
| forwardFlowingConnectors01 | passing | `len(connector6.display_route()) == 4` |
| freeFloatingDirection01 | passing | `len(conn_ref239.display_route()) == 4` |
| hola01 | passing | crash-only |
| hyperedge01 | skipped | needs hyperedges |
| hyperedge02 | skipped | needs hyperedges |
| hyperedgeLoop1 | skipped | translator support for state-capture test() harnesses |
| hyperedgeRerouting01 | skipped | needs hyperedges |
| improveHyperedge01 | skipped | needs hyperedges |
| improveHyperedge02 | skipped | needs hyperedges |
| improveHyperedge03 | skipped | needs hyperedges |
| improveHyperedge04 | skipped | needs hyperedges |
| improveHyperedge05 | skipped | needs hyperedges |
| improveHyperedge06 | skipped | needs hyperedges |
| infinity | passing | crash-only |
| inline | passing | crash-only |
| inlineoverlap01 | passing | `not exists_orthogonal_touching_paths()` |
| inlineoverlap02 | passing | `not exists_orthogonal_fixed_segment_overlap()` |
| inlineoverlap03 | passing | `not exists_orthogonal_fixed_segment_overlap()` |
| inlineoverlap04 | passing | `not exists_orthogonal_fixed_segment_overlap()` |
| inlineoverlap05 | passing | `not exists_orthogonal_fixed_segment_overlap()` |
| inlineoverlap06 | passing | `not exists_orthogonal_fixed_segment_overlap()` |
| inlineoverlap07 | passing | crash-only |
| inlineoverlap08 | passing | `not exists_orthogonal_fixed_segment_overlap()` |
| inlineOverlap09 | passing | `not exists_orthogonal_fixed_segment_overlap()` |
| inlineOverlap10 | passing | `not exists_orthogonal_fixed_segment_overlap()` |
| inlineOverlap11 | skipped | needs hyperedges |
| inlineShapes | passing | crash-only |
| junction01 | passing | crash-only |
| junction02 | passing | crash-only |
| junction03 | passing | crash-only |
| junction04 | skipped | ConnRef.splitAtSegment accessor |
| latesetup | skipped | needs callbacks |
| lineSegWrapperCrash1 | passing | crash-only |
| lineSegWrapperCrash2 | passing | crash-only |
| lineSegWrapperCrash3 | passing | crash-only |
| lineSegWrapperCrash4 | passing | crash-only |
| lineSegWrapperCrash5 | passing | crash-only |
| lineSegWrapperCrash6 | passing | crash-only |
| lineSegWrapperCrash7 | passing | crash-only |
| lineSegWrapperCrash8 | passing | crash-only |
| multiconnact | skipped | needs callbacks |
| node1 | passing | crash-only |
| nudgeCrossing01 | skipped | needs checkpoints |
| nudgeintobug | passing | `not (overlap or touching)` |
| nudgeold | passing | crash-only |
| nudgingSkipsCheckpoint01 | skipped | needs checkpoints |
| nudgingSkipsCheckpoint02 | skipped | needs checkpoints |
| orderassertion | passing | crash-only |
| orthordering01 | passing | `exists_crossings() == 0` |
| orthordering02 | passing | `exists_crossings() == 0` |
| overlappingRects | passing | crash-only |
| penaltyRerouting01 | passing | `exists_crossings() == 0` |
| performance01 | passing | crash-only |
| reallyslowrouting | disabled upstream | — |
| removeJunctions01 | skipped | translator support for endpoint connectivity assertion |
| restrictedNudging | passing | `not exists_orthogonal_touching_paths()` |
| slowrouting | passing | crash-only |
| tjunct | passing | crash-only |
| treeRootCrash01 | skipped | needs hyperedges |
| treeRootCrash02 | skipped | needs hyperedges |
| unsatisfiableRangeAssertion | disabled upstream | — |
| validPaths01 | passing | `not exists_invalid_orthogonal_paths()` |
| validPaths02 | passing | `not exists_invalid_orthogonal_paths()` |
| vertlineassertion | passing | crash-only |

## Summary

- **passing**: 46 / 83
- **skipped**: 34 / 83 — grouped:
  - feature gaps:
    - needs hyperedges: 13
    - needs checkpoints: 10
    - needs callbacks: 4
  - translator gaps (binding is complete; the upstream test uses a
    pattern the auto-translator does not yet emit):
    - state-capture ``test()`` harnesses
      (`2junctions`, `buildOrthogonalChannelInfo1`, `hyperedgeLoop1`)
    - implicit Point→ConnEnd at call sites (`connendmove`)
    - endpoint connectivity assertion (`removeJunctions01`)
  - small unwrapped accessors (one-line follow-up each, deferred to
    keep this PR focused):
    - `ShapeRef.transformConnectionPinPositions` (`connectionpin02`)
    - `ConnRef.splitAtSegment` (`junction04`)
- **disabled upstream**: 3 / 83

Phase 4 progresses one feature at a time; each feature lands its
own ADR under `docs/decisions/` and unblocks whichever skip stubs
were waiting on it. Re-run `python scripts/translate_upstream.py`
after a feature lands to regenerate tests against the new wrapper
surface.

Junctions (ADR 0003) and connection pins (ADR 0004) have both
landed. The remaining feature gaps (hyperedges, checkpoints,
callbacks) are the natural next phases; the small translator and
accessor gaps above can be picked up opportunistically.
