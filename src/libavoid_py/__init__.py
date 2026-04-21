"""libavoid-py — Python bindings for libavoid.

Phase 1 exposes a single function, :func:`version`, that returns the
upstream libavoid commit hash this wheel was built against. The routing
API lands in phase 2.
"""

from ._core import version

__all__ = ["version"]
