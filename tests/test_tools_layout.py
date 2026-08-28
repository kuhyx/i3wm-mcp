"""Tests for the arrangement tools (:mod:`i3wm_mcp.tools_layout`).

Covers the emitted command string for every branch plus the per-action
validation errors, since `manage_workspace` decides required arguments from
its `action` rather than from the signature.
"""

from __future__ import annotations

import pytest
from tests.conftest import FakeConnection

from i3wm_mcp import server


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"action": "switch", "name": "3"}, 'workspace "3"'),
        ({"action": "move_container_to", "name": "3"}, 'move container to workspace "3"'),
        (
            {"action": "move_container_to", "name": "3", "follow": True},
            'move container to workspace "3"; workspace "3"',
        ),
        ({"action": "rename", "new_name": "dev"}, 'rename workspace to "dev"'),
        ({"action": "rename", "name": "1", "new_name": "dev"}, 'rename workspace "1" to "dev"'),
        ({"action": "navigate", "direction": "next"}, "workspace next"),
    ],
)
async def test_manage_workspace_variants(set_backend, kwargs, expected) -> None:
    conn = set_backend(FakeConnection())
    await server.manage_workspace(**kwargs)
    assert conn.commands == [expected]


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"action": "switch"}, "`switch` requires `name`"),
        ({"action": "move_container_to"}, "requires `name`"),
        ({"action": "rename"}, "requires `new_name`"),
        ({"action": "navigate"}, "requires `direction`"),
    ],
)
async def test_manage_workspace_validation(set_backend, kwargs, match) -> None:
    set_backend(FakeConnection())
    with pytest.raises(ValueError, match=match):
        await server.manage_workspace(**kwargs)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"layout": "tabbed"}, "layout tabbed"),
        ({"split": "vertical"}, "split vertical"),
        ({"border": "none"}, "border none"),
        ({"border": "pixel", "border_width": 3}, "border pixel 3"),
        (
            {"layout": "tabbed", "split": "vertical", "border": "normal"},
            "layout tabbed; split vertical; border normal",
        ),
    ],
)
async def test_set_layout_variants(set_backend, kwargs, expected) -> None:
    conn = set_backend(FakeConnection())
    await server.set_layout(**kwargs)
    assert conn.commands == [expected]


async def test_set_layout_requires_something(set_backend) -> None:
    set_backend(FakeConnection())
    with pytest.raises(ValueError, match="at least one"):
        await server.set_layout()


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"state": "floating"}, "floating toggle"),
        ({"state": "floating", "enable": True}, "floating enable"),
        ({"state": "floating", "enable": False}, "floating disable"),
        ({"state": "sticky"}, "sticky toggle"),
        ({"state": "fullscreen"}, "fullscreen toggle"),
        ({"state": "fullscreen", "fullscreen_scope": "global"}, "fullscreen toggle global"),
    ],
)
async def test_toggle_window_state_variants(set_backend, kwargs, expected) -> None:
    conn = set_backend(FakeConnection())
    await server.toggle_window_state(**kwargs)
    assert conn.commands == [expected]
