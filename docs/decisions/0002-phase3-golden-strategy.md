# ADR 0002 — Phase 3: upstream test translation strategy

- **Status:** accepted
- **Date:** 2026-04-21
- **Applies to:** phase 3 of the roadmap in `CLAUDE.md` §5.

## Context

Phase 0's inventory (`docs/research/phase0.md`) established that the
upstream test harness is stock Autotools `make check`: each `.cpp` in
`cola/libavoid/tests/` compiles to a freestanding executable and passes
iff it exits `0`. There are no checked-in `.expected` files, no
stdout transcripts, no golden fixtures in the tree. 78 of 83 tests
are pure crash-regression (did `main()` reach `return 0`?); 5 carry
real functional assertions.

Phase 3 asks us to translate the 32 phase-2-translatable tests into
Python. `CLAUDE.md` §5 phase 3 additionally sketches a golden-file
workflow: run the upstream C++ binary once, save its output under
`tests/upstream/fixtures/`, and have Python tests assert equality
with `pytest.approx`.

We need to pick between two concrete paths:

- **A. Match upstream's own harness.** Each Python test replays the
  scenario and passes iff the router processes the transaction
  without raising. The 5 tests with real assertions port their
  assertion (`existsInvalidOrthogonalPaths`, `existsCrossings`,
  inline `assert` on `displayRoute().size()`, etc.).
- **B. Byte-level golden comparison.** Build the upstream C++
  binaries once, capture the text output of
  `Router::outputDiagramText()`, check it into `fixtures/`, and have
  the Python port assert its own output matches. (SVG output is even
  more fragile and is not a candidate — see `phase0.md`.)

## Decision

**Adopt option A for phase 3.**

Concretely:

1. Each translatable upstream test becomes a Python test under
   `tests/upstream/test_<name>.py`. The body constructs the same
   scenario (router flags, penalties, options, shapes, connectors)
   and calls `router.process_transaction()`.
2. The Python test passes iff:
   - the transaction processes without raising, **and**
   - every functional assertion the upstream test carries is
     translated — not dropped. Concretely:
     - tests whose `return` value is derived from
       `existsOrthogonalFixedSegmentOverlap()`,
       `existsOrthogonalTouchingPaths()`, `existsCrossings()`, or
       `existsInvalidOrthogonalPaths()` assert the same value
       from Python;
     - `freeFloatingDirection01`'s inline
       `assert(connRef239->displayRoute().size() == 4)` is preserved
       as a Python assertion. (Upstream uses plain `assert()`, which
       means it is compiled out under `NDEBUG`. Our translation
       re-asserts unconditionally, as `phase0.md` recommends.)
3. Tests tagged `translatable: partial` (needing pin / junction /
   hyperedge / checkpoint / callback support) are registered as
   `pytest.skip` with a reason string that names the missing
   feature. They are listed in `docs/api-coverage.md` so the skip
   is visible, not hidden.
4. No byte-level `fixtures/` directory is created in this phase.

Three public-API additions were required to make option A possible;
they were carried in the same commit as the translation. `Router`
gains `exists_orthogonal_segment_overlap`,
`exists_orthogonal_fixed_segment_overlap`,
`exists_orthogonal_touching_paths`, and `exists_crossings`. They
are one-line wrappers over public libavoid methods that
`api-surface.md` already tagged `v1-nice-to-have`; the `existsCrossings`
return type is `int` (a crossing count), the rest return `bool`.

## Rationale

- Option A matches what upstream treats as "passing" — the same
  signal library authors have been relying on for years. Our tests
  protect exactly the regressions the original tests protect.
- Option B's golden files are tied to a specific floating-point
  environment. The phase 0 analysis explicitly flagged cross-platform
  and cross-compiler drift as a risk. Producing a `.txt` file on
  Linux/gcc and asserting byte-equality on Windows/MSVC is very
  likely to fail on nudging tie-breaks, and loosening the comparison
  (pytest.approx across every coordinate in a text dump) is neither
  straightforward nor aligned with upstream's own posture of not
  shipping expected files.
- Option A makes the test suite meaningful the moment it is written.
  Option B needs an auxiliary build of the upstream `make check` tree
  before its fixtures exist, which is extra tooling that delivers no
  new signal over option A for most tests.
- We retain the option to add byte-level golden comparison *later*
  as an opt-in layer (e.g., `tests/upstream/golden/` with a separate
  CI job) if a concrete regression demands it. This ADR does not
  forbid a future ADR from adding it.

## Consequences

- 32 Python tests under `tests/upstream/test_<name>.py` are added,
  mirroring the 32 phase-2-translatable upstream tests 1:1 by name.
  Their structure mirrors the upstream `.cpp` line-for-line in the
  order shapes and connectors are registered; floats are preserved
  verbatim.
- `scripts/translate_upstream.py` generates these files from the
  upstream `.cpp` sources. Re-running it on a bumped libavoid commit
  regenerates the tests; drift between upstream edits and our ports
  is made visible by a git diff on the generated files, not by
  silent rot. The script is the mechanical part of this phase; the
  hand-written part is this ADR and the per-test assertion mapping
  encoded in the script.
- `scripts/generate_golden.py` is not produced in this phase. If a
  later phase adds golden comparison, it will add that script
  alongside a new ADR.
- `docs/api-coverage.md` is authored this phase and lists every
  upstream test with status (`passing`, `skipped`, or
  `blocked-needs-<feature>`) and a short reason.
- The 48 `translatable: partial` tests become `pytest.skip` stubs
  rather than not existing at all. Writing the stubs now means
  phase-4 work can un-skip tests as features are wrapped, without
  having to rediscover which tests cover which feature.
- The translator is tied to the pattern of upstream's existing
  `.cpp` files (a constrained subset of C++: `Polygon poly(N);
  poly.ps[i] = Point(...); new ShapeRef(router, poly, id);` etc.).
  If upstream starts writing tests in a new idiom, the translator
  will need extending. That is acceptable — upstream's test style
  has been stable for many years.

## Alternatives considered

- **Manual translation, no script.** Rejected: the largest test
  (`performance01`) is 7665 lines of poly/point boilerplate, and the
  eight `lineSegWrapperCrash*` tests are 1884 lines each. Hand
  translation is error-prone and loses the bump-regen guarantee.
- **Keep the 48 partial tests unwritten.** Rejected: we would lose
  the phase-4 unlock visibility. Skipped stubs with explicit reason
  strings make the feature gap explorable via `pytest -v`.
- **Run upstream's C++ tests via a subprocess.** Rejected as not
  actually a translation: the goal is to exercise the Python binding,
  not the upstream binary.
