"""The two selector-driven placement tools: `focus_window` and `move_window`.

Both take the same five criteria fields and both enforce an "exactly one"
rule -- one selector for focus, one destination for move -- so they share
:mod:`i3wm_mcp.commands` and belong together.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from . import runtime
from .commands import build_criteria, escape, require_exactly_one
from .models import CommandResult, Direction
from .runtime import MUTATE, MUTATE_IDEMPOTENT, mcp


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
    annotations=MUTATE_IDEMPOTENT,
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
    criteria = build_criteria(
        window_class=window_class, title=title, instance=instance, mark=mark, con_id=con_id
    )
    kind = require_exactly_one(
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
    return await runtime.backend.run(command)


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
    annotations=MUTATE,
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
    require_exactly_one(
        direction=direction is not None,
        to_workspace=to_workspace is not None,
        to_output=to_output is not None,
        to_scratchpad=to_scratchpad,
        to_center=to_center,
    )
    if direction is not None:
        action = f"move {direction} {amount_px} px"
    elif to_workspace is not None:
        action = f'move container to workspace "{escape(to_workspace)}"'
    elif to_output is not None:
        action = f'move container to output "{escape(to_output)}"'
    elif to_scratchpad:
        action = "move to scratchpad"
    else:  # to_center is the only remaining valid option
        action = "move position center"
    criteria = build_criteria(
        window_class=window_class, title=title, instance=instance, mark=mark, con_id=con_id
    )
    command = f"{criteria} {action}".strip()
    return await runtime.backend.run(command)
