"""Upstream ``cola/libavoid/tests/junction02.cpp``.

Phase 0's inventory flagged this test as needing junctions;
that is a phase-4 feature per ``CLAUDE.md`` §5. The stub records the
translation target so later phases can unskip it by porting the body.
"""

import pytest

pytest.skip(
    "libavoid_py does not yet wrap junctions; "
    "tracked in docs/api-coverage.md.",
    allow_module_level=True,
)
