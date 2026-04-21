# Phase 0 — Upstream test inventory and harness

This document is the result of reading the upstream `mjwybrow/adaptagrams`
repository before any wrapper code is written. It answers the first two
Phase 0 questions from `CLAUDE.md` §5:

1. What's actually in `cola/libavoid/tests/`?
2. What is the upstream test harness?

Sister documents:

- `api-surface.md` — public API catalog reachable from `libavoid.h`.
- `build-notes.md` — libavoid build-system details (sources, defines,
  platform-specific code).

## Upstream source reference

- Upstream repo: `https://github.com/mjwybrow/adaptagrams`
- Branch: `master` (there are no release tags on this project)
- Commit pinned for this research: **`840ebcff20dbba36ad03a2160edf7cbaf9859984`**
  (2025-10-29, "Merge pull request #84 from tczauderna/master")
- Libavoid source location within that repo: `cola/libavoid/`

All file paths below are relative to `cola/libavoid/` unless otherwise
noted. When the pinned commit is bumped in a later phase, this document
must be re-verified — counts, filenames, and disabled-test lists can
drift.

## Test directory overview

`cola/libavoid/tests/` contains:

- 83 C++ source files (one per test, `*.cpp`).
- `Makefile.am` — the automake test harness.
- `msctests/` — a parallel set of MSVC `.vcxproj` files, one per test,
  for Visual Studio users. These reference the same `.cpp` files.
- `output/` — a single-file directory containing `README.txt` that
  reads: "This directory is used to for output debug svg files from
  the testcases." It holds no checked-in expected output. It is an
  output destination, not a golden-file repository.

There is **no** `fixtures/` directory, no `.expected` files, no
`expected/` sibling directory, and no stdout transcript files anywhere
in the tests tree.

Of the 83 test `.cpp` files, **80 are enabled** in `Makefile.am`'s
`check_PROGRAMS` list. Three are disabled:

| Test | Reason it's disabled |
|------|----------------------|
| `corneroverlap01.cpp` | Listed in the Makefile comment as "Disabled tests" with no explanation. The file itself has a header comment "From cornertouching_libavoid-debug bug." |
| `unsatisfiableRangeAssertion.cpp` | Makefile comment: "really slow." |
| `reallyslowrouting.cpp` | Not listed in `check_PROGRAMS` and not mentioned in the disabled-tests comment. By name, presumably excluded for performance reasons. |

## Upstream test harness

### How tests run

The harness is **stock GNU Autotools `make check`**:

```
TESTS = $(check_PROGRAMS)
```

That one line in `cola/libavoid/tests/Makefile.am` tells automake to
treat every program in `check_PROGRAMS` as a test. `make check` from
the `cola/` build directory will:

1. Compile each listed `.cpp` into an independent executable, linking
   against `../libavoid/libavoid.la` (the libtool convenience archive).
2. Run each executable in turn with no arguments.
3. Record pass/fail as:
   - **pass** — exit code `0`
   - **fail** — any non-zero exit code (including crashes, signals, or
     explicit non-zero returns).
4. Summarize passes/fails/xfails in the final automake report.

There is no stdout/stderr comparison. There are no `.log` or
`.trs` files checked in (automake produces those at run time, but
they are build artifacts). A test is a freestanding executable that
is expected to exit `0`.

### How tests actually assert

Given the harness only looks at exit status, each test decides for
itself what "pass" means. Inspecting all 83 files gives three styles:

| Style | How pass is determined | Count |
|-------|------------------------|-------|
| **Smoke (exit 0)** | The `main()` constructs a scenario, calls `router->processTransaction()` and `router->outputDiagram("output/<name>")`, then `delete router; return 0;`. Pass = didn't crash, hit no internal assertion, and reached the `return 0`. | 78 |
| **Valid-paths check** | Returns `router->existsInvalidOrthogonalPaths()` as the exit code — a genuine functional check. | 3 (`validPaths01`, `validPaths02`, `hyperedgeRerouting01`) |
| **Inline assertion** | Contains explicit assertion calls in the test body. Failure aborts the process with non-zero exit. | 2 (`freeFloatingDirection01` with 1 `assert()`; `improveHyperedge05` with 7 `COLA_ASSERT(...)`) |

Consequences for our Python port:

- Most upstream tests are **crash regression tests**. They are
  scenarios that historically caused a segfault, hang, or internal
  assertion; passing only means libavoid still survives them. A
  straight translation gives us the same protection for the binding.
- The `outputDiagram()` call in most tests writes an SVG to
  `output/<test-name>.svg`. These SVGs are the only machine-readable
  artifact of a run. They are **not** checked into the repository and
  are not compared by the harness. They could be captured once as
  golden output for byte-level comparison in phase 3 (per `CLAUDE.md`
  §5 phase 3), at the cost of being brittle across libavoid versions
  and build environments.
- The three `existsInvalidOrthogonalPaths()` tests and the two
  inline-assertion tests give us something stronger than "didn't crash".
  Those translate cleanly into `assert`-style Python tests. Note that
  `improveHyperedge05` uses `COLA_ASSERT`, which becomes
  `static_cast<void>(0)` when `NDEBUG` is defined (see
  `build-notes.md`). Under the recommended MSVC build config this
  test silently degrades to a smoke test; the Python translation
  should re-assert the invariants unconditionally rather than
  follow the C++ debug-build gating.
- There is no stdout-vs-expected diffing to replicate. Anything we
  want to compare cross-language, we have to capture ourselves.

### What `outputDiagram()` produces

`Router::outputDiagram(name)` writes:

- `<name>.svg` — the debug SVG image
- `<name>.txt` — a text transcript of the instance

These are produced per-test into `tests/output/<name>.svg|.txt`. The
directory is cleared by `make clean`; the files are never checked in.
The text transcript is the more promising candidate for golden-file
comparison in phase 3 (SVGs contain floating-point coordinates that
may vary across compilers/platforms; the text dump is simpler).

## Per-test inventory

Legend for columns:

- **file** — source file under `cola/libavoid/tests/`.
- **enabled** — listed in `Makefile.am`'s `check_PROGRAMS`? (`n` means
  explicitly disabled or omitted upstream; we should treat these as
  low-priority and match upstream's decision.)
- **assertion style** — how pass/fail is decided (see above table).
- **features** — advanced libavoid features the test requires beyond
  the phase-2 core (`Router`, `ShapeRef`, `ConnRef`, `ConnEnd-from-point`,
  `Polygon`, `Rectangle`, `Point`, `PolyLine`). Features are detected by
  lexical scan — see "Detection caveats" below.
  - `pin` — `ShapeConnectionPin`, `CONNECTIONPIN_*`, or `ATTACH_POS_*`.
  - `junction` — `JunctionRef` constructor.
  - `hyperedge` — `HyperedgeRerouter` or `improveHyperedgeRoutes*` option.
  - `checkpoint` — `Checkpoint(...)` or `setRoutingCheckpoints`.
  - `callback` — `setCallback`.
  - (empty cell = uses only phase-2 core API.)
- **translatable** — can this be translated in phase 3 against the
  phase-2 wrapper alone?
  - `yes` — all used API is phase-2 core.
  - `partial` — needs one or more phase-4 features (pin / junction /
    hyperedge / checkpoint / callback). We can still translate the test
    body, but it will stay `pytest.skip` until the required feature is
    wrapped.
  - `no` — disabled upstream; not a translation target.

### Detection caveats

The features column is generated from a lexical `grep` of each file.
It is accurate for `ShapeConnectionPin`, `JunctionRef`, `HyperedgeRerouter`,
`Checkpoint(`, and `setCallback` — those are concrete library symbols.
Two caveats:

1. A test can use `ConnEnd(Point, ConnDirFlags)` without needing pins —
   `ConnDirFlags` is a phase-2-core concept. Tests in the `inlineoverlap`
   family use only direction flags on points and are genuinely phase-2.
2. The scan does not detect `Router::setTopologyAddon` or other exotic
   methods. Every upstream test in this list touches only routing
   features, which matches what the scan reports.

### Table

| file | enabled | assertion style | features | translatable |
|------|---------|-----------------|----------|--------------|
| 2junctions.cpp | y | exit0 | pin, junction | partial |
| buildOrthogonalChannelInfo1.cpp | y | exit0 | pin, junction | partial |
| checkpointNudging1.cpp | y | exit0 | checkpoint | partial |
| checkpointNudging2.cpp | y | exit0 | checkpoint | partial |
| checkpointNudging3.cpp | y | exit0 | checkpoint | partial |
| checkpoints01.cpp | y | exit0 | junction, checkpoint | partial |
| checkpoints02.cpp | y | exit0 | checkpoint | partial |
| checkpoints03.cpp | y | exit0 | checkpoint | partial |
| complex.cpp | y | exit0 | callback | partial |
| connectionpin01.cpp | y | exit0 | pin | partial |
| connectionpin02.cpp | y | exit0 | pin | partial |
| connectionpin03.cpp | y | exit0 | pin, junction | partial |
| connendmove.cpp | y | exit0 | pin | partial |
| corneroverlap01.cpp | n | exit0 | | no (disabled upstream) |
| endlessLoop01.cpp | y | exit0 | pin, junction, hyperedge | partial |
| example.cpp | y | exit0 | callback | partial |
| finalSegmentNudging1.cpp | y | exit0 | | yes |
| finalSegmentNudging2.cpp | y | exit0 | | yes |
| finalSegmentNudging3.cpp | y | exit0 | checkpoint | partial |
| forwardFlowingConnectors01.cpp | y | exit0 | pin | partial |
| freeFloatingDirection01.cpp | y | assert() | | yes |
| hola01.cpp | y | exit0 | pin | partial |
| hyperedge01.cpp | y | exit0 | junction, hyperedge | partial |
| hyperedge02.cpp | y | exit0 | pin, hyperedge | partial |
| hyperedgeLoop1.cpp | y | exit0 | pin, junction | partial |
| hyperedgeRerouting01.cpp | y | existsInvalidOrthogonalPaths | pin, junction, hyperedge | partial |
| improveHyperedge01.cpp | y | exit0 | pin, junction, hyperedge | partial |
| improveHyperedge02.cpp | y | exit0 | pin, junction, hyperedge | partial |
| improveHyperedge03.cpp | y | exit0 | pin, junction, hyperedge | partial |
| improveHyperedge04.cpp | y | exit0 | pin, junction, hyperedge | partial |
| improveHyperedge05.cpp | y | COLA_ASSERT() | pin, junction, hyperedge | partial |
| improveHyperedge06.cpp | y | exit0 | pin, junction, hyperedge | partial |
| infinity.cpp | y | exit0 | | yes |
| inline.cpp | y | exit0 | | yes |
| inlineoverlap01.cpp | y | exit0 | | yes |
| inlineoverlap02.cpp | y | exit0 | | yes |
| inlineoverlap03.cpp | y | exit0 | | yes |
| inlineoverlap04.cpp | y | exit0 | | yes |
| inlineoverlap05.cpp | y | exit0 | | yes |
| inlineoverlap06.cpp | y | exit0 | | yes |
| inlineoverlap07.cpp | y | exit0 | | yes |
| inlineoverlap08.cpp | y | exit0 | | yes |
| inlineOverlap09.cpp | y | exit0 | | yes |
| inlineOverlap10.cpp | y | exit0 | pin | partial |
| inlineOverlap11.cpp | y | exit0 | pin, junction, hyperedge | partial |
| inlineShapes.cpp | y | exit0 | pin | partial |
| junction01.cpp | y | exit0 | pin | partial |
| junction02.cpp | y | exit0 | junction | partial |
| junction03.cpp | y | exit0 | junction | partial |
| junction04.cpp | y | exit0 | pin, junction | partial |
| latesetup.cpp | y | exit0 | callback | partial |
| lineSegWrapperCrash1.cpp | y | exit0 | | yes |
| lineSegWrapperCrash2.cpp | y | exit0 | | yes |
| lineSegWrapperCrash3.cpp | y | exit0 | | yes |
| lineSegWrapperCrash4.cpp | y | exit0 | | yes |
| lineSegWrapperCrash5.cpp | y | exit0 | | yes |
| lineSegWrapperCrash6.cpp | y | exit0 | | yes |
| lineSegWrapperCrash7.cpp | y | exit0 | | yes |
| lineSegWrapperCrash8.cpp | y | exit0 | | yes |
| multiconnact.cpp | y | exit0 | callback | partial |
| node1.cpp | y | exit0 | pin, junction | partial |
| nudgeCrossing01.cpp | y | exit0 | checkpoint | partial |
| nudgeintobug.cpp | y | exit0 | | yes |
| nudgeold.cpp | y | exit0 | | yes |
| nudgingSkipsCheckpoint01.cpp | y | exit0 | checkpoint | partial |
| nudgingSkipsCheckpoint02.cpp | y | exit0 | checkpoint | partial |
| orderassertion.cpp | y | exit0 | | yes |
| orthordering01.cpp | y | exit0 | | yes |
| orthordering02.cpp | y | exit0 | | yes |
| overlappingRects.cpp | y | exit0 | | yes |
| penaltyRerouting01.cpp | y | exit0 | | yes |
| performance01.cpp | y | exit0 | | yes |
| reallyslowrouting.cpp | n | exit0 | | no (disabled upstream) |
| removeJunctions01.cpp | y | exit0 | pin, junction | partial |
| restrictedNudging.cpp | y | exit0 | | yes |
| slowrouting.cpp | y | exit0 | junction | partial |
| tjunct.cpp | y | exit0 | junction | partial |
| treeRootCrash01.cpp | y | exit0 | pin, junction, hyperedge | partial |
| treeRootCrash02.cpp | y | exit0 | pin, junction, hyperedge | partial |
| unsatisfiableRangeAssertion.cpp | n | exit0 | | no (disabled upstream) |
| validPaths01.cpp | y | existsInvalidOrthogonalPaths | pin | partial |
| validPaths02.cpp | y | existsInvalidOrthogonalPaths | pin | partial |
| vertlineassertion.cpp | y | exit0 | | yes |

### Summary counts

- 83 tests total; 80 enabled, 3 disabled upstream.
- **32 phase-2-translatable** (`translatable: yes`). These are the
  targets for phase 3's first pass.
- **48 blocked on phase-4 features** (`translatable: partial`),
  broken down by first blocking feature (a test is counted under its
  narrowest category; multi-feature tests fall into the last row):
  - `checkpoint` only: 9
  - `callback` only: 4
  - `pin` only (no junction / hyperedge / checkpoint / callback): 10
  - `junction` only (no pin / hyperedge / etc.): 4
  - multi-feature (e.g. pin+junction, pin+junction+hyperedge): 21
- 3 disabled upstream, do not translate.
- 5 tests have real assertions (3 `existsInvalidOrthogonalPaths`,
  2 `assert()`). The remaining 75 enabled tests are crash-regression
  smoke tests.

## What this implies for phases 2 and 3

1. **Phase 2 priority is unchanged.** The core wrapper (`Router`,
   geometry types, `ShapeRef`, `ConnRef`, `ConnEnd` from point) directly
   unlocks the 32 phase-2-translatable tests.
2. **Pin support is the most-unlocking phase-4 feature.** 29 of the
   48 partial tests use `ShapeConnectionPin` or the `CONNECTIONPIN_*` /
   `ATTACH_POS_*` constants. Wrapping pins alone — without junctions
   or hyperedges — is a big jump in coverage.
3. **Hyperedge support is the deepest tail.** 13 tests require
   `HyperedgeRerouter` or the hyperedge routing options.
4. **Callback support is small but sharp.** Only 4 tests exercise
   `setCallback`, but it's the hardest binding to write (GIL,
   reentrancy, lifetime) per `CLAUDE.md` §5 phase 4. Schedule it late.
5. **Golden-file strategy.** There are no upstream golden files. If we
   want byte-for-byte comparison, we generate our own from
   `outputDiagramText()` on a pinned libavoid commit. This should be a
   phase-3 decision recorded in `docs/decisions/` — the risk is
   tying our tests to a specific floating-point environment. A
   weaker but more portable option: assert on shapes of the returned
   `PolyLine` (point count, bounding box, orthogonality) rather than
   exact coordinates.
