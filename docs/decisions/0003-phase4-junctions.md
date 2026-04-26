# ADR 0003 — Phase 4: JunctionRef

- **Status:** proposed
- **Date:** 2026-04-26
- **Applies to:** the first slice of phase 4 in `CLAUDE.md` §5.

## Context

Phase 3 closed with 32 of 83 upstream regression tests passing and 48
skipped on phase-4 feature gaps. The five gaps, by number of skipped
tests they account for in `docs/api-coverage.md`:

- hyperedges — 13
- connection pins — 11
- junctions — 11
- checkpoints — 9
- callbacks — 4

Junctions are picked first because:

- They are a self-contained, narrow API (one new class plus three
  Router methods plus one extra `ConnEnd` constructor — see below).
- They are a hard prerequisite for any future hyperedge work
  (`HyperedgeRerouter` operates on connectors that terminate at
  junctions). Wrapping junctions does not commit us to wrapping
  hyperedges, but wrapping hyperedges first would force us to wrap
  junctions too.
- They directly unblock the six tests already stubbed under
  `tests/upstream/test_2junctions.py`,
  `tests/upstream/test_junction01.py` … `_junction04.py`, and
  `tests/upstream/test_remove_junctions01.py`. Other "needs
  junctions"-tagged tests in `docs/api-coverage.md`
  (`buildOrthogonalChannelInfo1`, `hyperedgeLoop1`, `node1`,
  `slowrouting`, `tjunct`) will be re-examined; some are likely to
  remain skipped on a secondary feature (hyperedges, callbacks).

## Decision

Wrap `Avoid::JunctionRef` and the small set of supporting calls that
make it usable from Python. Specifically:

### New Python class `libavoid_py.JunctionRef`

Mirrors `vendor/adaptagrams/cola/libavoid/junction.h` exactly, with
the project's standard `camelCase` → `snake_case` translation:

| C++ | Python | Notes |
|-----|--------|-------|
| `JunctionRef(Router*, Point, unsigned int id = 0)` | `JunctionRef(router, position, id=0)` | `id=0` defers to libavoid's auto-id assignment, matching upstream. |
| `position() const` | `position` (read-only property) | |
| `setPositionFixed(bool)` / `positionFixed() const` | `position_fixed` (read/write property) | Pythonic property — no separate getter/setter. Single-name property keeps the binding thin. |
| `recommendedPosition() const` | `recommended_position` (read-only property) | |
| `makeRectangle(Router*, const Point&)` | `make_rectangle(router, position)` | Returns a `Rectangle`. |
| `preferOrthogonalDimension(size_t)` | `prefer_orthogonal_dimension(dim)` | Accepts `XDIM` / `YDIM` (already exposed in phase 2). |
| `removeJunctionAndMergeConnectors()` | `remove_and_merge_connectors()` | Returns the merged `ConnRef`, or `None` if the junction had ≠ 2 attached connectors. See §Lifetime below. |

Renaming `removeJunctionAndMergeConnectors()` to
`remove_and_merge_connectors()` is the one place we deviate from a
literal name translation — the C++ name embeds the receiver type
("Junction"), which is redundant on a Python method bound to a
`JunctionRef` instance. Recorded here so a future reader does not
"fix" it.

### New `Router` methods

| C++ | Python |
|-----|--------|
| `Router::deleteJunction(JunctionRef*)` | `Router.delete_junction(junction)` |
| `Router::moveJunction(JunctionRef*, const Point&)` | `Router.move_junction(junction, new_position)` |
| `Router::moveJunction(JunctionRef*, double xDiff, double yDiff)` | second overload accepted — implemented as a single `move_junction(junction, ...)` that dispatches on argument shape (`Point` vs. `(x, y)` floats), keeping the binding count to one Python method. |

### New `ConnEnd` constructor

`ConnEnd(JunctionRef*)` is added as a second `ConnEnd(...)`
overload. The existing `ConnEnd.type` accessor (already wrapped in
phase 2 and returning `ConnEndType.ConnEndJunction` when applicable)
gains a corresponding `ConnEnd.junction` accessor returning the
attached `JunctionRef` or `None` (mirrors `ConnEnd::junction()`).

### Lifetime

Three lifetime rules, matching the convention already established
for `ShapeRef` and `ConnRef` in phase 2 — `py::keep_alive` for the
router→object reference, `py::nodelete` holders so Python GC does
not double-free, and use-after-`delete` documented (not actively
intercepted, same as `Router.delete_shape`):

1. **Router owns the junction.** A `JunctionRef` constructed in
   Python is registered with the router by libavoid in its
   constructor. The Python wrapper holds a `py::keep_alive<1, 2>`
   linking the junction's lifetime to the router, exactly as phase
   2 does for `ShapeRef` and `ConnRef`. The user must not call any
   destructor; freeing happens through `Router.delete_junction()`
   or when the router itself is destroyed.

2. **`delete_junction(j)` makes `j` unusable.** The C++ object is
   freed; touching the Python wrapper afterwards is a use-after-
   free. The docstring spells this out; we do not synthesise an
   "invalidated wrapper" check (phase 2 deliberately did not do
   this for `ShapeRef` / `ConnRef` either, and adding it here only
   would be inconsistent — it is a candidate for a future
   cross-cutting ADR if real users hit it).

3. **`remove_and_merge_connectors()` deletes one connector but
   does not free the junction.** Per upstream docstring: the
   junction is removed from the scene but **not** freed; one of
   the two attached connectors is removed *and* deleted; the other
   is returned (merged). Same documentation-only treatment as rule
   2 — the docstring tells the caller (a) the consumed `ConnRef`
   wrapper must not be touched, (b) `delete_junction(j)` is still
   their responsibility for the orphaned junction. The returned
   `ConnRef` is the one libavoid kept alive; pybind11's
   `return_value_policy::reference_internal` keeps it tied to the
   router.

These rules exist because the upstream API hands ownership to the
router with subtle exceptions; documenting them clearly in the
binding is cheaper than debugging segfaults later.

## Rationale

- Junctions are the smallest phase-4 increment that delivers a
  visible test-count change and a structural prerequisite. Picking
  the smallest available unit keeps phase 4 reviewable.
- Using Python `@property` for `position`, `position_fixed`, and
  `recommended_position` matches the geometry types' style from
  phase 2 (`Box.min`, `Polygon.size`) and is preferable to a
  literal `set_position_fixed(bool)` + `position_fixed()` pair that
  would read like a C++ port rather than Python.
- The `remove_and_merge_connectors` rename is the only deviation
  from literal name translation in this phase. Documenting it in an
  ADR is what `CLAUDE.md` §2 requires of any API name divergence.
- We do *not* introduce a "connector list per junction" accessor in
  this phase. libavoid does not expose one publicly; tracking
  attachments lives on the connector side via `ConnEnd.junction`.
  Adding a synthesized list later as a phase-4 extension is fine,
  but it would be invented API and wants its own ADR.

## Consequences

- New file `src/bindings/junction.cpp`; new entries in
  `src/bindings/module.cpp`; small additions to
  `src/bindings/router.cpp` (delete/move) and
  `src/bindings/connector.cpp` (the junction-aware `ConnEnd`
  overload + accessor).
- `stubs/libavoid_py.pyi` gains `JunctionRef` and the new `Router`
  / `ConnEnd` methods.
- `tests/upstream/test_2junctions.py`,
  `test_junction01.py`…`test_junction04.py`, and
  `test_remove_junctions01.py` are re-translated (un-skipped) by
  re-running `scripts/translate_upstream.py`. Tests that turn out
  to need a second phase-4 feature stay skipped with an updated
  reason string.
- `docs/api-coverage.md` gets a new row for `JunctionRef` and the
  new `Router` / `ConnEnd` calls; the test-status table and the
  summary counts are updated in the same PR.
- `README.md` adds a one-line mention of junction support to its
  feature list (per the project convention recorded in CLAUDE.md
  §6 and the user's standing preference: README updates ride with
  the API-changing PR, not in a trailing docs PR).
- Hyperedges, pins, checkpoints, and callbacks remain blocked.
  Hyperedge work, when it lands, can rely on `JunctionRef` as a
  given.

## Alternatives considered

- **Connection pins first.** Same skip-count payoff (11 tests) and
  also useful as a building block, but pins have a larger surface
  (`ShapeConnectionPin` + four enum types + several `ShapeRef` and
  `ConnEnd` overloads). Junctions are smaller, so they go first;
  pins follow as ADR 0004.
- **Bundle junctions and hyperedges into one phase.** Rejected:
  hyperedges add `HyperedgeRerouter`, `HyperedgeNewAndDeletedObjectLists`,
  and the two `improveHyperedgeRoutes*` router options' full
  semantics. Doing them in one PR would violate the "small,
  reviewable PRs" rule from CLAUDE.md §2.
- **Skip the `remove_and_merge_connectors` method for now.** It is
  the only nontrivial lifetime case in this slice, and dropping it
  would simplify the binding. Rejected because `removeJunctions01`
  exists upstream specifically to regression-test it; skipping the
  method would leave that test stub stranded.
- **Expose `setPositionFixed` / `positionFixed` as separate
  methods (literal port).** Rejected: phase 2 already established
  the property idiom for boolean state on the geometry types; doing
  the same here keeps the wrapper coherent.
