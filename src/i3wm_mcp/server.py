"""The i3wm-mcp FastMCP server: 13 tool definitions over the i3/Sway IPC.

Design choices that matter for tool-definition quality:

* **Flat parameters.** Tools take ``Annotated[T, Field(description=...)]``
  arguments, not a single wrapper model, so every parameter is a described,
  top-level entry in the ``inputSchema``.
* **Typed returns.** Every tool returns a pydantic model from :mod:`.models`, so
  FastMCP emits an ``outputSchema`` and the description need not restate the
  return shape.
* **Honest annotations.** ``readOnlyHint``/``destructiveHint`` reflect real
  behaviour and never contradict the prose description.
* **Consolidated surface.** Rarely-used verbs (marks, gaps, i3bar, scratchpad
  show/hide, reload/restart) are reached through the guarded ``run_command``
  escape hatch rather than dedicated tools, keeping the set small and distinct.

The module-level :data:`backend` is the single i3 gateway; tests replace it with
an :class:`~i3wm_mcp.backend.I3Backend` wired to a fake connection.
"""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__
from .backend import I3Backend
from .formatting import (
    collect_windows,
    find_focused,
    output_to_info,
    workspace_to_info,
)
from .models import (
    CommandResult,
    ConfigResult,
    Direction,
    FocusedResult,
    OutputListResult,
    TreeResult,
    WorkspaceListResult,
)

mcp = FastMCP("i3wm-mcp")
# FastMCP has no version parameter; set the advertised server version directly so
# clients see our package version rather than the mcp library's.
mcp._mcp_server.version = __version__

# Single i3 gateway. Reassigned by tests to point at a fake connection.
backend: I3Backend = I3Backend()

# Annotation presets ---------------------------------------------------------
_READ = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
_MUTATE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
)
_MUTATE_IDEMPOTENT = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
_DESTRUCTIVE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
)
_DESTRUCTIVE_OPEN = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True
)


# -- Command-string helpers --------------------------------------------------


def _escape(value: str) -> str:
    """Escape a value for use inside an i3 criteria double-quoted string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _criteria(
    *,
    window_class: str | None = None,
    title: str | None = None,
    instance: str | None = None,
    mark: str | None = None,
    con_id: int | None = None,
) -> str:
    """Build an i3 ``[...]`` criteria selector, or '' when no field is given."""
    parts: list[str] = []
    if con_id is not None:
        parts.append(f"con_id={int(con_id)}")
    if mark is not None:
        parts.append(f'con_mark="{_escape(mark)}"')
    if window_class is not None:
        parts.append(f'class="{_escape(window_class)}"')
    if instance is not None:
        parts.append(f'instance="{_escape(instance)}"')
    if title is not None:
        parts.append(f'title="{_escape(title)}"')
    return f"[{' '.join(parts)}]" if parts else ""


def _require_exactly_one(**named: bool) -> str:
    """Return the single truthy option name, or raise if not exactly one is set."""
    chosen = [name for name, present in named.items() if present]
    if len(chosen) != 1:
        options = ", ".join(named)
        raise ValueError(f"Provide exactly one of: {options} (got {len(chosen)}).")
    return chosen[0]


# -- Read tools --------------------------------------------------------------


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
    annotations=_READ,
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
    root = await backend.get_tree()
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
    annotations=_READ,
)
async def get_focused() -> FocusedResult:
    """Return the focused window, or a null result when none is focused."""
    root = await backend.get_tree()
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
    annotations=_READ,
)
async def list_workspaces() -> WorkspaceListResult:
    """Return all active workspaces."""
    workspaces = [workspace_to_info(ws) for ws in await backend.get_workspaces()]
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
    annotations=_READ,
)
async def list_outputs() -> OutputListResult:
    """Return all display outputs."""
    outputs = [output_to_info(o) for o in await backend.get_outputs()]
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
    annotations=_READ,
)
async def get_config(
    include_config_text: Annotated[
        bool,
        Field(description="Include the full config file text (can be large). Default true."),
    ] = True,
) -> ConfigResult:
    """Return a version + configuration snapshot."""
    version = await backend.get_version()
    human = str(getattr(version, "human_readable", "") or "")
    config_text: str | None = None
    if include_config_text:
        config_reply = await backend.get_config()
        config_text = getattr(config_reply, "config", None)
    return ConfigResult(
        version=human,
        is_sway="sway" in human.lower(),
        loaded_config_path=getattr(version, "loaded_config_file_name", None),
        config_text=config_text,
        binding_modes=await backend.get_binding_modes(),
        active_binding_mode=await backend.get_binding_state(),
    )


# -- Non-destructive mutation tools -----------------------------------------


@mcp.tool(
    name="focus_window",
    title="Focus i3 Window",
    description=(
        "Move keyboard focus, selected by exactly one of: a direction; a specific window "
        "(class/title/instance/mark/con_id criteria); the parent/child container; the "
        "floating/tiling layer; or an output. Reversible. Supplying none or several "
        "selectors is rejected. To *move* the focused window instead of focusing, use "
        "`move_window`."
    ),
    annotations=_MUTATE_IDEMPOTENT,
)
async def focus_window(
    direction: Annotated[
        Direction | None, Field(description="Focus the neighbour in this direction.")
    ] = None,
    window_class: Annotated[
        str | None, Field(description="Focus a window whose X11 class matches (criteria).")
    ] = None,
    title: Annotated[
        str | None, Field(description="Focus a window whose title matches (criteria).")
    ] = None,
    instance: Annotated[
        str | None, Field(description="Focus a window whose WM_CLASS instance matches (criteria).")
    ] = None,
    mark: Annotated[
        str | None, Field(description="Focus the window carrying this mark (criteria).")
    ] = None,
    con_id: Annotated[
        int | None, Field(description="Focus the container with this exact i3 id (criteria).")
    ] = None,
    target: Annotated[
        Literal["parent", "child"] | None,
        Field(description="Focus the parent or child container of the current focus."),
    ] = None,
    layer: Annotated[
        Literal["floating", "tiling", "mode_toggle"] | None,
        Field(description="Focus the floating layer, the tiling layer, or toggle between them."),
    ] = None,
) -> CommandResult:
    """Focus a window/container per exactly one selector."""
    criteria = _criteria(
        window_class=window_class, title=title, instance=instance, mark=mark, con_id=con_id
    )
    kind = _require_exactly_one(
        direction=direction is not None,
        criteria=bool(criteria),
        target=target is not None,
        layer=layer is not None,
    )
    if kind == "direction":
        command = f"focus {direction}"
    elif kind == "criteria":
        command = f"{criteria} focus"
    elif kind == "target":
        command = f"focus {target}"
    else:
        command = f"focus {layer}"
    return await backend.run(command)


@mcp.tool(
    name="move_window",
    title="Move i3 Window",
    description=(
        "Move the focused container (or one matched by class/title/instance/mark/con_id) to "
        "exactly one destination: a direction (with pixel amount), a workspace, an output, "
        "the scratchpad, or a screen position (center). Reversible; returns per-command "
        "success. To change *focus* rather than move, use `focus_window`; to move whole "
        "workspaces between monitors, use `manage_workspace`."
    ),
    annotations=_MUTATE,
)
async def move_window(
    direction: Annotated[
        Direction | None, Field(description="Move the container this direction.")
    ] = None,
    amount_px: Annotated[
        int,
        Field(ge=1, le=2000, description="Pixels to move when `direction` is set. Default 10."),
    ] = 10,
    to_workspace: Annotated[
        str | None, Field(description="Move the container to this workspace (name or number).")
    ] = None,
    to_output: Annotated[
        str | None, Field(description="Move the container to this output, e.g. 'HDMI-1'.")
    ] = None,
    to_scratchpad: Annotated[
        bool, Field(description="Move the container to the scratchpad. Default false.")
    ] = False,
    to_center: Annotated[
        bool, Field(description="Center a floating container on its output. Default false.")
    ] = False,
    window_class: Annotated[
        str | None, Field(description="Select the window to move by X11 class (criteria).")
    ] = None,
    title: Annotated[
        str | None, Field(description="Select the window to move by title (criteria).")
    ] = None,
    instance: Annotated[
        str | None, Field(description="Select the window to move by WM_CLASS instance (criteria).")
    ] = None,
    mark: Annotated[
        str | None, Field(description="Select the window to move by mark (criteria).")
    ] = None,
    con_id: Annotated[
        int | None, Field(description="Select the window to move by exact i3 id (criteria).")
    ] = None,
) -> CommandResult:
    """Move a container to exactly one destination."""
    # Validate the "exactly one destination" rule, then branch on the actual
    # values so the type checker can narrow away the Optionals.
    _require_exactly_one(
        direction=direction is not None,
        to_workspace=to_workspace is not None,
        to_output=to_output is not None,
        to_scratchpad=to_scratchpad,
        to_center=to_center,
    )
    if direction is not None:
        action = f"move {direction} {amount_px} px"
    elif to_workspace is not None:
        action = f'move container to workspace "{_escape(to_workspace)}"'
    elif to_output is not None:
        action = f'move container to output "{_escape(to_output)}"'
    elif to_scratchpad:
        action = "move to scratchpad"
    else:  # to_center is the only remaining valid option
        action = "move position center"
    criteria = _criteria(
        window_class=window_class, title=title, instance=instance, mark=mark, con_id=con_id
    )
    command = f"{criteria} {action}".strip()
    return await backend.run(command)


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
    annotations=_MUTATE,
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
        command = f'workspace "{_escape(name)}"'
    elif action == "move_container_to":
        if name is None:
            raise ValueError("`move_container_to` requires `name`.")
        command = f'move container to workspace "{_escape(name)}"'
        if follow:
            command += f'; workspace "{_escape(name)}"'
    elif action == "rename":
        if new_name is None:
            raise ValueError("`rename` requires `new_name`.")
        target = f' "{_escape(name)}"' if name is not None else ""
        command = f'rename workspace{target} to "{_escape(new_name)}"'
    else:  # navigate
        if direction is None:
            raise ValueError("`navigate` requires `direction`.")
        command = f"workspace {direction}"
    return await backend.run(command)


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
    annotations=_MUTATE,
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
    return await backend.run("; ".join(commands))


@mcp.tool(
    name="toggle_window_state",
    title="Toggle i3 Window State",
    description=(
        "Enable, disable, or toggle one boolean window state — `floating`, `fullscreen`, or "
        "`sticky` — on the focused window. Reversible. Omit `enable` to toggle, or set it "
        "true/false to force. `fullscreen_scope` picks per-output ('normal') vs across-all "
        "('global'). For layout/border changes use `set_layout`."
    ),
    annotations=_MUTATE,
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
    return await backend.run(command)


# -- Destructive tools -------------------------------------------------------


@mcp.tool(
    name="exec_application",
    title="Launch Application (i3 exec)",
    description=(
        "Launch an external program via i3's `exec`. DESTRUCTIVE / open-world: runs an "
        "arbitrary command line on the user's machine with their privileges — never pass "
        "untrusted input. Set `no_startup_id=true` for programs without startup-notification "
        "support (avoids a lingering busy cursor). For built-in i3 verbs use the dedicated "
        "tools instead — `focus_window`, `move_window`, `set_layout` — not this."
    ),
    annotations=_DESTRUCTIVE_OPEN,
)
async def exec_application(
    command: Annotated[
        str,
        Field(min_length=1, max_length=1000, description="The shell command line to launch."),
    ],
    no_startup_id: Annotated[
        bool,
        Field(description="Pass i3's --no-startup-id flag. Default false."),
    ] = False,
) -> CommandResult:
    """Launch a program via i3 exec."""
    flag = "--no-startup-id " if no_startup_id else ""
    return await backend.run(f"exec {flag}{command}")


@mcp.tool(
    name="run_command",
    title="Run Raw i3 Command",
    description=(
        "Run a raw i3/Sway command string — the escape hatch for operations without a "
        "dedicated tool: marks (`mark`/`unmark`), i3-gaps (`gaps ...`), i3bar (`bar ...`), "
        "scratchpad show/hide, and `reload`/`restart`. DESTRUCTIVE / open-world: the payload "
        "is unrestricted and CAN include `kill`, `restart`, `reload`, or `exit` (which logs "
        "the user out), so validate before sending. Prefer the typed tools (`focus_window`, "
        "`move_window`, `set_layout`, ...) whenever one fits."
    ),
    annotations=_DESTRUCTIVE_OPEN,
)
async def run_command(
    command: Annotated[
        str,
        Field(min_length=1, max_length=2000, description="Raw i3/Sway command payload to send."),
    ],
) -> CommandResult:
    """Send a raw command payload to i3."""
    return await backend.run(command)


@mcp.tool(
    name="kill_window",
    title="Close i3 Window",
    description=(
        "Close a window — the focused one, or one matched by class/title/instance/mark/"
        "con_id. DESTRUCTIVE: the target application is asked to quit and may discard unsaved "
        "work; there is no undo, and matching several windows closes all of them. To move a "
        "window out of the way instead of closing it, use `move_window` (e.g. to the "
        "scratchpad)."
    ),
    annotations=_DESTRUCTIVE,
)
async def kill_window(
    window_class: Annotated[
        str | None, Field(description="Close windows whose X11 class matches (criteria).")
    ] = None,
    title: Annotated[
        str | None, Field(description="Close windows whose title matches (criteria).")
    ] = None,
    instance: Annotated[
        str | None, Field(description="Close windows whose WM_CLASS instance matches (criteria).")
    ] = None,
    mark: Annotated[
        str | None, Field(description="Close the window carrying this mark (criteria).")
    ] = None,
    con_id: Annotated[
        int | None, Field(description="Close the container with this exact i3 id (criteria).")
    ] = None,
) -> CommandResult:
    """Close the focused window, or those matched by criteria."""
    criteria = _criteria(
        window_class=window_class, title=title, instance=instance, mark=mark, con_id=con_id
    )
    command = f"{criteria} kill".strip()
    return await backend.run(command)
