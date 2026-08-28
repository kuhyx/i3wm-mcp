"""Tests for the destructive tools (:mod:`i3wm_mcp.tools_exec`).

Nothing here reaches a real window manager: the fake connection records the
payload, which is exactly the value that would otherwise close a window or
launch a process.
"""

from __future__ import annotations

import pytest
from tests.conftest import FakeConnection

from i3wm_mcp import server


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"command": "firefox"}, "exec firefox"),
        ({"command": "firefox", "no_startup_id": True}, "exec --no-startup-id firefox"),
    ],
)
async def test_exec_application(set_backend, kwargs, expected) -> None:
    conn = set_backend(FakeConnection())
    await server.exec_application(**kwargs)
    assert conn.commands == [expected]


async def test_run_command(set_backend) -> None:
    conn = set_backend(FakeConnection())
    await server.run_command(command="reload")
    assert conn.commands == ["reload"]


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, "kill"),
        ({"con_id": 5}, "[con_id=5] kill"),
        ({"window_class": "Firefox"}, '[class="Firefox"] kill'),
    ],
)
async def test_kill_window(set_backend, kwargs, expected) -> None:
    conn = set_backend(FakeConnection())
    await server.kill_window(**kwargs)
    assert conn.commands == [expected]
