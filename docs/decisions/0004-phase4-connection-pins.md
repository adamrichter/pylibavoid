# ADR 0004 — Phase 4: connection pins

- **Status:** proposed
- **Date:** 2026-04-26
- **Applies to:** the second slice of phase 4 in `CLAUDE.md` §5.

## Context

After ADR 0003 (junctions) landed, the skipped-test inventory in
`docs/api-coverage.md` looks like:

- needs connection pins — 17  ← biggest unblock
- needs hyperedges — 13
- needs checkpoints — 10
- needs callbacks — 4

Connection pins are picked next. They are the largest payoff still
available, they are a strict dependency for any future hyperedge
work (the hyperedge tests that remain blocked also use pins), and
they round out the "shapes can be connected to" story that the
phase-2 `ShapeRef` started.

The upstream surface, read from
`vendor/adaptagrams/cola/libavoid/connectionpin.h` and the existing
`connend.h`:

- `ShapeConnectionPin` class with three constructors:
  1. `(ShapeRef*, classId, xOff, yOff, proportional, insideOff, visDirs)` — modern.
  2. `(ShapeRef*, classId, xOff, yOff, insideOff, visDirs)` — pre-3.0 compat (no `proportional`).
  3. `(JunctionRef*, classId, visDirs = ConnDirNone)` — pin on a junction.
- Methods: `setConnectionCost`, `position(newPoly = Polygon())`,
  `directions`, `setExclusive`, `isExclusive`, `ids` (returns
  `pair<uint, uint>`).
- Module-level constants: `CONNECTIONPIN_UNSET`,
  `CONNECTIONPIN_CENTRE`, `ATTACH_POS_TOP`, `ATTACH_POS_BOTTOM`,
  `ATTACH_POS_LEFT`, `ATTACH_POS_RIGHT`, `ATTACH_POS_CENTRE`,
  `ATTACH_POS_MIN_OFFSET`, `ATTACH_POS_MAX_OFFSET`.
- New `ConnEnd` constructor `ConnEnd(ShapeRef*, classId)` and the
  `ConnEnd::shape()` and `ConnEnd::pinClassId()` accessors.

## Decision

Wrap `Avoid::ShapeConnectionPin`, the supporting constants, and the
new `ConnEnd` overload + accessors. Specifically:

### New Python class `libavoid_py.ShapeConnectionPin`

Mirrors the upstream class with the project's standard
`camelCase` → `snake_case` translation. Property style is used for
`exclusive` (boolean state), matching ADR 0003's precedent for
`JunctionRef.position_fixed`.

| C++ | Python | Notes |
|-----|--------|-------|
| `ShapeConnectionPin(ShapeRef*, classId, xOff, yOff, proportional, insideOff, visDirs)` | `ShapeConnectionPin(shape, class_id, x_offset, y_offset, proportional, inside_offset, visibility_directions)` | All seven args required (matches upstream). |
| `ShapeConnectionPin(ShapeRef*, classId, xOff, yOff, insideOff, visDirs)` | dropped | Pre-3.0 compat constructor; upstream comment says "Provided for compatibility with old debug files." Skipping it keeps the binding small; can be added later if a real call site appears. |
| `ShapeConnectionPin(JunctionRef*, classId, visDirs = ConnDirNone)` | `ShapeConnectionPin(junction, class_id, visibility_directions=ConnDirFlag.ConnDirNone)` | Used by upstream to give junctions explicit pins; rare from user code (the JunctionRef ctor auto-creates four pins) but cheap to wrap. |
| `setConnectionCost(double)` | `set_connection_cost(cost)` | |
| `position(const Polygon& newPoly = Polygon()) const` | `position(new_poly=None)` | The upstream default is an empty `Polygon()`, which the implementation reads as "use current shape position". The Python default `None` is translated to that empty Polygon at the call site, sparing callers a ``Polygon()`` import for the common case. |
| `directions()` | `directions()` | Returns the `ConnDirFlags` bitmask as a plain `int`, matching `ConnEnd.directions` from phase 2. |
| `setExclusive(bool)` / `isExclusive()` | `exclusive` (read/write property) | Single-name property for parity with `JunctionRef.position_fixed`. |
| `ids() -> pair<uint, uint>` | `ids()` returns a 2-tuple `(containing_object_id, class_id)` | pybind11/stl pair conversion. |
| `operator==`, `operator<` | not exposed | Used for `ShapeConnectionPinSet` ordering inside libavoid; no role in the Python API. |

### Module-level constants

Exposed verbatim under `libavoid_py`:

- `CONNECTIONPIN_UNSET` (= `INT_MAX`)
- `CONNECTIONPIN_CENTRE` (= `INT_MAX - 1`)
- `ATTACH_POS_TOP`, `ATTACH_POS_BOTTOM`, `ATTACH_POS_CENTRE`
- `ATTACH_POS_LEFT`, `ATTACH_POS_RIGHT` (aliases for `_TOP` / `_BOTTOM`)
- `ATTACH_POS_MIN_OFFSET`, `ATTACH_POS_MAX_OFFSET`

These are flat module attributes, not an enum. Upstream treats them
as plain integer / double literals; a Python enum would invent type
hierarchy that is not in the C++ API and would break expressions
like `class_id = CONNECTIONPIN_CENTRE` from working as a bare
integer.

### `ConnEnd` additions (extending the phase-2 binding)

| C++ | Python |
|-----|--------|
| `ConnEnd(ShapeRef*, unsigned int)` | `ConnEnd(shape, class_id)` constructor overload. |
| `ShapeRef *ConnEnd::shape() const` | `ConnEnd.shape()` returning the `ShapeRef` or `None`. Mirrors `ConnEnd.junction()` from ADR 0003. |
| `unsigned int ConnEnd::pinClassId() const` | `ConnEnd.pin_class_id()` returning the integer class ID; only meaningful when `type() == ConnEndType.ShapePin`. |

The `ConnEndType.ShapePin` value's docstring (currently "phase-4
feature; not constructible from Python yet") is updated.

### Lifetime

The pin↔shape ownership is the new wrinkle compared to ADR 0003.
Upstream is explicit: "Ownership of this ShapeConnectionPin is
passed to the parent shape." So the chain is now:

```
JunctionRef ─┐
ShapeRef ───┴─→ Router  (existing keep_alive from phase 2 / ADR 0003)
ShapeConnectionPin ─→ ShapeRef OR JunctionRef  (new this PR)
ConnEnd ─→ JunctionRef (ADR 0003)
ConnEnd ─→ ShapeRef    (new this PR, via ConnEnd(shape, classId))
```

Concretely:

1. **Shape (or junction) owns the pin.** A `ShapeConnectionPin`
   constructed in Python is registered with its parent in the
   constructor. The Python wrapper uses
   `std::unique_ptr<ShapeConnectionPin, py::nodelete>` and
   `py::keep_alive<1, 2>` so the parent shape (or junction)
   outlives the pin's Python wrapper. This is the same pattern
   used for `ShapeRef → Router` and `ConnRef → Router` in phase 2.
2. **Discarding the Python pin handle is normal.** Upstream code
   routinely writes `new ShapeConnectionPin(shape, ...)` with the
   return value unused — the side effect on the shape's pin set
   is what matters. With `nodelete` + `keep_alive`, dropping the
   Python wrapper is safe; the C++ pin lives on inside the shape.
3. **`ConnEnd(shape, class_id)` keeps the shape alive** via
   `py::keep_alive<1, 2>` on the new constructor, mirroring the
   `ConnEnd(JunctionRef*)` case.
4. **Pin destruction follows shape destruction.** When the parent
   shape is freed (Router goes out of scope, or
   `Router.delete_shape` runs), libavoid frees its pins. Any
   surviving Python pin wrappers are now dangling; touching them
   is a use-after-free, documented in the docstring (matching the
   convention from phase 2 / ADR 0003 — no synthesised
   invalidation check).

## Rationale

- Connection pins is the largest single-feature unblock available
  (17 skipped tests). Tackling it next maximises post-PR signal
  per unit of binding work.
- Constants stay as flat module attributes because that's what they
  are upstream. Promoting them to an `IntEnum` would be inventive
  in a way that ADR 0003's property idiom was not — properties
  swap one Python idiom for another C++-idiomatic getter/setter
  pair, but enums change the *type* of the constant and would
  make `class_id = CONNECTIONPIN_CENTRE` produce an enum where the
  C++ produces an int.
- Skipping the pre-3.0 compat constructor keeps the binding from
  carrying an alias the project does not need. None of the
  upstream tests use it (they all pass the `proportional` flag).
- Keeping `position(new_poly=None)` rather than literally exposing
  `position(new_poly=Polygon())` avoids a per-call `Polygon`
  allocation for the common case and avoids the Python mutable-
  default-argument footgun. The semantics match upstream.
- We do **not** add a `ShapeRef.connection_pins()` accessor.
  Upstream does not expose one publicly, and connectors find pins
  via class IDs at routing time. Adding a Python-side list would
  invent API. Re-evaluate if a real caller asks.

## Consequences

- New file `src/bindings/connectionpin.cpp`; new entries in
  `src/bindings/module.cpp` and `src/bindings/bindings.h`; small
  additions to `src/bindings/connector.cpp` (the `ConnEnd(shape,
  class_id)` overload + the two new accessors); the
  `ConnEndType.ShapePin` docstring is updated.
- 17 upstream test stubs are re-translated. Some will pass
  immediately; some may turn out to need a *second* feature
  (hyperedges, callbacks) and stay skipped under a new reason.
  The exact new pass count is reported in the PR body, not
  pre-committed here.
- `docs/api-coverage.md` gets a `ShapeConnectionPin` row, the
  new `ConnEnd` accessors, the constants, and updated test-status
  / summary tables.
- `README.md` adds `ShapeConnectionPin` to the wrapped-API list in
  the same PR (project convention).
- After this PR the only remaining phase-4 skips are hyperedges,
  checkpoints, and callbacks. Hyperedges become the next natural
  candidate (largest remaining count + builds directly on
  junctions and pins).

## Alternatives considered

- **Bind only `ConnEnd(shape, class_id)` and skip
  `ShapeConnectionPin` itself.** Rejected: connectors find pins by
  class ID, so without a way to *create* pins from Python, the new
  ConnEnd ctor is unusable. A "pinless" subset is not a coherent
  shipping unit.
- **Wrap pins as `shape.add_connection_pin(...)`,
  `junction.add_connection_pin(...)` helpers, hiding the
  `ShapeConnectionPin` class.** Rejected: this is invented API.
  The upstream pattern of constructing a pin and discarding the
  handle works fine in Python; introducing a helper on shapes
  would create a parallel API surface to maintain and would
  diverge from the upstream documentation users will find online.
- **Promote `ATTACH_POS_*` and `CONNECTIONPIN_*` to enums.**
  Rejected as discussed above — changes the type, breaks bare-int
  usage.
- **Bundle pins with hyperedges into one phase.** Rejected for the
  same reason ADR 0003 rejected bundling junctions with hyperedges:
  the PR would be too large to review usefully.
