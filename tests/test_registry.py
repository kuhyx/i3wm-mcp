"""The advertised tool set, asserted by name.

Tools register themselves as a side effect of :mod:`i3wm_mcp.server` importing
their module. Nothing else in the suite can see a dropped registration: every
other test calls the tool function directly, so forgetting an import in the
facade would leave a client with fewer tools and the suite still green. This
file is the only thing standing between that mistake and a release.
"""

from __future__ import annotations

from i3wm_mcp import server

EXPECTED_TOOLS = {
    "exec_application",
    "focus_window",
    "get_config",
    "get_focused",
    "get_tree",
    "kill_window",
    "list_outputs",
    "list_workspaces",
    "manage_workspace",
    "move_window",
    "run_command",
    "set_layout",
    "toggle_window_state",
}


async def test_all_tools_are_registered() -> None:
    """Every tool module reached the server, and none registered twice."""
    tools = await server.mcp.list_tools()
    names = [t.name for t in tools]
    assert sorted(names) == sorted(EXPECTED_TOOLS)
    assert len(names) == len(set(names))


def test_every_registered_tool_is_exported_from_the_facade() -> None:
    """`server.<tool>` resolves for each registered tool, so the re-exports match."""
    assert set(server.__all__) == EXPECTED_TOOLS | {"mcp"}
    for name in EXPECTED_TOOLS:
        assert callable(getattr(server, name))
