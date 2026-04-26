"""Upstream ``cola/libavoid/tests/buildOrthogonalChannelInfo1.cpp``.

Phase 0's inventory flagged this test as needing translator support for state-capture test() harnesses;
that is a phase-4 feature per ``CLAUDE.md`` §5. The stub records the
translation target so later phases can unskip it by porting the body.
"""

import pytest

pytest.skip(
    "libavoid_py does not yet wrap translator support for state-capture test() harnesses; "
    "tracked in docs/api-coverage.md.",
    allow_module_level=True,
)
