"""Arrangement tools that act on the focused context rather than on criteria:
workspace operations, container layout, and boolean window state.

None of these take criteria selectors -- they operate on the current workspace
or the focused window -- which is why they sit apart from
:mod:`i3wm_mcp.tools_focus`.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from . import runtime
from .commands import escape
from .models import CommandResult
from .runtime import MUTATE, mcp


@mcp.tool(
    name="manage_workspace",
    title="Manage i3 Workspace",
    description=(
        "Act on workspaces: `switch` to one, `move_container_to` one (optionally following), "
        "`rename` one, or `navigate` next/prev/back_and_forth. Reversible. `action` selects "
        "the operation and determines which of `name`/`new_name`/`direction` are required. "
        "To move a single window rather than switch, use `move_window`; to list workspaces "
        "use `list_workspaces`."
    ),
    annotations=MUTATE,
)
async def manage_workspace(
    action: Annotated[
        Literal["switch", "move_container_to", "rename", "navigate"],
        Field(description="Which workspace operation to perform."),
    ],
    name: Annotated[
        str | None,
        Field(description="Target workspace for switch/move_container_to; old name for rename."),
    ] = None,
    new_name: Annotated[
        str | None, Field(description="New workspace name (required for `rename`).")
    ] = None,
    direction: Annotated[
        Literal["next", "prev", "next_on_output", "prev_on_output", "back_and_forth"] | None,
        Field(description="Navigation direction (required for `navigate`)."),
    ] = None,
    follow: Annotated[
        bool,
        Field(description="For move_container_to, also switch to the target. Default false."),
    ] = False,
) -> CommandResult:
    """Perform the selected workspace operation."""
    if action == "switch":
        if name is None:
            raise ValueError("`switch` requires `name`.")
        command = f'workspace "{escape(name)}"'
    elif action == "move_container_to":
        if name is None:
            raise ValueError("`move_container_to` requires `name`.")
        command = f'move container to workspace "{escape(name)}"'
        if follow:
            command += f'; workspace "{escape(name)}"'
    elif action == "rename":
        if new_name is None:
            raise ValueError("`rename` requires `new_name`.")
        target = f' "{escape(name)}"' if name is not None else ""
        command = f'rename workspace{target} to "{escape(new_name)}"'
    else:  # navigate
        if direction is None:
            raise ValueError("`navigate` requires `direction`.")
        command = f"workspace {direction}"
    return await runtime.backend.run(command)


@mcp.tool(
    name="set_layout",
    title="Set i3 Layout",
    description=(
        "Set how the focused container arranges children: container `layout` "
        "(stacking/tabbed/split*), the `split` orientation for the next window, and/or the "
        "`border` style. Reversible. Provide at least one of layout/split/border; "
        "`border_width` applies only to the `pixel` border. For floating/fullscreen/sticky "
        "state use `toggle_window_state`."
    ),
    annotations=MUTATE,
)
async def set_layout(
    layout: Annotated[
        Literal["stacking", "tabbed", "splith", "splitv", "default", "toggle split"] | None,
        Field(description="Container layout to apply to the focused node."),
    ] = None,
    split: Annotated[
        Literal["horizontal", "vertical", "toggle"] | None,
        Field(description="Split orientation for the next new window."),
    ] = None,
    border: Annotated[
        Literal["normal", "pixel", "none", "toggle"] | None,
        Field(description="Border style for the focused window."),
    ] = None,
    border_width: Annotated[
        int,
        Field(ge=0, le=50, description="Border width in px; used only with border='pixel'."),
    ] = 2,
) -> CommandResult:
    """Apply the requested layout/split/border changes as one payload."""
    commands: list[str] = []
    if layout is not None:
        commands.append(f"layout {layout}")
    if split is not None:
        commands.append(f"split {split}")
    if border is not None:
        commands.append(f"border pixel {border_width}" if border == "pixel" else f"border {border}")
    if not commands:
        raise ValueError("Provide at least one of: layout, split, border.")
    return await runtime.backend.run("; ".join(commands))


@mcp.tool(
    name="toggle_window_state",
    title="Toggle i3 Window State",
    description=(
        "Enable, disable, or toggle one boolean window state — `floating`, `fullscreen`, or "
        "`sticky` — on the focused window. Reversible. Omit `enable` to toggle, or set it "
        "true/false to force. `fullscreen_scope` picks per-output ('normal') vs across-all "
        "('global'). For layout/border changes use `set_layout`."
    ),
    annotations=MUTATE,
)
async def toggle_window_state(
    state: Annotated[
        Literal["floating", "fullscreen", "sticky"],
        Field(description="Which boolean window state to change."),
    ],
    enable: Annotated[
        bool | None,
        Field(description="true=enable, false=disable, omitted=toggle."),
    ] = None,
    fullscreen_scope: Annotated[
        Literal["normal", "global"],
        Field(description="Fullscreen scope when state='fullscreen'. Default 'normal'."),
    ] = "normal",
) -> CommandResult:
    """Set or toggle the requested window state."""
    verb = "toggle" if enable is None else ("enable" if enable else "disable")
    if state == "fullscreen":
        suffix = " global" if fullscreen_scope == "global" else ""
        command = f"fullscreen {verb}{suffix}"
    else:
        command = f"{state} {verb}"
    return await runtime.backend.run(command)
