# CLAUDE.md — libavoid Python bindings project

This file guides an AI coding assistant (Claude Code or similar) working on this
repository. Read it fully before making changes. When in doubt, prefer asking a
clarifying question over guessing.

## 1. What this project is

A Python package that exposes the C++ library **libavoid** (from the
[mjwybrow/adaptagrams](https://github.com/mjwybrow/adaptagrams) project, under
`cola/libavoid/`) as a pip-installable wheel for Linux and Windows.

**Goal in one sentence:** Let Python code do orthogonal and polyline connector
routing by importing a module, the same way libavoid-js lets JavaScript code
do it — without the user needing a C++ compiler installed.

**Non-goal:** This package is **not** a Visio integration, not a diagram tool,
not a GUI. It is a thin, domain-agnostic wrapper over libavoid. It must have
zero dependencies on pywin32, Excel, Visio, or anything Windows-specific.

**Downstream consumer:** A separate project (not in this repo) uses these
bindings to compute connector routes for Visio diagrams. That project is
Windows-only, pywin32-based, and outside the scope of this repo. When making
design choices, prefer keeping the binding general-purpose over optimizing
for that one consumer.

**Distribution posture:** This package is **published publicly** to GitHub
(source) and PyPI (wheels). It is not a private, internal, or company-only
artifact. Every design decision — naming, API shape, dependency choice,
license metadata, commit hygiene, CI logs — should be made assuming strangers
will read it, audit it, fork it, and report issues. Do not embed company
names, internal URLs, private paths, personal email addresses, or anything
that would be awkward in public.

## 2. Working agreements for the AI assistant

- **Ask before inventing API.** The wrapped API should mirror libavoid's C++
  API as closely as Python idioms allow. Do not invent novel method names,
  rearrange classes, or add convenience helpers without a written decision
  recorded in `docs/decisions/`.
- **Do not fabricate facts about libavoid.** If you are unsure whether a
  method exists, what a parameter means, or what a return type is, read
  the actual headers in `vendor/adaptagrams/cola/libavoid/` rather than
  guessing. The headers are the source of truth.
- **Check the real repo before citing it.** Directory listings, test counts,
  file names — verify by cloning and running `ls`, not by searching the web.
  The adaptagrams project has no releases; `master` branch is the reference.
- **Honest failure reporting.** If a test fails, a build breaks, or a
  platform doesn't work, say so clearly. Do not silently skip, do not mark
  broken things as passing, do not `xfail` without a written reason.
- **Incremental changes.** Prefer small PRs that do one thing. The wrapper
  grows in layers (geometry types → router → shapes → connectors → routing
  parameters → advanced features), not in one big sweep.
- **No AI slop in commits.** Commit messages describe what changed and why,
  not "implemented feature X with best practices." No emoji, no marketing
  language, no generated changelog prose.

## 3. Technical constraints (non-negotiable)

- **Language & binding toolchain:** Python ≥ 3.11, C++17, **pybind11** for
  bindings, **scikit-build-core** as the PEP 517 build backend, **CMake** as
  the build system. Rationale: modern, well-supported, produces wheels
  cleanly via cibuildwheel. Do not use SWIG. Do not use Boost.Python.
- **Target platforms:** Linux x86_64 (manylinux_2_28 or newer) and Windows
  AMD64. macOS and ARM are explicitly out of scope for v1; do not add them
  without a written decision.
- **Python versions:** 3.11, 3.12, 3.13. Drop older ones to keep the wheel
  matrix small.
- **libavoid source:** Vendored as a **git submodule** at
  `vendor/adaptagrams/`, pinned to a specific commit. Do not copy source
  files into the repo. Do not depend on a system-installed libavoid.
- **No runtime dependencies** other than Python itself. The wheel is
  self-contained: libavoid is statically linked into the extension module.
- **License:** The package is distributed under **LGPL-2.1-or-later**, matching
  libavoid. See section 12 for the full story, the static-linking
  obligations, and what we are required to ship. Do not add
  GPL-incompatible code. Record any new dependency's license in
  `THIRD_PARTY_NOTICES.md`.

## 4. Repository layout (target state)

```
.
├── CLAUDE.md                   # this file
├── README.md                   # user-facing, install & quickstart
├── LICENSE                     # LGPL-2.1-or-later
├── THIRD_PARTY_NOTICES.md      # libavoid notice + any others
├── pyproject.toml              # scikit-build-core config, metadata
├── CMakeLists.txt              # top-level CMake
├── src/
│   ├── libavoid_py/            # Python package (pure-Python parts)
│   │   ├── __init__.py
│   │   └── py.typed
│   └── bindings/               # pybind11 C++ sources
│       ├── module.cpp          # PYBIND11_MODULE entry point
│       ├── geometry.cpp        # Point, Polygon, Rectangle, PolyLine
│       ├── router.cpp          # Router, RouteType, RoutingParameter
│       ├── shape.cpp           # ShapeRef
│       ├── connector.cpp       # ConnRef, ConnEnd
│       └── ...                 # one file per logical area
├── tests/
│   ├── conftest.py
│   ├── unit/                   # pure Python unit tests of the wrapper
│   ├── scenarios/              # hand-crafted routing scenarios
│   └── upstream/               # translations of libavoid's own tests
│       ├── test_example.py
│       └── fixtures/           # golden output data
├── stubs/
│   └── libavoid_py.pyi         # type stubs for IDEs
├── vendor/
│   └── adaptagrams/            # git submodule
├── docs/
│   ├── decisions/              # ADRs (architecture decision records)
│   ├── api-coverage.md         # what's wrapped, what isn't
│   └── research/               # phase 0 findings
├── scripts/
│   ├── build_local.sh          # Linux dev build helper
│   ├── generate_golden.py      # run C++ tests, save outputs for Python tests
│   └── check_coverage.py       # report wrapped API surface vs. upstream
└── .github/
    └── workflows/
        ├── build.yml           # cibuildwheel on push/PR
        └── release.yml         # publish on tag
```

## 5. Phased plan

Work in phases. Do not start phase N+1 until phase N is reviewed and closed.

### Phase 0 — Research (deliverable: `docs/research/phase0.md`)

Before writing a single line of binding code, find out:

1. **What's actually in `cola/libavoid/tests/`.** Clone adaptagrams, list the
   directory, categorize each file: is it a `main()` program? Does it have
   a `.expected` reference file? What API does it exercise? Produce a table
   in `docs/research/phase0.md` with columns: file, purpose, API surface
   used, has-expected-output, translatable-to-python (yes/no/partial).
2. **What the test harness is.** Does the upstream build run tests via
   `make check`? How are pass/fail determined? Is there stdout-vs-expected
   diffing? Transcribe the mechanism.
3. **What the public API surface looks like in headers.** Read
   `libavoid/libavoid.h` and its includes. Produce a catalog in
   `docs/research/api-surface.md` listing every public class, every public
   method, every enum value, with a 1-line description. Mark each as
   "v1-must-wrap", "v1-nice-to-have", or "out-of-scope".
4. **Build system specifics.** What source files compile into libavoid?
   What preprocessor defines does it need? Does it have platform-specific
   code paths (especially for Windows/MSVC)? Record in
   `docs/research/build-notes.md`.

Only after phase 0 is merged does phase 1 begin.

### Phase 1 — Skeleton wheel

Deliverable: a wheel that installs, imports, and exposes a single dummy
function.

1. `pyproject.toml` with scikit-build-core backend, project metadata, PEP 621
   compliance.
2. Top-level `CMakeLists.txt` that finds Python, pybind11, and adds the
   extension module.
3. `src/bindings/module.cpp` with `PYBIND11_MODULE` defining a single
   function `version() -> str` that returns the libavoid git commit hash
   the wheel was built from.
4. `vendor/adaptagrams` submodule added, pinned to a specific commit.
5. libavoid built as a static library by CMake (replicating its automake
   build — compile the .cpp files in `cola/libavoid/*.cpp`). Use CMake's
   `add_library(libavoid STATIC ...)`. Do **not** call out to automake.
6. A single smoke test in `tests/unit/test_smoke.py` that imports the
   module and calls `version()`.
7. GitHub Actions workflow using cibuildwheel that builds wheels for
   Linux (manylinux_2_28) and Windows on every push. Wheels uploaded as
   CI artifacts.
8. Successful CI run on both platforms, downloaded wheel installs cleanly
   on a stock Windows Python.

### Phase 2 — Core API (deliverable: minimum viable wrapper)

In this order, one PR each:

1. Geometry types: `Point`, `Polygon`, `Rectangle`, `PolyLine`. Include
   `__repr__`, equality, iteration where natural. Test round-trip: construct
   in Python, read attributes back, they match.
2. `Router` with `RouteType` enum (`PolyLineRouting`, `OrthogonalRouting`)
   and `RoutingParameter` / `RoutingOption` enums. Expose
   `set_routing_parameter`, `set_routing_option`, `process_transaction`.
3. `ShapeRef` — rectangle and polygon constructors, takes a `Router`.
   Lifetime: router owns shapes (per libavoid's C++ semantics); the Python
   wrapper must mirror this without segfaults. Write explicit lifetime
   tests (create shape, delete Python reference, router still works).
4. `ConnRef` — construct with `ConnEnd` at point or shape. Expose
   `display_route()` returning a `PolyLine`.
5. `ConnEnd` — from point, from shape (dynamic attachment). Skip connection
   pins for now.

After each of these, a matching set of Python unit tests under `tests/unit/`.

### Phase 3 — Upstream test translation

Using the phase 0 catalog:

1. For each upstream test marked "translatable", write a Python equivalent
   under `tests/upstream/test_<name>.py`.
2. Generate golden outputs by running the upstream C++ test once (script in
   `scripts/generate_golden.py`). Save under `tests/upstream/fixtures/`.
3. Python test asserts equality (or `pytest.approx` with tight tolerance)
   against the golden file.
4. Track translation progress in `docs/api-coverage.md` with a table:
   upstream test name, status (passing / skipped / blocked), reason if not
   passing.
5. Goal: every upstream test that uses only phase-2 wrapped API passes.
   Tests that need unwrapped features are explicitly skipped with a clear
   message, not hidden failures.

### Phase 4 — Advanced features (as needed)

Only add if required by downstream consumer or upstream tests blocked on it:

- Junctions (`JunctionRef`)
- Connection pins (`ShapeConnectionPin`)
- Clusters (`ClusterRef`)
- Checkpoints
- Hyperedges
- Callbacks (C++ `setCallback` → Python callable; be careful about GIL
  and object lifetime here, this is the hardest part of the binding)

Each of these gets its own phase with its own decision record.

## 6. API design principles

- **Pythonic naming:** C++ `camelCase` methods become Python `snake_case`.
  `processTransaction()` → `process_transaction()`. `displayRoute()` →
  `display_route()`.
- **Enums are `enum.IntEnum` subclasses**, not bare integers. Users write
  `RouteType.Orthogonal`, not `1`.
- **Exceptions, not return codes.** Map libavoid error conditions to
  Python exceptions (`ValueError`, `RuntimeError`). Never return `None`
  to signal failure.
- **Ownership is explicit.** libavoid passes ownership of `ShapeRef` and
  `ConnRef` to the `Router`. The Python wrapper must track this: do not
  allow double-free, do not allow use-after-free if the router is deleted
  first. Use `py::keep_alive` or store Python references on the router to
  model this.
- **Type stubs (`.pyi`) are a first-class deliverable**, not an
  afterthought. Users should get autocomplete and `mypy` coverage from
  day one.
- **Resist adding convenience helpers** until there is a concrete user
  asking for them. Helpers accumulate maintenance burden. A thin wrapper
  is a good wrapper.

## 7. Testing

- **Framework:** pytest. No unittest-style `TestCase` classes.
- **Layout:** `tests/unit/` for wrapper correctness, `tests/scenarios/` for
  hand-written routing cases, `tests/upstream/` for translated upstream
  tests.
- **Golden data** lives next to the test that uses it, under
  `tests/upstream/fixtures/`. One file per test, named after the test.
- **Floating-point comparisons** use `pytest.approx` with an explicit
  tolerance (suggest 1e-9 absolute for exact-same-platform reproduction,
  looser for cross-platform). Record the rationale in the test if a
  non-default tolerance is needed.
- **Cross-platform discrepancies** are tracked: if a test produces
  different output on Linux vs Windows, do **not** just loosen the
  tolerance — open a decision record, investigate whether libavoid itself
  is nondeterministic on the input, and only loosen if the upstream C++
  tests show the same behavior.
- **Coverage:** aim for >90% line coverage of `src/bindings/` exercised
  by the full test suite. `coverage.py` for Python-side coverage;
  `gcov`/`llvm-cov` optional for C++ side.
- **CI runs all tests on Linux and Windows.** A passing Linux run is not
  a green build.

## 8. Build & distribution

- **Local Linux dev build:** `pip install -e . --config-settings=build-dir=build`
  (scikit-build-core's editable mode). Rebuild C++ on changes via
  `scripts/build_local.sh`.
- **Wheel build:** `cibuildwheel` in GitHub Actions. Config in
  `pyproject.toml` under `[tool.cibuildwheel]`.
- **manylinux:** use `manylinux_2_28` base images. Do not use
  `manylinux2014` — it's old enough to cause C++17 header issues.
- **Windows:** MSVC 2022 (VS 17.x), x64 only.
- **Publishing:** to PyPI on tagged releases (`release.yml`). Use OIDC
  trusted publishing, no long-lived PyPI tokens in secrets.

## 9. Documentation

- **README.md:** installation (`pip install libavoid-py`), 20-line quickstart,
  link to upstream libavoid for algorithm details.
- **API reference:** generated from docstrings via Sphinx + autodoc or
  pdoc. Docstrings live in the pybind11 code (`.def("name", &func, "docstring")`).
- **Every public method has a docstring.** No exceptions. If you don't
  know what a method does well enough to write a docstring, you don't
  know it well enough to wrap it.
- **Decision records** (ADRs) under `docs/decisions/` for any non-obvious
  choice. Format: one numbered markdown file per decision, sections
  "Context / Decision / Consequences". These are the project's memory.

## 10. What to do when stuck

In order:

1. Read the relevant libavoid header in `vendor/adaptagrams/cola/libavoid/`.
2. Read the corresponding `.cpp` to see how it's used internally.
3. Read the upstream test that exercises this feature (phase 0 catalog
   will tell you which one).
4. Check how libavoid-js wraps the same feature (https://github.com/Aksem/libavoid-js)
   — they've solved many of the same cross-language problems.
5. If still stuck, write a failing test that demonstrates the confusion
   and open an issue. Do not guess and commit.

## 11. Out of scope for this repository

Repeating because drift is the main risk:

- Visio integration. Belongs in the downstream tool's repo.
- Excel reading. Not a routing concern.
- pywin32, COM, Windows-only code. Forbidden in this package.
- Auto-layout of shape positions. libavoid routes connectors given shape
  positions; it does not compute shape positions. Positioning belongs
  elsewhere.
- GUI. There is no GUI here, not even a CLI. Just a library.

## 12. License details and what we must ship

### 12.1 What adaptagrams actually says

The file `cola/LICENSE` in the adaptagrams repository contains the verbatim
text of the **GNU Lesser General Public License, Version 2.1, February 1999**
(published by the Free Software Foundation). That file by itself does not
decide whether the project is "LGPL-2.1-only" or "LGPL-2.1-or-later" — the
license text is identical in both cases; the difference lives in the
per-source-file copyright headers.

The adaptagrams source file headers (for example in
`cola/libavoid/router.cpp`) carry the standard FSF boilerplate:

> This library is free software; you can redistribute it and/or modify it
> under the terms of the GNU Lesser General Public License as published by
> the Free Software Foundation; either version 2.1 of the License, or
> (at your option) any later version.

The **"or (at your option) any later version"** phrase is what makes the
correct SPDX identifier `LGPL-2.1-or-later` and not `LGPL-2.1-only`. Do not
change this identifier without re-reading the source headers and confirming
they still say "or later".

Adaptagrams is additionally **dual-licensed**: Monash University offers a
commercial license for a fee. That path is not relevant to this project and
we do not invoke it; we distribute under the LGPL terms only.

### 12.2 Which license applies to the Python wrapper code

Two choices make sense:

- **LGPL-2.1-or-later** for the whole package (wrapper + vendored libavoid).
  Simplest. No ambiguity about combined-work obligations. Recommended default.
- A more permissive license (MIT / BSD / Apache-2.0) for the wrapper code
  alone, while the bundled libavoid stays LGPL. Legally this is fine — LGPL
  permits this combination — but it complicates the distribution story
  because recipients still need the LGPL obligations satisfied for libavoid.

Decision: the wrapper is **LGPL-2.1-or-later**. Recorded as an ADR under
`docs/decisions/`. Revisit only if a concrete reason appears.

### 12.3 Static linking obligations

We statically link libavoid into the Python extension module
(`libavoid_py*.so` on Linux, `libavoid_py*.pyd` on Windows). This matters
because LGPL-2.1 section 6 requires that recipients of a statically-linked
distribution be able to **relink the executable against a modified version
of the library**.

For a Python wheel, satisfying this requires we ship (or make readily
available) all of the following:

1. **The LGPL-2.1 license text.** Include `LICENSE` (or `COPYING.LESSER`)
   at the repository root. The wheel's metadata license field must say
   `LGPL-2.1-or-later`.
2. **Attribution notice.** A clear statement that the wheel contains
   libavoid, who holds the copyright, and a pointer to the original source.
   Goes in `THIRD_PARTY_NOTICES.md` at the repo root and is bundled into the
   wheel under the package's `.dist-info/` metadata.
3. **Access to libavoid source at the exact commit we built against.**
   Three ways to satisfy this, in decreasing order of preference:
   - **Best:** A `vendor/adaptagrams` git submodule pinned to a specific
     commit hash. Anyone with the repo has the source. This is our default.
   - **Acceptable:** A written offer in `README.md` pointing to the
     upstream commit URL (`https://github.com/mjwybrow/adaptagrams/tree/<hash>`)
     valid for at least three years.
   - **Avoid:** Shipping the libavoid source inside the wheel itself. Works
     but bloats the wheel for no gain.
4. **The object files or equivalent** needed to relink against a modified
   libavoid. The practical interpretation accepted by the community is:
   ship the wrapper source (the pybind11 `.cpp` files) and the build system
   (`CMakeLists.txt`, `pyproject.toml`) so a user can rebuild with their
   modified libavoid. Our open-source repo satisfies this by default; the
   `README.md` must point at it.
5. **The modified libavoid source, if we modified it.** We **do not modify
   libavoid** in this project — we vendor upstream and build it as-is. If a
   patch ever becomes necessary, it must live as a separate file under
   `patches/` and be applied during build, not squashed into the vendored
   source tree, so what we changed is obvious.

### 12.4 What downstream users of the wheel can do

LGPL-2.1 is specifically designed to permit closed-source programs to use
the library. Consequences for anyone who `pip install libavoid-py`:

- They can import it from a proprietary/closed-source Python application.
  That application does **not** become LGPL.
- They must preserve the LGPL notices that come with the wheel (our
  `THIRD_PARTY_NOTICES.md` and license file).
- If they redistribute the wheel (e.g., bundling it into their own
  installer), they must also pass along the license, notices, and source
  availability.
- They cannot sublicense libavoid under a more restrictive license.

Our README should state this clearly in a short "License" section so users
do not have to read LGPL to understand what they can do.

### 12.5 Concrete files to produce

At repository root:

- `LICENSE` — LGPL-2.1 text, verbatim from
  `https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt`.
- `THIRD_PARTY_NOTICES.md` — section for libavoid with copyright holder
  (Monash University / Michael Wybrow), upstream URL, exact commit hash,
  license, and a short summary. Additional sections added if we ever pick
  up other third-party code.
- `README.md` — section titled "License" linking to `LICENSE`, naming
  `LGPL-2.1-or-later`, and the written offer (see 12.3.3).

In `pyproject.toml`:

- `license = "LGPL-2.1-or-later"` using PEP 639 license expression syntax.
- `license-files = ["LICENSE", "THIRD_PARTY_NOTICES.md"]`.

### 12.6 What you must never do

- Strip LGPL notices from any file.
- Change the SPDX identifier without re-reading source headers.
- Static-link libavoid and then ship a closed-source wheel with no source
  access path. That violates section 6 of the LGPL.
- Claim a different license in metadata than what the source headers say.
- Assume "LGPL is just like MIT but longer." It is not. Read the text.

### 12.7 Public release checklist (GitHub + PyPI)

This package is published publicly. Before any release — and especially
before the first release — verify every item on this list. It is the
practical distillation of everything above, in the order a release should
be checked.

**Repository (before the first push to the public remote):**

- [ ] `LICENSE` at repo root: verbatim LGPL-2.1 text from
      `https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt`.
- [ ] `THIRD_PARTY_NOTICES.md` at repo root, with an entry for libavoid
      containing: copyright holder (Michael Wybrow, Monash University),
      upstream URL (`https://github.com/mjwybrow/adaptagrams`), the exact
      commit hash the submodule is pinned to, and the license
      (`LGPL-2.1-or-later`).
- [ ] `README.md` contains:
  - A one-line description.
  - Install command (`pip install <package-name>`).
  - A 20-line quickstart example.
  - A "License" section naming `LGPL-2.1-or-later` and linking to `LICENSE`.
  - A sentence stating this is an **unofficial** wrapper, not maintained by
    the libavoid authors.
  - An "Acknowledgments" or "Citation" section crediting Wybrow, Marriott,
    and Stuckey and pointing to their routing papers listed on
    `https://www.adaptagrams.org/documentation/libavoid.html`.
- [ ] `CONTRIBUTING.md` stating contributions are accepted under
      `LGPL-2.1-or-later`.
- [ ] `vendor/adaptagrams/` is a **git submodule**, not a copy. The pinned
      commit hash is recorded in `THIRD_PARTY_NOTICES.md`.
- [ ] No edits to anything under `vendor/`. Any needed patches live under
      `patches/` and are applied at build time.
- [ ] No company names, internal URLs, private paths, personal email
      addresses, or secrets anywhere in the repo history. Run a final
      `git log --all -p | grep -iE '<internal-domain>|<personal-email>'`
      equivalent before the first push.

**Package name:**

- [ ] Check PyPI web UI for the chosen name. If taken, pick another.
- [ ] Check that the name does not imply official endorsement (e.g. avoid
      `official-libavoid-bindings`). Derivative forms (`libavoid-py`,
      `pylibavoid`) are fine as long as the README clarifies "unofficial".
- [ ] Once picked, register the name on PyPI early with a 0.0.0 placeholder
      if useful, to prevent squatting.

**`pyproject.toml` (PEP 621 + PEP 639):**

- [ ] `[project] license = "LGPL-2.1-or-later"` — SPDX expression, not a
      freeform string, not `LGPL-2.1+` (old style).
- [ ] `[project] license-files = ["LICENSE", "THIRD_PARTY_NOTICES.md"]`.
- [ ] **No** `License :: OSI Approved :: ...` classifier. Modern PyPI
      expects PEP 639 `license` or classifiers, not both — mixing produces
      upload errors.
- [ ] `[project] authors` lists the binding maintainers, **not** the
      libavoid authors. Crediting upstream belongs in README and
      `THIRD_PARTY_NOTICES.md`, not in package metadata.
- [ ] `[project.urls]` includes at least `Homepage`, `Source`, and
      `Issues` pointing at the public GitHub repo.
- [ ] `[project] description` is one line that makes sense to a PyPI
      visitor who has never heard of libavoid.
- [ ] `[project] readme = "README.md"` — the README renders as the PyPI
      project description.

**GitHub settings (once the repo is public):**

- [ ] GitHub's license detector shows "GNU Lesser General Public License
      v2.1" in the repo sidebar. If it doesn't, the `LICENSE` file has been
      altered — revert to the verbatim FSF text.
- [ ] Repository "About" section mentions that this is a Python wrapper
      for libavoid.
- [ ] Repository topics include `python`, `python-bindings`, `libavoid`,
      `routing`, `lgpl`.
- [ ] Default branch is protected: no force-push, CI must pass before
      merge.
- [ ] Dependabot / Renovate enabled for build dependencies (pybind11,
      scikit-build-core, cibuildwheel).

**Pre-release verification:**

- [ ] CI builds Linux and Windows wheels successfully.
- [ ] Test suite passes on both platforms in CI.
- [ ] Locally install the built Windows wheel on a stock Python with no
      compiler; confirm `import libavoid_py` and a basic routing example
      work.
- [ ] `python -m twine check dist/*.whl dist/*.tar.gz` reports no errors.
- [ ] Upload to **TestPyPI first**, install from there, confirm the package
      page looks correct (license shown, README rendered, URLs clickable).
- [ ] Only then publish to real PyPI. Use PyPI **trusted publishing (OIDC)**
      from GitHub Actions. Do not use long-lived PyPI API tokens in
      repository secrets.

**Ongoing obligations after first release:**

- [ ] Respond to issues in a timely manner, or mark the repo as
      unmaintained honestly. A stale package with an unanswered security
      advisory is worse than a clearly-unmaintained one.
- [ ] Keep `THIRD_PARTY_NOTICES.md` in sync when the libavoid submodule
      commit is bumped. Each bump is a PR that updates both the submodule
      pointer and the commit hash in the notices file.
- [ ] On any release that changes the libavoid commit, note it in
      `CHANGELOG.md`.
- [ ] If a contributor opens a PR, confirm they understand the LGPL
      licensing of their contribution before merging (a PR template
      checkbox is enough).

**Courtesy (not required, recommended):**

- [ ] Open an issue on `mjwybrow/adaptagrams` announcing the wrapper.
      Short, polite, one paragraph, link to repo. Upstream may link back;
      users may find you faster.
- [ ] If the package gets real usage, consider adding a `SECURITY.md`
      explaining how to report vulnerabilities.

---

**Last review:** when starting work, read sections 2, 3, and 11 at minimum.
Update this file when project conventions change; keep it honest.
