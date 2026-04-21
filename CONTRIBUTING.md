# Contributing

Thanks for wanting to help. A few ground rules keep this project
maintainable.

## License of your contribution

By opening a pull request, you agree that your contribution is
distributed under **LGPL-2.1-or-later**, matching the rest of the
package and the libavoid source it wraps. If that is not acceptable
for your situation, please say so in the PR before merging and we will
figure it out.

## What belongs here

- Bindings over the public libavoid API defined in
  `vendor/adaptagrams/cola/libavoid/`.
- Python-side tests of the wrapper.
- Type stubs, docstrings, build improvements, CI fixes.

## What does not belong here

- Patches to vendored libavoid source. We build upstream as-is. If a
  change is genuinely needed, ship it as a separate file under
  `patches/` and apply it at build time; never edit `vendor/` in place.
- Diagram tooling, Visio/Excel integration, GUI code, auto-layout.
  These live in downstream projects.

## Before opening a PR

- Read the relevant sections of `CLAUDE.md`. Sections 2 (working
  agreements), 3 (technical constraints), 6 (API design principles),
  and 11 (out of scope) are the ones that get violated most often.
- Keep PRs small and focused. One feature or fix per PR.
- If you are wrapping a new piece of the libavoid API, write a
  docstring on every public method. No exceptions.
- If you are making a non-obvious choice, add an ADR under
  `docs/decisions/` explaining the context, decision, and
  consequences.

## Local development

The build is driven by scikit-build-core + CMake. On Linux:

```
git clone --recurse-submodules <this repo>
cd libavoid-py
pip install -e . --config-settings=build-dir=build
pytest
```

If you forgot `--recurse-submodules`, run
`git submodule update --init --recursive` before building.

## Reporting bugs

Open an issue with a minimal reproducer — the shortest Python snippet
that demonstrates the problem. If the bug is actually in libavoid
itself (not the wrapper), we will redirect you upstream to
<https://github.com/mjwybrow/adaptagrams/issues>.
