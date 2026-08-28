"""Tests for the selector-driven tools (:mod:`i3wm_mcp.tools_focus`).

Every case asserts the exact i3 command string the tool emitted, recorded in
``conn.commands`` -- the command text is the contract with i3, so an assertion
on the returned model alone would not catch a malformed payload.
"""

from __future__ import annotations

import pytest
from tests.conftest import FakeConnection

from i3wm_mcp import server


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"direction": "left"}, "focus left"),
        ({"con_id": 5}, "[con_id=5] focus"),
        ({"mark": "x"}, '[con_mark="x"] focus'),
        ({"window_class": "Firefox"}, '[class="Firefox"] focus'),
        ({"instance": "nav"}, '[instance="nav"] focus'),
        ({"title": "t"}, '[title="t"] focus'),
        ({"target": "parent"}, "focus parent"),
        ({"layer": "floating"}, "focus floating"),
    ],
)
async def test_focus_window_variants(set_backend, kwargs, expected) -> None:
    conn = set_backend(FakeConnection())
    result = await server.focus_window(**kwargs)
    assert result.success is True
    assert conn.commands == [expected]


async def test_focus_window_requires_exactly_one(set_backend) -> None:
    set_backend(FakeConnection())
    with pytest.raises(ValueError, match="exactly one"):
        await server.focus_window()
    with pytest.raises(ValueError, match="exactly one"):
        await server.focus_window(direction="left", target="parent")


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"direction": "left"}, "move left 10 px"),
        ({"direction": "right", "amount_px": 25}, "move right 25 px"),
        ({"to_workspace": "3"}, 'move container to workspace "3"'),
        ({"to_output": "HDMI-0"}, 'move container to output "HDMI-0"'),
        ({"to_scratchpad": True}, "move to scratchpad"),
        ({"to_center": True}, "move position center"),
        ({"to_workspace": "3", "con_id": 5}, '[con_id=5] move container to workspace "3"'),
    ],
)
async def test_move_window_variants(set_backend, kwargs, expected) -> None:
    conn = set_backend(FakeConnection())
    await server.move_window(**kwargs)
    assert conn.commands == [expected]


async def test_move_window_requires_one_destination(set_backend) -> None:
    set_backend(FakeConnection())
    with pytest.raises(ValueError, match="exactly one"):
        await server.move_window()
    with pytest.raises(ValueError, match="exactly one"):
        await server.move_window(to_scratchpad=True, to_center=True)
