# libavoid-py

Python bindings for [libavoid](https://www.adaptagrams.org/documentation/libavoid.html),
a C++ library for incremental orthogonal and polyline connector routing
around obstacles.

This is an **unofficial** wrapper. It is not maintained by the libavoid
authors. Upstream libavoid lives in the
[adaptagrams](https://github.com/mjwybrow/adaptagrams) project at
`cola/libavoid/`; this package vendors it as a git submodule and exposes
it to Python via [pybind11](https://pybind11.readthedocs.io/).

## Status

Early. Phase 1 of the roadmap — a wheel that installs, imports, and
exposes `version()`. See `CLAUDE.md` for the full phased plan. The
routing API (`Router`, `ShapeRef`, `ConnRef`, geometry types) lands in
phase 2.

## Install

```
pip install libavoid-py
```

No runtime dependencies beyond Python. libavoid is statically linked
into the extension module.

Supported platforms: Linux x86_64 (manylinux_2_28+) and Windows AMD64,
on CPython 3.11, 3.12, and 3.13.

## Quickstart

```python
import libavoid_py

# Phase 1: only version() is exposed. It returns the libavoid
# commit hash that this wheel was built against.
print(libavoid_py.version())
```

Full routing examples will land with phase 2.

## License

This package is distributed under
[**LGPL-2.1-or-later**](LICENSE), matching the license of the libavoid
source it embeds.

What this means in practice:

- You can `import libavoid_py` from a proprietary/closed-source Python
  application. That application does **not** become LGPL.
- If you redistribute this wheel (for example, bundling it into your
  own installer), you must also pass along the license text and the
  third-party notices.
- You cannot sublicense the bundled libavoid under a more restrictive
  license.
- You are entitled to relink the extension module against a modified
  libavoid. The pinned upstream source is always available at the
  commit URL printed in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md),
  and the build system in this repository is sufficient to rebuild the
  extension. This written offer is valid for at least three years from
  the date of the release you obtained.

Non-lawyers summary: if you want to use it, use it. If you want to
modify libavoid and ship that, you have to let your users replace your
modified libavoid with theirs.

## Acknowledgments

libavoid is the work of Michael Wybrow, Kim Marriott, and Peter Stuckey
at Monash University. The algorithms this package exposes are described
in their papers, listed on the
[adaptagrams documentation site](https://www.adaptagrams.org/documentation/libavoid.html).
If you use libavoid in academic work, cite their publications.

This repository contains no original algorithmic work — it is a binding
over their library.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Contributions are accepted under
LGPL-2.1-or-later.
