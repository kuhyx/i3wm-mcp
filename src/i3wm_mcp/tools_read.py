"""Read-only tools: layout tree, focus, workspaces, outputs, configuration.

Every tool here carries :data:`~i3wm_mcp.runtime.READ` and an explicit
"Read-only." in its prose, which is what keeps the annotation and the
description from contradicting each other.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from . import runtime
from .formatting import collect_windows, find_focused, output_to_info, workspace_to_info
from .models import (
    ConfigResult,
    FocusedResult,
    OutputListResult,
    TreeResult,
    WorkspaceListResult,
)
from .runtime import READ, mcp


@mcp.tool(
    name="get_tree",
    title="Query i3 Layout Tree",
    description=(
        "List application windows from the i3/Sway layout tree, optionally filtered by "
        "class, title, instance, role, workspace, or floating/urgent state. Read-only. "
        "Returns matched leaf windows with their ids, marks and location; use a returned "
        "`id` as `con_id` in focus_window/move_window/kill_window. For only the active "
        "window use `get_focused`; for a flat workspace summary use `list_workspaces`; "
        "for monitors use `list_outputs`. Capped at 200 windows (`truncated` flags the cap)."
    ),
    annotations=READ,
)
async def get_tree(
    window_class: Annotated[
        str | None, Field(description="Case-insensitive regex on the window's X11 class.")
    ] = None,
    title: Annotated[
        str | None, Field(description="Case-insensitive regex on the window title/name.")
    ] = None,
    instance: Annotated[
        str | None, Field(description="Case-insensitive regex on the X11 WM_CLASS instance.")
    ] = None,
    role: Annotated[
        str | None, Field(description="Case-insensitive regex on the X11 window role.")
    ] = None,
    workspace: Annotated[
        str | None, Field(description="Case-insensitive regex on the owning workspace name.")
    ] = None,
    floating: Annotated[
        bool | None, Field(description="If set, keep only floating (true) or tiled (false).")
    ] = None,
    urgent: Annotated[
        bool | None, Field(description="If set, keep only windows with the urgency hint = value.")
    ] = None,
) -> TreeResult:
    """Return windows from the layout tree matching the given filters."""
    root = await runtime.backend.get_tree()
    windows, truncated = collect_windows(
        root,
        {
            "window_class": window_class,
            "title": title,
            "instance": instance,
            "role": role,
            "workspace": workspace,
            "floating": floating,
            "urgent": urgent,
        },
    )
    return TreeResult(count=len(windows), windows=windows, truncated=truncated)


@mcp.tool(
    name="get_focused",
    title="Get Focused i3 Window",
    description=(
        "Get the single currently-focused window's details (class/app_id, title, marks, "
        "geometry, workspace, output). Read-only, no parameters. Use this instead of "
        "scanning `get_tree` when you only need the active window; returns `focused: null` "
        "when nothing holds focus, e.g. on an empty workspace."
    ),
    annotations=READ,
)
async def get_focused() -> FocusedResult:
    """Return the focused window, or a null result when none is focused."""
    root = await runtime.backend.get_tree()
    return FocusedResult(focused=find_focused(root))


@mcp.tool(
    name="list_workspaces",
    title="List i3 Workspaces",
    description=(
        "List all active workspaces with number, name, visibility, focus, urgency and "
        "owning output. Read-only. Use this for navigation decisions; for the windows on a "
        "workspace use `get_tree` with a `workspace` filter, and for monitors use "
        "`list_outputs`."
    ),
    annotations=READ,
)
async def list_workspaces() -> WorkspaceListResult:
    """Return all active workspaces."""
    workspaces = [workspace_to_info(ws) for ws in await runtime.backend.get_workspaces()]
    return WorkspaceListResult(count=len(workspaces), workspaces=workspaces)


@mcp.tool(
    name="list_outputs",
    title="List i3 Outputs",
    description=(
        "List display outputs (monitors): name, active/primary state, current workspace and "
        "geometry. Read-only. Use before moving windows or workspaces between monitors with "
        "`move_window` or `manage_workspace`; for the workspaces themselves use "
        "`list_workspaces`."
    ),
    annotations=READ,
)
async def list_outputs() -> OutputListResult:
    """Return all display outputs."""
    outputs = [output_to_info(o) for o in await runtime.backend.get_outputs()]
    return OutputListResult(count=len(outputs), outputs=outputs)


@mcp.tool(
    name="get_config",
    title="Inspect i3 Configuration",
    description=(
        "Inspect i3/Sway configuration state in one call: version, whether the compositor is "
        "Sway, the loaded config path and (optionally) its full text, plus configured and "
        "active binding modes. Read-only. Set `include_config_text=false` to skip the "
        "potentially large config body. This is the only config-introspection tool; live "
        "layout comes from `get_tree`."
    ),
    annotations=READ,
)
async def get_config(
    include_config_text: Annotated[
        bool,
        Field(description="Include the full config file text (can be large). Default true."),
    ] = True,
) -> ConfigResult:
    """Return a version + configuration snapshot."""
    version = await runtime.backend.get_version()
    human = str(getattr(version, "human_readable", "") or "")
    config_text: str | None = None
    if include_config_text:
        config_reply = await runtime.backend.get_config()
        config_text = getattr(config_reply, "config", None)
    return ConfigResult(
        version=human,
        is_sway="sway" in human.lower(),
        loaded_config_path=getattr(version, "loaded_config_file_name", None),
        config_text=config_text,
        binding_modes=await runtime.backend.get_binding_modes(),
        active_binding_mode=await runtime.backend.get_binding_state(),
    )
