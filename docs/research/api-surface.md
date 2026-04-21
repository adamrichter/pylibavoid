# libavoid public API surface

Anchor commit: `840ebcff20dbba36ad03a2160edf7cbaf9859984` of
`mjwybrow/adaptagrams`, directory `cola/libavoid/`.

## Method

`libavoid.h` is the sanctioned user-facing include. It pulls in 13
headers. Everything **transitively reachable from those headers**,
declared in `namespace Avoid`, and not in a `private:` section is
public API.

Of those 13 headers, five are internal plumbing even though they are
installed:

- `graph.h` — `EdgeInf`, `EdgeList`, visibility graph edges. Internal
  state of the router.
- `vertices.h` — `VertInf`, `VertID`, visibility graph vertices.
  Internal state of the router.
- `visibility.h` — one free function `vertexVisibility()`, internal.
- `debug.h` — `db_printf` helper macro, only active under
  `LIBAVOID_DEBUG`.
- `timer.h` — the `Timer` class, only active under `AVOID_PROFILE`.

A well-behaved user never instantiates these or calls their functions;
the upstream tests never do. They are marked **out-of-scope** below
for the Python wrapper.

Obstacle (`obstacle.h`) is also reached transitively (as the base of
`ShapeRef` and `JunctionRef`). It is a documented-but-abstract
superclass whose two public methods (`id()`, `polygon()`, `router()`,
`position()`) are already exposed on both subclasses. We wrap the
subclasses directly and do not expose `Obstacle` as its own Python
type.

Tags per entry:

- **v1-must-wrap** — required for phase 2 deliverables in CLAUDE.md
  §5. These directly support routing a connector around shapes.
- **v1-nice-to-have** — reachable from phase-2 types and low-cost to
  expose (accessors, debug helpers, ID methods, transaction control).
- **v4-phase** — deferred to phase 4: pins, junctions, clusters,
  hyperedges, checkpoints, callbacks. See `CLAUDE.md` §5.
- **internal** — router-internal state or debugging hook that is
  not part of the "use libavoid from a user's application" story.
  Explicitly not wrapped unless a concrete user asks.
- **out-of-scope** — internal helper class/function that happens to
  be in an installed header but is not part of the intended user API.

Headers use `AVOID_EXPORT` on every type the upstream author
considers part of the ABI. That macro is our implicit whitelist — if
a class lacks it, treat it as internal until we have a reason to
expose it.

---

## `geomtypes.h`

### Constants

| Symbol | Value | Tag |
|--------|-------|-----|
| `Avoid::XDIM` | `0` | v1-must-wrap |
| `Avoid::YDIM` | `1` | v1-must-wrap |
| `Avoid::kUnassignedVertexNumber` | `8` | internal |
| `Avoid::kShapeConnectionPin` | `9` | internal |

### `Point` (class, `AVOID_EXPORT`) — v1-must-wrap

A point in the plane.

| Member | Tag | Notes |
|--------|-----|-------|
| `Point()` | v1-must-wrap | Default constructor. |
| `Point(double x, double y)` | v1-must-wrap | Standard constructor. |
| `operator==(const Point&)` | v1-must-wrap | Exact equality. |
| `equals(const Point&, double epsilon=0.0001)` | v1-must-wrap | Approximate equality. |
| `operator!=(const Point&)` | v1-must-wrap | |
| `operator<(const Point&)` | v1-nice-to-have | Lexicographic; documented as only for `std::set`. |
| `operator[](size_t dim)` | v1-must-wrap | Dimension access; 0=x, 1=y. |
| `operator+`, `operator-` | v1-must-wrap | Treat as vector arithmetic. |
| `double x`, `double y` | v1-must-wrap | Public fields. |
| `unsigned int id` | v1-nice-to-have | Optional ID. |
| `unsigned short vn` | internal | Vertex number, internal use. |

### `Vector` — v1-must-wrap

`typedef Point Vector;` — expose as Python alias.

### `Box` (class, `AVOID_EXPORT`) — v1-must-wrap

Bounding box.

| Member | Tag |
|--------|-----|
| `Point min`, `Point max` | v1-must-wrap |
| `double length(size_t dim)` | v1-nice-to-have |
| `double width()` | v1-must-wrap |
| `double height()` | v1-must-wrap |

### `PolygonInterface` (class, `AVOID_EXPORT`) — internal

Abstract common interface for `Polygon` and `ReferencingPolygon`.
Not surfaced in Python — we mirror the methods on the concrete
classes.

### `Edge` (class, `AVOID_EXPORT`) — v1-nice-to-have

Two-point line segment with fields `Point a`, `Point b`.

### `Polygon` (class, `AVOID_EXPORT`) — v1-must-wrap

Dynamic polygon.

| Member | Tag | Notes |
|--------|-----|-------|
| `Polygon()` | v1-must-wrap | Empty. |
| `Polygon(int n)` | v1-must-wrap | n-point polygon. |
| `Polygon(const PolygonInterface&)` | v1-nice-to-have | Copy/convert. |
| `clear()` | v1-nice-to-have | |
| `empty()`, `size()`, `id()`, `at(size_t)` | v1-must-wrap | |
| `setPoint(size_t, const Point&)` | v1-must-wrap | |
| `simplify()` | v1-nice-to-have | Collapses collinear segments. |
| `curvedPolyline(double, bool closed=false)` | v1-nice-to-have | Bezier approximation. |
| `translate(double dx, double dy)` | v1-nice-to-have | |
| `int _id` | v1-nice-to-have | Public ID field. |
| `std::vector<Point> ps` | v1-must-wrap | The points. |
| `std::vector<char> ts` | v1-nice-to-have | Per-point operation letter (`M`/`L`/`C`/`Z`). |
| `std::vector<std::pair<size_t,Point>> checkpointsOnRoute` | v4-phase | Tied to checkpoint feature. |
| `checkpointsOnSegment(size_t, int)` | v4-phase | Tied to checkpoint feature. |

### `PolyLine` — v1-must-wrap

`typedef Polygon PolyLine;` — connector routes are returned as this
type. In Python it can be an alias of the `Polygon` wrapper.

### `ReferencingPolygon` (class, `AVOID_EXPORT`) — v4-phase

A polygon that references points from other polygons. Only used for
cluster boundaries, which is a phase-4 cluster feature. Defer.

### `Rectangle` (class, `AVOID_EXPORT`, extends `Polygon`) — v1-must-wrap

| Member | Tag |
|--------|-----|
| `Rectangle(const Point& topLeft, const Point& bottomRight)` | v1-must-wrap |
| `Rectangle(const Point& centre, double width, double height)` | v1-must-wrap |

---

## `router.h`

### Enum `RouterFlag` — v1-must-wrap

Constructor flags for `Router`. Values:

| Value | Tag | Notes |
|-------|-----|-------|
| `PolyLineRouting = 1` | v1-must-wrap | |
| `OrthogonalRouting = 2` | v1-must-wrap | May be combined with `|`. |

### Enum `RoutingParameter` — v1-must-wrap

Routing penalty/parameter identifiers. All values listed so the
Python `IntEnum` matches libavoid exactly:

| Value | Tag |
|-------|-----|
| `segmentPenalty = 0` | v1-must-wrap |
| `anglePenalty` | v1-must-wrap |
| `crossingPenalty` | v1-must-wrap |
| `clusterCrossingPenalty` | v4-phase (cluster) |
| `fixedSharedPathPenalty` | v1-nice-to-have |
| `portDirectionPenalty` | v1-nice-to-have |
| `shapeBufferDistance` | v1-must-wrap |
| `idealNudgingDistance` | v1-must-wrap |
| `reverseDirectionPenalty` | v1-nice-to-have |
| `lastRoutingParameterMarker` | internal (sentinel) |

### `PenaltyType` — v1-must-wrap

`typedef enum RoutingParameter PenaltyType;` — backwards-compat alias.
Expose only under the new name in Python (do not create a second
Python enum).

### Enum `RoutingOption` — v1-must-wrap

| Value | Tag |
|-------|-----|
| `nudgeOrthogonalSegmentsConnectedToShapes = 0` | v1-must-wrap |
| `improveHyperedgeRoutesMovingJunctions` | v4-phase (hyperedge) |
| `penaliseOrthogonalSharedPathsAtConnEnds` | v1-nice-to-have |
| `nudgeOrthogonalTouchingColinearSegments` | v1-nice-to-have |
| `performUnifyingNudgingPreprocessingStep` | v1-must-wrap |
| `improveHyperedgeRoutesMovingAddingAndDeletingJunctions` | v4-phase (hyperedge) |
| `nudgeSharedPathsWithCommonEndPoint` | v1-nice-to-have |
| `lastRoutingOptionMarker` | internal (sentinel) |

### Enum `TransactionPhases` — v1-nice-to-have

Phase identifiers passed to
`Router::shouldContinueTransactionWithProgress()`. All seven values
(`TransactionPhaseOrthogonalVisibilityGraphScanX`,
`...ScanY`, `TransactionPhaseRouteSearch`,
`TransactionPhaseCrossingDetection`, `TransactionPhaseRerouteSearch`,
`TransactionPhaseOrthogonalNudgingX`, `...Y`,
`TransactionPhaseCompleted`) are part of the callback contract. Wrap
them together with the virtual if we wrap the virtual at all (it is
subclass-of-Router territory and may be v4-phase).

### Constants — v1-must-wrap

- `Avoid::zeroParamValue = 0`
- `Avoid::chooseSensibleParamValue = -1`

### `LineRep` (struct) — internal

Used for debug SVG highlighting; internal.

### `ConnRerouteFlagDelegate` — internal

Explicitly documented in the header as "internal helper class that
should not be used by the user."

### `TopologyAddonInterface` — out-of-scope

Header comment: "This is an internal helper class that should not
be used by the user. It is used by libtopology to add additional
functionality to libavoid while keeping libavoid dependency free."

### `Router` (class, `AVOID_EXPORT`) — v1-must-wrap

Central router instance.

| Member | Tag | Notes |
|--------|-----|-------|
| `Router(unsigned int flags)` | v1-must-wrap | |
| `virtual ~Router()` | v1-must-wrap | Destroys all owned shapes/connectors. |
| `setTransactionUse(bool)` | v1-nice-to-have | |
| `transactionUse()` | v1-nice-to-have | |
| `processTransaction()` | v1-must-wrap | |
| `deleteShape(ShapeRef*)` | v1-must-wrap | |
| `moveShape(ShapeRef*, const Polygon&, bool first_move=false)` | v1-must-wrap | |
| `moveShape(ShapeRef*, double dx, double dy)` | v1-must-wrap | |
| `deleteJunction(JunctionRef*)` | v4-phase (junction) | |
| `deleteConnector(ConnRef*)` | v1-must-wrap | |
| `moveJunction(JunctionRef*, const Point&)` | v4-phase (junction) | |
| `moveJunction(JunctionRef*, double, double)` | v4-phase (junction) | |
| `setRoutingParameter(RoutingParameter, double=chooseSensibleParamValue)` | v1-must-wrap | |
| `routingParameter(RoutingParameter)` | v1-must-wrap | |
| `setRoutingOption(RoutingOption, bool)` | v1-must-wrap | |
| `routingOption(RoutingOption)` | v1-must-wrap | |
| `setRoutingPenalty(RoutingParameter, double=chooseSensibleParamValue)` | v1-must-wrap | Convenience wrapper for `setRoutingParameter`. |
| `hyperedgeRerouter()` | v4-phase (hyperedge) | |
| `outputInstanceToSVG(std::string=...)` | v1-nice-to-have | |
| `virtual newObjectId()` | v1-nice-to-have | Overridable; subclass Router in Python? Probably v4. |
| `objectIdIsUnused(unsigned int)` | v1-nice-to-have | |
| `virtual shouldContinueTransactionWithProgress(...)` | v4-phase | Requires a Python subclass pattern; lumps with callback work. |
| `newAndDeletedObjectListsFromHyperedgeImprovement()` | v4-phase (hyperedge) | |
| `setDebugHandler(DebugHandler*)` | out-of-scope | `DebugHandler` type lives in `debughandler.h`, which is not included by `libavoid.h`. |
| `debugHandler()` | out-of-scope | |
| `deleteCluster(ClusterRef*)` | v4-phase (cluster) | |
| `attachedShapes/attachedConns/...` | internal | Undocumented plumbing. |
| `printInfo()` | v1-nice-to-have | Writes to stdout. |
| `existsOrthogonalSegmentOverlap(bool atEnds=false)` | v1-nice-to-have | Test helper. |
| `existsOrthogonalFixedSegmentOverlap(bool atEnds=false)` | v1-nice-to-have | Test helper. |
| `existsOrthogonalTouchingPaths()` | v1-nice-to-have | Test helper. |
| `existsCrossings(bool optimisedForConnectorType=false)` | v1-nice-to-have | Test helper. |
| `existsInvalidOrthogonalPaths()` | v1-must-wrap | Used by 3 upstream validity tests. |
| `outputDiagramSVG(std::string=..., LineReps* = nullptr)` | v1-nice-to-have | |
| `outputDiagramText(std::string=...)` | v1-nice-to-have | Candidate for phase-3 golden data. |
| `outputDiagram(std::string=...)` | v1-must-wrap | Used throughout the test corpus. |
| `setTopologyAddon(...)` / `improveOrthogonalTopology()` | out-of-scope | Requires libtopology. |

Public fields on `Router` (yes, there are many, see `router.h` lines
401–431) — these are essentially internal state. Tag **internal**.
Do not expose: `m_obstacles`, `connRefs`, `clusterRefs`, `visGraph`,
`invisGraph`, `visOrthogGraph`, `contains`, `vertices`,
`enclosingClusters`, `PartialTime`, `SimpleRouting`,
`ClusteredRouting`, `IgnoreRegions`, `UseLeesAlgorithm`,
`InvisibilityGrph`, `SelectiveReroute`, `PartialFeedback`,
`RubberBandRouting`, `st_checked_edges`.

---

## `shape.h`

### Enum `ShapeTransformationType` — v4-phase (pin)

Used only by `ShapeRef::transformConnectionPinPositions`.

Values: `TransformationType_CW90=0`, `CW180`, `CW270`, `FlipX`, `FlipY`.

### `ShapeRef` (class, `AVOID_EXPORT`, extends `Obstacle`) — v1-must-wrap

| Member | Tag | Notes |
|--------|-----|-------|
| `ShapeRef(Router*, Polygon&, unsigned int id=0)` | v1-must-wrap | |
| `virtual ~ShapeRef()` | v1-must-wrap | Not user-called. |
| `polygon()` | v1-must-wrap | |
| `transformConnectionPinPositions(ShapeTransformationType)` | v4-phase (pin) | |
| `position()` | v1-must-wrap | |
| Inherited from `Obstacle`: `id()`, `router()`, `setNewPoly(const Polygon&)`, `routingBox()`, `routingPolygon()`, `attachedConnectors()` | v1-must-wrap | Expose via the Python `ShapeRef` directly. |

---

## `connector.h`

### Enum `ConnType` — v1-must-wrap

| Value | Tag |
|-------|-----|
| `ConnType_None = 0` | v1-nice-to-have (sentinel) |
| `ConnType_PolyLine = 1` | v1-must-wrap |
| `ConnType_Orthogonal = 2` | v1-must-wrap |

### `Checkpoint` (class, `AVOID_EXPORT`) — v4-phase (checkpoint)

| Member | Tag |
|--------|-----|
| `Checkpoint(const Point&)` | v4-phase |
| `Checkpoint(const Point&, ConnDirFlags, ConnDirFlags)` | v4-phase |
| `Checkpoint()` | v4-phase |
| Fields `point`, `arrivalDirections`, `departureDirections` | v4-phase |

### `ConnRef` (class, `AVOID_EXPORT`) — v1-must-wrap

| Member | Tag | Notes |
|--------|-----|-------|
| `ConnRef(Router*, unsigned int id=0)` | v1-must-wrap | |
| `ConnRef(Router*, const ConnEnd& src, const ConnEnd& dst, unsigned int id=0)` | v1-must-wrap | |
| `~ConnRef()` | v1-must-wrap | Not user-called. |
| `setEndpoints(const ConnEnd&, const ConnEnd&)` | v1-must-wrap | |
| `setSourceEndpoint(const ConnEnd&)` | v1-must-wrap | |
| `setDestEndpoint(const ConnEnd&)` | v1-must-wrap | |
| `id()` | v1-must-wrap | |
| `router()` | v1-nice-to-have | |
| `needsRepaint()` | v1-must-wrap | |
| `route()` | v1-nice-to-have | Raw route; debug. |
| `displayRoute()` | v1-must-wrap | Returns the user-facing `PolyLine`. |
| `setCallback(void (*)(void*), void*)` | v4-phase (callback) | Hard: GIL + lifetime. |
| `routingType()` | v1-must-wrap | |
| `setRoutingType(ConnType)` | v1-must-wrap | |
| `splitAtSegment(size_t)` | v4-phase (junction) | Creates a new `JunctionRef`. |
| `setRoutingCheckpoints(const std::vector<Checkpoint>&)` | v4-phase (checkpoint) | |
| `routingCheckpoints()` | v4-phase (checkpoint) | |
| `endpointConnEnds()` | v1-nice-to-have | Useful introspection. |
| `src()`, `dst()` | internal | `VertInf*`, internal plumbing. |
| `setFixedRoute(const PolyLine&)` | v1-nice-to-have | |
| `setFixedExistingRoute()` | v1-nice-to-have | |
| `hasFixedRoute()` | v1-nice-to-have | |
| `clearFixedRoute()` | v1-nice-to-have | |
| `set_route`, `calcRouteDist`, `makeActive`, `makeInactive`, `start`, `removeFromGraph`, `isInitialised`, `makePathInvalid`, `setHateCrossings`, `doesHateCrossings`, `setEndpoint(...)`, `possibleDstPinPoints` | internal | Router-internal plumbing. |

### Free-standing types

- `PtOrder`, `PtOrderMap`, `PointSet`, `PtConnPtrPair`,
  `PointRepVector`, `NodeIndexPairLinkList`, `ConnectorCrossings`,
  `splitBranchingSegments`, `validateBendPoint`, the `CROSSING_*`
  constants — all **internal**. Used by the router's crossing analysis.

---

## `connend.h`

### Enum `ConnDirFlag` — v1-must-wrap

| Value | Tag |
|-------|-----|
| `ConnDirNone = 0` | v1-must-wrap |
| `ConnDirUp = 1` | v1-must-wrap |
| `ConnDirDown = 2` | v1-must-wrap |
| `ConnDirLeft = 4` | v1-must-wrap |
| `ConnDirRight = 8` | v1-must-wrap |
| `ConnDirAll = 15` | v1-must-wrap |

### `ConnDirFlags` — v1-must-wrap

`typedef unsigned int ConnDirFlags;` — expose as an `IntFlag` bitset
alias in Python.

### Enum `ConnEndType` — v1-nice-to-have

`ConnEndPoint`, `ConnEndShapePin`, `ConnEndJunction`, `ConnEndEmpty`.

### `ConnEnd` (class, `AVOID_EXPORT`) — v1-must-wrap

| Member | Tag | Notes |
|--------|-----|-------|
| `ConnEnd(const Point&)` | v1-must-wrap | |
| `ConnEnd(const Point&, ConnDirFlags)` | v1-must-wrap | |
| `ConnEnd(ShapeRef*, unsigned int connectionPinClassID)` | v4-phase (pin) | |
| `ConnEnd(JunctionRef*)` | v4-phase (junction) | |
| `type()` | v1-nice-to-have | |
| `position()` | v1-must-wrap | |
| `directions()` | v1-must-wrap | |
| `shape()` | v4-phase (pin) | |
| `junction()` | v4-phase (junction) | |
| `pinClassId()` | v4-phase (pin) | |
| `ConnEnd()` default, `~ConnEnd()` | v1-nice-to-have | |

---

## `connectionpin.h` — v4-phase (pin)

### Constants

- `CONNECTIONPIN_UNSET = INT_MAX` — v4-phase
- `CONNECTIONPIN_CENTRE = INT_MAX - 1` — v4-phase
- `ATTACH_POS_TOP = 0.0`, `ATTACH_POS_CENTRE = 0.5`,
  `ATTACH_POS_BOTTOM = 1.0`, `ATTACH_POS_LEFT`, `ATTACH_POS_RIGHT` —
  v4-phase
- `ATTACH_POS_MIN_OFFSET = 0`, `ATTACH_POS_MAX_OFFSET = -1` — v4-phase

### `ConnectionPinIds` — v4-phase

`typedef std::pair<unsigned int, unsigned int> ConnectionPinIds;`

### `ShapeConnectionPin` (class, `AVOID_EXPORT`) — v4-phase (pin)

Two shape-pin constructors, one junction-pin constructor,
`setConnectionCost`, `position`, `directions`, `setExclusive`,
`isExclusive`, `ids`, `operator==`, `operator<`. All tagged
**v4-phase**; wrapping requires shape-owned lifetime management.

`CmpConnPinPtr` and `ShapeConnectionPinSet` are **internal** (used by
`Obstacle` to store pin collections).

---

## `junction.h` — v4-phase (junction)

### `JunctionRef` (class, `AVOID_EXPORT`, extends `Obstacle`) — v4-phase

| Member | Tag |
|--------|-----|
| `JunctionRef(Router*, Point position, unsigned int id=0)` | v4-phase |
| `~JunctionRef()` | v4-phase |
| `removeJunctionAndMergeConnectors()` | v4-phase |
| `position()` | v4-phase |
| `setPositionFixed(bool)` | v4-phase |
| `positionFixed()` | v4-phase |
| `recommendedPosition()` | v4-phase |
| `makeRectangle(Router*, const Point&)` | internal |
| `preferOrthogonalDimension(size_t)` | internal |

`JunctionRefList` typedef — v4-phase.

---

## `viscluster.h` — v4-phase (cluster)

### `ClusterRef` (class, `AVOID_EXPORT`) — v4-phase

Header comment flags this as "currently experimental; you will likely
suffer a large performance hit when using it." Defer past phase 4
unless a concrete consumer asks.

Methods: constructor, `setNewPoly`, `id`, `polygon`,
`rectangularPolygon`, `router`, `makeActive`/`makeInactive` (last two
are internal plumbing).

---

## `hyperedge.h` — v4-phase (hyperedge)

### `HyperedgeNewAndDeletedObjectLists` (struct, `AVOID_EXPORT`) — v4-phase

Five public list fields:
`newJunctionList`, `newConnectorList`, `deletedJunctionList`,
`deletedConnectorList`, `changedConnectorList`.

### `HyperedgeRerouter` (class, `AVOID_EXPORT`) — v4-phase

| Member | Tag |
|--------|-----|
| `HyperedgeRerouter()` | v4-phase |
| `registerHyperedgeForRerouting(ConnEndList)` | v4-phase |
| `registerHyperedgeForRerouting(JunctionRef*)` | v4-phase |
| `newAndDeletedObjectLists(size_t index)` | v4-phase |
| `count()` | v4-phase |

Typedefs: `ConnEndList`, `ConnRefList`, `JunctionRefList`.

---

## `obstacle.h` — internal base class

`Obstacle` is not included directly by `libavoid.h`; it is pulled in
via `shape.h` and `junction.h`. The public accessors (`id()`,
`polygon()`, `router()`, `position()`, `setNewPoly()`, `routingBox()`,
`routingPolygon()`, `attachedConnectors()`) should be exposed on
`ShapeRef` and `JunctionRef` directly. No Python-visible `Obstacle`
class unless we discover we need polymorphism.

---

## Headers listed as out-of-scope

- **`graph.h`** — `EdgeInf`, `EdgeList`, `FlagList`, `ShapeList`.
  Visibility graph internals.
- **`vertices.h`** — `VertID`, `VertInf`, `VertexPair`, `EdgeInfList`,
  `VertIDProps`. Router-internal.
- **`visibility.h`** — `vertexVisibility()` free function.
  Router-internal.
- **`debug.h`** — `db_printf` and the `Avoid::LIBAVOID_DEBUG` macro.
  Development-only.
- **`timer.h`** — `Timer` class, `TimerIndex` enum. Gated behind
  `AVOID_PROFILE`; we do not compile with it.
- **`assertions.h`** — the `COLA_ASSERT` macro. Not exposed to users;
  relevant to build-notes.md.
- **`dllexport.h`** — the `AVOID_EXPORT` macro. Build-system detail.
- **`debughandler.h`** — `DebugHandler` base class. Used via
  `Router::setDebugHandler()`. Dev-only hook.
- **`makepath.h`, `obstacle.h` (beyond the ShapeRef/JunctionRef base
  methods above), `orthogonal.h`, `hyperedgeimprover.h`,
  `hyperedgetree.h`, `mtst.h`, `scanline.h`, `actioninfo.h`,
  `vpsc.h`** — internal routing algorithm implementation. Never
  touched by upstream tests. Do not wrap.

---

## Summary of v1 scope

The **v1-must-wrap** set is small enough to be built in phase 2 and
gives the 32 phase-2-translatable upstream tests a surface to run on.
It consists of:

- `geomtypes.h`: `Point`, `Vector` (alias), `Box`, `Polygon`,
  `Rectangle`, `PolyLine` (alias); `XDIM`, `YDIM`.
- `router.h`: enums `RouterFlag`, `RoutingParameter`/`PenaltyType`,
  `RoutingOption`; constants `zeroParamValue`,
  `chooseSensibleParamValue`; class `Router` with its routing-control,
  shape-and-connector management, transaction, and diagnostic methods.
- `shape.h`: `ShapeRef`.
- `connector.h`: `ConnType`, `ConnRef`.
- `connend.h`: `ConnDirFlag`, `ConnDirFlags`, `ConnEnd` (point and
  point+flags constructors).

The **v1-nice-to-have** set is small; wrap these opportunistically
when wrapping the surrounding class, and skip if they add friction.

Everything tagged **v4-phase**, **internal**, or **out-of-scope** is
deferred. Each v4 area (pin, junction, cluster, hyperedge,
checkpoint, callback) gets its own phase and its own decision record
per `CLAUDE.md` §5.
