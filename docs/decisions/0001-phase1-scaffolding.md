# ADR 0001 — Phase 1 scaffolding: build toolchain, licensing, versioning

- **Status:** accepted
- **Date:** 2026-04-21
- **Applies to:** phase 1 of the roadmap in `CLAUDE.md` §5.

## Context

Phase 1's deliverable is a wheel that installs, imports, and exposes a
single `version() -> str` function. Before writing any binding code we
had to decide on the build backend, how libavoid's sources get compiled
and linked, how the pinned commit travels from `vendor/adaptagrams` all
the way to `libavoid_py.version()`, and how the LGPL-2.1 obligations
are satisfied at the package boundary. Phase 0's research
(`docs/research/phase0.md`, `api-surface.md`, `build-notes.md`)
supplied the facts this ADR decides from; it does not revisit them.

## Decisions

1. **Build backend: scikit-build-core + CMake, with pybind11.**
   `pyproject.toml` declares `scikit-build-core>=0.10` and
   `pybind11>=2.13` as build requirements. Rationale: modern PEP 517
   backend, native CMake driver, clean cibuildwheel integration. We
   reject SWIG and Boost.Python per `CLAUDE.md` §3. Minimum CMake 3.18
   is enforced in the top-level `CMakeLists.txt`.

2. **libavoid is compiled as a static library inside the extension.**
   The CMake target `libavoid_static` enumerates the 23 `.cpp` files
   listed in `cola/libavoid/Makefile.am`'s `libavoid_la_SOURCES`. The
   list is explicit (no globbing) so any upstream source addition or
   removal becomes a visible diff on a submodule bump. The pybind11
   extension `_core` links `libavoid_static` with `PRIVATE` linkage;
   the static archive is not installed or exposed to users.

3. **C++ standard: C++17 for both libavoid and the binding.** libavoid
   itself requires only C++11 (checked in phase 0), but mixing object
   files at different standards is asking for subtle ABI issues, so we
   compile everything at C++17. `CMAKE_CXX_EXTENSIONS=OFF` so we do
   not depend on GCC extensions.

4. **MSVC build configuration.** Set
   `LIBAVOID_NO_DLL` (flatten `AVOID_EXPORT` to empty when
   static-linking) and `NDEBUG` (avoid the `<afx.h>`/MFC branch in
   `assertions.h`) on `libavoid_static` as `PUBLIC` compile
   definitions, so the binding target inherits them. Rationale in
   `docs/research/build-notes.md` §"Preprocessor defines that matter".
   Consequence: MSVC Debug configurations are not supported; we build
   `Release` wheels only. If Debug-with-assertions is ever needed,
   revisit via `USE_ASSERT_EXCEPTIONS` plus a vendored
   `libvpsc/assertions.h`.

5. **Position-independent code on non-MSVC via
   `POSITION_INDEPENDENT_CODE ON` on the target**, not raw `-fPIC`
   flags. CMake emits the right flag per toolchain and the concept is
   a no-op for MSVC.

6. **How `version()` learns the commit hash.** At CMake configure
   time we resolve the hash in this order:
   1. `git -C vendor/adaptagrams rev-parse HEAD` when git is available
      and the submodule is checked out.
   2. Read `LIBAVOID_COMMIT.txt` at the repo root when git is not
      available (this is how sdist installs work — the file is shipped
      in the sdist, the `.git` is not).
   3. Fail with `message(FATAL_ERROR ...)` if neither produces a value.
      We refuse to build a wheel whose advertised version is "unknown".
   The resolved hash is injected as `-DLIBAVOID_COMMIT_HASH="..."` on
   the binding target and returned verbatim by `version()`. CI enforces
   that the submodule HEAD and `LIBAVOID_COMMIT.txt` agree.

7. **Distribution name `libavoid-py`, import name `libavoid_py`,
   extension module `libavoid_py._core`.** Distribution matches the
   install command advertised in `CLAUDE.md` §9 and §12.5. The
   `_core` extension stays private: `libavoid_py/__init__.py`
   re-exports its public surface, which means future pure-Python
   helpers can co-exist without breaking `import libavoid_py`.

8. **License: LGPL-2.1-or-later for the whole package.** Per
   `CLAUDE.md` §12.2. `pyproject.toml` uses PEP 639 syntax
   (`license = "LGPL-2.1-or-later"`, `license-files = ["LICENSE",
   "THIRD_PARTY_NOTICES.md"]`); no legacy `License ::` classifier.
   The `LICENSE` file is the verbatim LGPL-2.1 text copied from
   `vendor/adaptagrams/cola/LICENSE`, which matches the FSF canonical
   text.

9. **sdist contents.** The adaptagrams submodule is not tracked by
   the parent repo's git index, so scikit-build-core's default
   (git-based) sdist logic would miss libavoid's sources. We opt into
   explicit inclusion in `[tool.scikit-build]`: `sdist.include`
   whitelists `vendor/adaptagrams/cola/libavoid/**.cpp|.h` plus the
   upstream `LICENSE`, `AUTHORS`, and `README.md`. `sdist.exclude`
   drops sibling libraries (`libcola`, `libvpsc`, etc.) and the
   83-file test tree we do not compile.

10. **CI targets.** `.github/workflows/build.yml` runs cibuildwheel
    on `ubuntu-latest` (manylinux_2_28) and `windows-latest`, for
    CPython 3.11 / 3.12 / 3.13 (non-free-threaded), architecture
    x86_64 / AMD64. Tests run inside cibuildwheel's `test-command`
    step, so a wheel that passes CI actually imports and passes the
    smoke test. We skip musllinux and 32-bit targets; they are out of
    scope per `CLAUDE.md` §3. macOS and ARM stay out of scope.

## Consequences

- A submodule bump is a three-file change: `vendor/adaptagrams`
  pointer, `LIBAVOID_COMMIT.txt`, and the commit hash recorded in
  `THIRD_PARTY_NOTICES.md`. CI fails loudly if any two disagree.
- Adding or removing a `.cpp` file from libavoid's Makefile requires
  a visible edit to `CMakeLists.txt`. Phase 0's bump checklist in
  `build-notes.md` already lists this.
- Windows users on a non-`Release` MSVC toolchain (e.g. a developer
  trying to debug the extension) need to add `NDEBUG` manually or
  accept they cannot get `COLA_ASSERT`-live debug builds. Acceptable
  for phase 1; revisit if it bites in phase 2+.
- The `version()` function is the only API surface for phase 1. The
  smoke test asserts the 40-char hex shape and, when run inside a
  source checkout, cross-checks against `LIBAVOID_COMMIT.txt`. This
  is enough to detect a misconfigured build (empty hash, stale file,
  wrong submodule checkout) without overcommitting to a public
  contract — `version()` may be renamed or moved in phase 2 if the
  API shape settles elsewhere.
