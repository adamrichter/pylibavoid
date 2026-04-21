# libavoid build notes

Anchor commit: `840ebcff20dbba36ad03a2160edf7cbaf9859984` of
`mjwybrow/adaptagrams`, directory `cola/libavoid/`.

## Question this document answers

> What do we need to do to compile libavoid as a static library inside
> our Python extension, on Linux (manylinux_2_28 + GCC) and Windows
> (MSVC 2022), with no runtime dependencies and no LGPL-relinking
> obligations violated?

## Sources to compile

From `cola/libavoid/Makefile.am`, the `libavoid_la_SOURCES` list is
authoritative. 23 `.cpp` files go into the library:

```
actioninfo.cpp
connectionpin.cpp
connector.cpp
connend.cpp
geometry.cpp
geomtypes.cpp
graph.cpp
hyperedge.cpp
hyperedgeimprover.cpp
hyperedgetree.cpp
junction.cpp
makepath.cpp
mtst.cpp
obstacle.cpp
orthogonal.cpp
router.cpp
scanline.cpp
shape.cpp
timer.cpp
vertices.cpp
viscluster.cpp
visibility.cpp
vpsc.cpp
```

Note: `vpsc.cpp` is a libavoid-local, consolidated subset of libvpsc
(see the comment at the top of the file). libavoid ships its own
minimal vpsc copy so it compiles standalone — that's why the `cola/`
build can assemble libavoid without libvpsc. There is a `USELIBVPSC`
guard that would switch to the sibling libvpsc if defined; we do
not define it.

Our CMake target should be a straight enumeration of these 23 files:

```cmake
add_library(libavoid STATIC <list of 23 files from vendor/adaptagrams/cola/libavoid/>)
```

Avoid globbing; list them explicitly so upstream additions don't
silently get built, and so a commit bump is a visible change to
`CMakeLists.txt`.

## Include path

From the Makefile: `libavoid_la_CPPFLAGS = -I$(top_srcdir)
-I$(includedir)/libavoid -fPIC`. In upstream layout, `top_srcdir` is
`cola/`, so the effective include root is `cola/` and sources use
`#include "libavoid/xxx.h"`.

For CMake this translates to:

```cmake
target_include_directories(libavoid PUBLIC ${adaptagrams_SOURCE_DIR}/cola)
```

i.e. the parent directory of `libavoid/`. Do not add `cola/libavoid`
itself — the sources include each other as `"libavoid/router.h"`, not
`"router.h"`.

## C++ standard

`configure.ac` sets `CXXFLAGS="-std=gnu++11 $CXXFLAGS"`. A
grep for C++17-only constructs (`if constexpr`, `std::optional`,
`std::variant`, `std::string_view`, `std::filesystem`, `[[nodiscard]]`)
turns up nothing in libavoid sources. libavoid requires **C++11**.

Our binding code is C++17 (pybind11 + scikit-build-core + CLAUDE.md
§3). Mixing the two is fine: compile libavoid with `-std=c++17` (or
`/std:c++17` on MSVC) to match the binding objects. C++17 is backward
compatible with C++11 for everything libavoid uses.

## External dependencies

None. libavoid only uses the C++ standard library. The full set of
system includes (from a `grep #include` across all sources) is:

```
<algorithm> <cassert> <cfloat> <climits> <clocale> <cmath>
<cstdarg> <cstdio> <cstdlib> <cstring> <ctime>
<iomanip> <iostream> <limits> <list> <map> <queue> <set>
<sstream> <string> <utility> <vector>
```

Plus `<afx.h>` (MFC), conditionally included in two places:
`assertions.h` (under `_MSC_VER && !NDEBUG`) and `debug.h` (under
`_MSC_VER && USE_ATLTRACE`). See the assertions and debug sections
below; both guards are disabled in our build.

No POSIX headers, no `<windows.h>`, no `<unistd.h>`, no libraries
beyond libstdc++/libc++. This is why the wheel can satisfy "no runtime
dependencies": all the vendored code links into a single extension
module.

Cairomm appears in the wider adaptagrams `configure.ac` but is only
used by `libcola`. libavoid does not pull it in.

## Preprocessor defines that matter

`libavoid` has seven relevant macros:

| Macro | Defined where | Effect | What we want |
|-------|---------------|--------|--------------|
| `LIBAVOID_NO_DLL` | By the consumer | Suppresses MSVC `__declspec(dllexport/dllimport)` attributes in `dllexport.h`. | **Define** for our MSVC static build. |
| `LIBAVOID_EXPORTS` | By the library during its own build | When building as a DLL: switches `AVOID_EXPORT` to `dllexport`. | **Do not define**. We are statically linking. |
| `NDEBUG` | By the consumer (release builds) | Disables `COLA_ASSERT` and avoids pulling `<afx.h>` on MSVC. | **Define for MSVC Release**. For Linux, keep `COLA_ASSERT` active in Debug unless assertions slow us down. |
| `USE_ASSERT_EXCEPTIONS` | By the consumer | `assertions.h` falls back to `libvpsc/assertions.h` — which we do not vendor. | **Do not define**. |
| `USE_ATLTRACE` | By the consumer | In `debug.h`, routes `db_printf` through `ATL::AtlTrace`. Requires ATL headers. | **Do not define**. |
| `LIBAVOID_DEBUG` | By the consumer | Turns on verbose `db_printf` output. | **Do not define**. |
| `AVOID_PROFILE` | By the consumer | Enables the `Timer` class and `TIMER_*` macros. | **Do not define**. |

### `dllexport.h` (Windows DLL visibility)

```c
#if defined(_MSC_VER) && !defined(LIBAVOID_NO_DLL)
    #ifdef LIBAVOID_EXPORTS
        #define AVOID_EXPORT __declspec(dllexport)
    #else
        #define AVOID_EXPORT __declspec(dllimport)
    #endif
#else
    #define AVOID_EXPORT
#endif
```

We static-link libavoid into the pybind11 extension module. That means:
- On Linux/GCC: `_MSC_VER` is not defined; `AVOID_EXPORT` is empty
  automatically. No action.
- On Windows/MSVC: the default (neither macro set) would mark every
  class as `dllimport`, which is wrong when the class is defined in
  the same binary. Define `LIBAVOID_NO_DLL` when compiling both
  libavoid and the pybind11 wrapper so `AVOID_EXPORT` is empty.

```cmake
if(MSVC)
    target_compile_definitions(libavoid PUBLIC LIBAVOID_NO_DLL)
endif()
```

Use `PUBLIC` so the binding target inherits it and every
`#include "libavoid/...h"` sees the same definition.

### `assertions.h` (MFC dependency on MSVC debug builds)

```c
#ifdef NDEBUG
  #define COLA_ASSERT(expr) static_cast<void>(0)
#else
  #ifdef _MSC_VER
    #include <afx.h>
    #define COLA_ASSERT(expr) ASSERT(expr)
  #elif defined(USE_ASSERT_EXCEPTIONS)
    #include "libvpsc/assertions.h"
  #else
    #include <cassert>
    #define COLA_ASSERT(expr) assert(expr)
  #endif
#endif
```

Problem: in an MSVC Debug build without `NDEBUG`, the preprocessor
picks the MFC branch, which requires `<afx.h>` — MFC headers that
aren't present in a standard Build Tools install and that would link
against `mfc140.dll` as a runtime dependency, violating the
no-dependencies posture.

Three ways to avoid MFC:

1. **Define `NDEBUG`** on all MSVC configurations (even Debug). This
   matches how most Python build configurations behave: cibuildwheel
   and scikit-build-core use `Release` by default on MSVC. Cleanest.
2. Define `USE_ASSERT_EXCEPTIONS` and vendor `libvpsc/assertions.h`.
   Adds a file we don't otherwise need.
3. Patch `assertions.h` in a `patches/` file to drop the MSVC branch.
   Per `CLAUDE.md` §12.3 patches go under `patches/`, not squashed
   into the vendored source.

**Decision default**: use (1) — ensure `NDEBUG` is defined for any
MSVC configuration we ship. CMake's default `Release` does this;
`Debug` does not. We will either build only `Release` wheels (the
cibuildwheel default) or explicitly add `NDEBUG` via
`target_compile_definitions` when building any other MSVC config.

Record whichever we pick as an ADR in `docs/decisions/` when phase 1
lands.

### `debug.h` (ATL dependency on MSVC)

```c
#ifdef LIBAVOID_DEBUG
  #if defined(_MSC_VER) && defined(USE_ATLTRACE)
    #include <afx.h>
    #define db_printf ATL::AtlTrace
  ...
```

Only fires if **both** `LIBAVOID_DEBUG` and `USE_ATLTRACE` are
defined. We define neither, so this branch never compiles. No action.

### `timer.h`

```c
#ifndef AVOID_PROFILE
  #define TIMER_START(...) do {} while(0)
  ...
#else
  ... Timer/bigclock_t/TimerIndex ...
#endif
```

The header defaults to a no-op. Without `AVOID_PROFILE`, timers do
nothing and contribute no runtime cost. No action.

## Platform-specific code paths

Grep for `_MSC_VER`, `_WIN32`, `WIN32`, `__MINGW*` across libavoid
sources turns up **three files**: `assertions.h`, `debug.h`,
`dllexport.h` — all discussed above, and all gated off when we set
the flags recommended in this document.

No `#ifdef __linux__`, no `#ifdef _WIN32` logic in the routing code
itself. libavoid's algorithms are fully portable.

## What the upstream builds produce

- **Autotools (Linux)**: libtool archive `libavoid.la`, which produces
  `libavoid.so.X.Y.Z`/`libavoid.X.Y.Z.dylib` (shared) and
  `libavoid.a` (static). `libavoid.pc` pkg-config file is also
  installed.
- **MSBuild (Windows)**: `libavoid.vcxproj` / `libavoid.sln`. The
  vcxproj is configured as `DynamicLibrary` in all four build
  configurations (Debug/Release × Win32/x64). If we were to drive
  this directly we'd switch to `StaticLibrary`, but we're replacing
  it with CMake anyway.

The installed headers (from `libavoidinclude_HEADERS` in
`Makefile.am`) are what land in `$prefix/include/libavoid/`. We do
not install headers in our wheel — the extension is a compiled
artifact — but the list is useful as a sanity check for "is this
header user-facing?" (see `api-surface.md`).

## CMake skeleton for phase 1

Concrete target layout for `CMakeLists.txt` in the top of the repo:

```cmake
cmake_minimum_required(VERSION 3.18)
project(libavoid_py LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(ADAPTAGRAMS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/vendor/adaptagrams)
set(LIBAVOID_DIR    ${ADAPTAGRAMS_DIR}/cola/libavoid)

add_library(libavoid_static STATIC
    ${LIBAVOID_DIR}/actioninfo.cpp
    ${LIBAVOID_DIR}/connectionpin.cpp
    ${LIBAVOID_DIR}/connector.cpp
    ${LIBAVOID_DIR}/connend.cpp
    ${LIBAVOID_DIR}/geometry.cpp
    ${LIBAVOID_DIR}/geomtypes.cpp
    ${LIBAVOID_DIR}/graph.cpp
    ${LIBAVOID_DIR}/hyperedge.cpp
    ${LIBAVOID_DIR}/hyperedgeimprover.cpp
    ${LIBAVOID_DIR}/hyperedgetree.cpp
    ${LIBAVOID_DIR}/junction.cpp
    ${LIBAVOID_DIR}/makepath.cpp
    ${LIBAVOID_DIR}/mtst.cpp
    ${LIBAVOID_DIR}/obstacle.cpp
    ${LIBAVOID_DIR}/orthogonal.cpp
    ${LIBAVOID_DIR}/router.cpp
    ${LIBAVOID_DIR}/scanline.cpp
    ${LIBAVOID_DIR}/shape.cpp
    ${LIBAVOID_DIR}/timer.cpp
    ${LIBAVOID_DIR}/vertices.cpp
    ${LIBAVOID_DIR}/viscluster.cpp
    ${LIBAVOID_DIR}/visibility.cpp
    ${LIBAVOID_DIR}/vpsc.cpp
)

target_include_directories(libavoid_static PUBLIC ${ADAPTAGRAMS_DIR}/cola)

if(NOT MSVC)
    target_compile_options(libavoid_static PRIVATE -fPIC)
endif()

if(MSVC)
    # Flatten AVOID_EXPORT to an empty macro when static-linking.
    target_compile_definitions(libavoid_static PUBLIC LIBAVOID_NO_DLL)
    # Ensure assertions.h never tries to include <afx.h>.
    target_compile_definitions(libavoid_static PUBLIC NDEBUG)
endif()

# ... then the pybind11 module links libavoid_static PRIVATE.
```

Notes on why each decision is the default, not the user preference:

- `-fPIC` only on non-MSVC. MSVC does not use `-fPIC` and the concept
  of position-independent code is implicit for DLLs.
- The `NDEBUG` propagation for MSVC is the simplest way to avoid the
  MFC dependency. If we later want MSVC Debug builds to keep
  `COLA_ASSERT` live, switch to `USE_ASSERT_EXCEPTIONS` with a
  vendored `libvpsc/assertions.h`, or patch `assertions.h`.
- Target name `libavoid_static` disambiguates from the upstream
  `libavoid` target (we're not building their `.so`), and avoids a
  CMake target-name clash if someone ever links against the real
  upstream libavoid in the same build.

This is advisory for phase 1; the ADR with final choices lives in
`docs/decisions/` when phase 1 PRs open.

## Things we will *not* rely on

- Upstream's `configure.ac` / `Makefile.am` — we replace it with CMake.
- Upstream's `.vcxproj` — we replace it with CMake driving MSVC.
- Upstream's `.pc` file — we do not install headers.
- Upstream's autodetection of Cairomm — not relevant to libavoid.

## Things that could break on commit bumps

When we bump the `vendor/adaptagrams` submodule, re-check:

1. Does `libavoid_la_SOURCES` in `Makefile.am` have new or removed
   `.cpp` files? If yes, update our `CMakeLists.txt` source list.
2. Has any source started using C++17-only features? If our binding
   was C++17 already, no change. Worth a grep check.
3. Are there new preprocessor knobs (`LIBAVOID_*`, `USE_*`,
   `AVOID_*`) to consider?
4. Does the installed public API change in ways that affect the
   bindings? If so, `docs/research/api-surface.md` needs a refresh too.

Dependabot/Renovate on the submodule pointer is the right place to
surface these checks routinely.
