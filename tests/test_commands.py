"""Tests for the shared criteria builder (:mod:`i3wm_mcp.commands`).

Exercised through the tools rather than the helpers directly: the thing that
must not regress is the command string i3 receives, and only an end-to-end
assertion proves the escaping survives interpolation into the payload.
"""

from __future__ import annotations

from tests.conftest import FakeConnection

from i3wm_mcp import server


async def test_criteria_escaping(set_backend) -> None:
    """A mark containing quotes/backslashes is escaped in the criteria."""
    conn = set_backend(FakeConnection())
    await server.kill_window(mark='a"b\\c')
    assert conn.commands == ['[con_mark="a\\"b\\\\c"] kill']


async def test_criteria_ordering_multiple_fields(set_backend) -> None:
    """Multiple criteria fields combine in the documented order."""
    conn = set_backend(FakeConnection())
    await server.focus_window(con_id=5, window_class="X", title="t")
    assert conn.commands == ['[con_id=5 class="X" title="t"] focus']
