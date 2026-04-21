# Third-party notices

This wheel statically links third-party source code. Each section below
identifies a component, its copyright holder, upstream source, the exact
commit we build against, and the applicable license.

## libavoid

- **Component:** libavoid — orthogonal and polyline connector routing library.
- **Copyright:** Copyright (C) 2004-2014 Monash University.
- **Author:** Michael Wybrow.
- **Upstream project:** adaptagrams
  (<https://github.com/mjwybrow/adaptagrams>), directory `cola/libavoid/`.
- **Pinned commit:** `840ebcff20dbba36ad03a2160edf7cbaf9859984`
  (2025-10-29, "Merge pull request #84 from tczauderna/master").
  The submodule at `vendor/adaptagrams/` tracks this commit exactly.
- **License:** LGPL-2.1-or-later. Per the per-file copyright headers in
  `vendor/adaptagrams/cola/libavoid/*.cpp`, you may use this library
  under the terms of the GNU Lesser General Public License version 2.1
  "or (at your option) any later version". The full license text is in
  [`LICENSE`](LICENSE).
- **Modifications:** none. We build libavoid as-is from the pinned
  commit. If a patch ever becomes necessary it will be shipped as a
  separate file under `patches/` and applied at build time, never
  squashed into the vendored source tree.
- **Relinking obligation (LGPL-2.1 §6):** recipients of this wheel may
  replace the bundled libavoid. The complete source of the pinned
  version is available at the upstream URL above; the build system
  (`CMakeLists.txt`, `pyproject.toml`) and the pybind11 wrapper sources
  in this repository contain everything needed to relink against a
  modified libavoid.
