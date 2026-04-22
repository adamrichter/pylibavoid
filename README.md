# libavoid-py

Python bindings for [libavoid](https://www.adaptagrams.org/documentation/libavoid.html),
a C++ library for incremental orthogonal and polyline connector routing
around obstacles.

This is an **unofficial** wrapper. It is not maintained by the libavoid
authors. Upstream libavoid lives in the
[adaptagrams](https://github.com/mjwybrow/adaptagrams) project at
`cola/libavoid/`; this package vendors it as a git submodule and exposes
it to Python via [pybind11](https://pybind11.readthedocs.io/).

> **Not ready for use.** libavoid-py is in active development. The
> public API may change without notice, there are no published
> releases on PyPI, and several libavoid features are not wrapped
> yet (see [Status](#status) below). If you build from source, pin
> a specific git commit — `main` is a moving target while the
> roadmap progresses.

## Status

Pre-alpha. The core routing API — `Router`, `ShapeRef`, `ConnRef`,
`ConnEnd`, geometry primitives, and the routing-parameter/option
enums — is wrapped and exercised by unit tests, plus 32 upstream
regression tests translated from
`vendor/adaptagrams/cola/libavoid/tests/`. See
[`docs/api-coverage.md`](docs/api-coverage.md) for the per-test
status. Advanced features (connection pins, junctions, clusters,
hyperedges, checkpoints, and routing-progress callbacks) are not yet
wrapped; see `CLAUDE.md` §5 phase 4 for that plan.

## Install

Not yet published to PyPI — `pip install libavoid-py` will not
work today. To try the current state of the bindings, build from
source:

```
git clone --recursive https://github.com/adamrichter/pylibavoid.git
cd pylibavoid
pip install .
```

Requires a C++17 compiler and CMake. No runtime dependencies
beyond Python; libavoid is statically linked into the extension
module.

The build targets Linux x86_64 (manylinux_2_28+) and Windows
AMD64 on CPython 3.11, 3.12, and 3.13. CI exercises both
platforms; other platforms are not supported in this iteration.

## Quickstart

Route an orthogonal connector between two rectangular shapes:

```python
import libavoid_py as la

router = la.Router(la.RouterFlag.OrthogonalRouting)

# Two rectangles sitting side-by-side with a gap between them.
a = la.ShapeRef(router, la.Rectangle(la.Point(0, 0), la.Point(40, 20)))
b = la.ShapeRef(router, la.Rectangle(la.Point(100, 0), la.Point(140, 20)))

# Draw a connector from the right edge of A to the left edge of B.
src = la.ConnEnd(la.Point(40, 10))
dst = la.ConnEnd(la.Point(100, 10))
conn = la.ConnRef(router, src, dst)

router.process_transaction()  # compute routes

route = conn.display_route()   # PolyLine = list of Points
for pt in route:
    print(pt)
```

Every identifier here mirrors libavoid's C++ name: the upstream
documentation at <https://www.adaptagrams.org/documentation/libavoid.html>
applies directly, with `camelCase` methods rewritten to `snake_case`.

Check the `tests/` directory for worked examples of routing
parameters, shape movement, and transaction-based batching.
`tests/upstream/` mirrors the upstream libavoid regression tests
under `vendor/adaptagrams/cola/libavoid/tests/`; re-run
`python scripts/translate_upstream.py` after bumping the submodule
to regenerate them from the new upstream sources.

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
