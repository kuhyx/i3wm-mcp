"""Test the console entry point (:mod:`i3wm_mcp.__main__`)."""

from __future__ import annotations

import pytest

from i3wm_mcp import __main__


def test_main_starts_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """`main()` delegates to the FastMCP server's stdio ``run()``."""
    called: dict[str, bool] = {}
    monkeypatch.setattr(__main__.mcp, "run", lambda: called.setdefault("ran", True))
    __main__.main()
    assert called == {"ran": True}
