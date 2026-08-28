"""Tests for the read-only tools (:mod:`i3wm_mcp.tools_read`).

Each test installs a fake connection via ``set_backend`` and asserts the
returned model. Tools are called through :mod:`i3wm_mcp.server`, the facade
clients see, so a re-export that went missing fails here too.
"""

from __future__ import annotations

from tests.conftest import (
    FakeCon,
    FakeConfig,
    FakeConnection,
    FakeOutput,
    FakeVersion,
    FakeWorkspace,
)

from i3wm_mcp import server


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

    set_backend(FakeConnection(tree=FakeCon(type="root", name="root")))
    assert (await server.get_focused()).focused is None


async def test_list_workspaces(set_backend) -> None:
    set_backend(FakeConnection(workspaces=[FakeWorkspace(), FakeWorkspace(num=2, name="2")]))
    result = await server.list_workspaces()
    assert result.count == 2
    assert result.workspaces[1].name == "2"


async def test_list_outputs(set_backend) -> None:
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
