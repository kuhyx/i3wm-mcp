"""Test the console entry point (:mod:`i3wm_mcp.__main__`)."""

from __future__ import annotations

import sys

import pytest

from i3wm_mcp import __main__


def test_main_starts_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """`main()` delegates to the MCP server's stdio ``run()``."""
    called: dict[str, bool] = {}
    monkeypatch.setattr(__main__.mcp, "run", lambda: called.setdefault("ran", True))
    __main__.main([])
    assert called == {"ran": True}


def test_main_help(capsys: pytest.CaptureFixture[str]) -> None:
    """``--help`` prints the credit line and exits cleanly."""
    with pytest.raises(SystemExit) as exc_info:
        __main__.main(["--help"])
    assert exc_info.value.code == 0
    stdout = capsys.readouterr().out
    assert stdout.endswith("Created by kuhy https://kuhy.duckdns.org\n")


def test_main_respects_sys_argv(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Calling ``main()`` with no argument reads ``sys.argv[1:]``."""
    monkeypatch.setattr(sys, "argv", ["i3wm-mcp", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        __main__.main()
    assert exc_info.value.code == 0
    stdout = capsys.readouterr().out
    assert stdout.endswith("Created by kuhy https://kuhy.duckdns.org\n")
