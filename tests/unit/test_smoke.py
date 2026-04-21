"""Phase 1 smoke test.

The wheel should import, expose :func:`version`, and return the libavoid
commit hash that was pinned at build time. The pinned hash lives in
``LIBAVOID_COMMIT.txt`` at the repo root and is authoritative: when we
bump the submodule we update that file, so the check here doubles as a
guard against forgetting to update either side.
"""

from __future__ import annotations

import re
from pathlib import Path

import libavoid_py


def test_module_exposes_version() -> None:
    assert hasattr(libavoid_py, "version")
    assert callable(libavoid_py.version)


def test_version_is_40_char_hex() -> None:
    hash_ = libavoid_py.version()
    assert isinstance(hash_, str)
    assert re.fullmatch(r"[0-9a-f]{40}", hash_), (
        f"expected a 40-char lowercase hex git hash, got {hash_!r}"
    )


def _pinned_hash_from_repo() -> str | None:
    """Return the hash from LIBAVOID_COMMIT.txt if we are running from
    a source checkout; otherwise None (running from an installed wheel
    outside the repo)."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        candidate = parent / "LIBAVOID_COMMIT.txt"
        if candidate.exists():
            return candidate.read_text().strip()
    return None


def test_version_matches_pinned_commit_when_in_repo() -> None:
    pinned = _pinned_hash_from_repo()
    if pinned is None:
        return
    assert libavoid_py.version() == pinned, (
        "libavoid_py.version() disagrees with LIBAVOID_COMMIT.txt — one of "
        "them was updated without the other"
    )
