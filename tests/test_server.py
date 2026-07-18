"""Tests for the tool layer (:mod:`i3wm_mcp.server`).

Each test installs a fake connection via ``set_backend`` and asserts both the
returned model and the exact i3 command string the tool emitted (recorded in
``conn.commands``).
"""

from __future__ import annotations

import pytest
from tests.conftest import (
    FakeConfig,
    FakeConnection,
    FakeVersion,
    FakeWorkspace,
)

from i3wm_mcp import server

# -- Read tools --------------------------------------------------------------


async def test_get_tree(set_backend, sample_tree) -> None:
    set_backend(FakeConnection(tree=sample_tree))
    result = await server.get_tree()
    assert result.count == 3
    assert result.truncated is False


async def test_get_tree_with_filter(set_backend, sample_tree) -> None:
    set_backend(FakeConnection(tree=sample_tree))
    result = await server.get_tree(window_class="firefox")
    assert result.count == 1
    assert result.windows[0].window_class == "firefox"


async def test_get_focused_present_and_absent(set_backend, sample_tree) -> None:
    set_backend(FakeConnection(tree=sample_tree))
    assert (await server.get_focused()).focused.window_class == "firefox"

    from tests.conftest import FakeCon

    set_backend(FakeConnection(tree=FakeCon(type="root", name="root")))
    assert (await server.get_focused()).focused is None


async def test_list_workspaces(set_backend) -> None:
    set_backend(FakeConnection(workspaces=[FakeWorkspace(), FakeWorkspace(num=2, name="2")]))
    result = await server.list_workspaces()
    assert result.count == 2
    assert result.workspaces[1].name == "2"


async def test_list_outputs(set_backend) -> None:
    from tests.conftest import FakeOutput

    set_backend(FakeConnection(outputs=[FakeOutput(), FakeOutput(name="HDMI-0", primary=False)]))
    result = await server.list_outputs()
    assert result.count == 2
    assert result.outputs[0].primary is True


async def test_get_config_full(set_backend) -> None:
    set_backend(FakeConnection(config=FakeConfig("set $mod Mod4\n"), binding_modes=["default"]))
    result = await server.get_config()
    assert result.version == "4.25.1"
    assert result.is_sway is False
    assert result.config_text == "set $mod Mod4\n"
    assert result.binding_modes == ["default"]


async def test_get_config_without_text_and_sway(set_backend) -> None:
    set_backend(FakeConnection(version=FakeVersion(human_readable="sway version 1.9")))
    result = await server.get_config(include_config_text=False)
    assert result.config_text is None
    assert result.is_sway is True


# -- focus_window ------------------------------------------------------------


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


# -- move_window -------------------------------------------------------------


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


# -- manage_workspace --------------------------------------------------------


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


# -- set_layout --------------------------------------------------------------


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


# -- toggle_window_state -----------------------------------------------------


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


# -- destructive tools -------------------------------------------------------


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


# -- helper behaviour --------------------------------------------------------


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
