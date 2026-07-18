"""Pydantic output models and shared enums for the i3wm-mcp tools.

Every tool returns one of these models. FastMCP turns the return annotation into
the tool's ``outputSchema``, so the ``Field(description=...)`` text here is part
of the machine-readable contract the model sees — it documents *return* shape
without the human description having to spell it out.

Input parameters are intentionally *not* modelled here: tools declare flat
``Annotated[T, Field(...)]`` arguments so each parameter appears as a described,
top-level entry in the tool's ``inputSchema`` (better parameter-schema coverage
than a single nested wrapper object).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# -- Shared enums / literals -------------------------------------------------

Direction = Literal["left", "right", "up", "down"]
"""A cardinal direction used for focus and move commands."""

Rect = dict[str, int]
"""An i3 geometry rectangle: ``{x, y, width, height}`` in pixels."""


# -- Command result models ---------------------------------------------------


class CommandOutcome(BaseModel):
    """The result of a single i3 command within a (possibly chained) payload."""

    success: bool = Field(description="Whether this individual i3 command succeeded.")
    error: str | None = Field(
        default=None,
        description="i3's error message for this command, or null when it succeeded.",
    )


class CommandResult(BaseModel):
    """Roll-up returned by every mutating tool.

    ``success`` is the AND of every command's outcome; ``error`` is the first
    failure message (null when everything succeeded). ``outcomes`` preserves the
    per-command detail for chained payloads.
    """

    success: bool = Field(description="True only if every command in the payload succeeded.")
    error: str | None = Field(
        default=None,
        description="First error message across the payload, or null on full success.",
    )
    outcomes: list[CommandOutcome] = Field(
        default_factory=list,
        description="Per-command outcomes, in payload order.",
    )


# -- Query result models -----------------------------------------------------


class WindowInfo(BaseModel):
    """A single window/container distilled from the i3 layout tree."""

    id: int = Field(description="i3 container id (con_id); stable while the window lives.")
    name: str | None = Field(default=None, description="Container/window title as i3 reports it.")
    type: str | None = Field(default=None, description="Node type, e.g. 'con', 'floating_con'.")
    window_class: str | None = Field(
        default=None, description="X11 WM_CLASS class (null on Wayland windows)."
    )
    window_instance: str | None = Field(
        default=None, description="X11 WM_CLASS instance (null on Wayland windows)."
    )
    app_id: str | None = Field(
        default=None, description="Wayland app_id — the Sway analogue of window_class."
    )
    window_role: str | None = Field(default=None, description="X11 window role, if set.")
    marks: list[str] = Field(default_factory=list, description="Marks attached to this container.")
    focused: bool = Field(default=False, description="Whether this container currently has focus.")
    urgent: bool = Field(default=False, description="Whether the urgency hint is set.")
    floating: bool = Field(default=False, description="Whether the container is floating.")
    fullscreen: bool = Field(default=False, description="Whether the container is fullscreen.")
    layout: str | None = Field(default=None, description="Layout of this node, e.g. 'splith'.")
    workspace: str | None = Field(default=None, description="Name of the owning workspace, if any.")
    output: str | None = Field(default=None, description="Name of the owning output, if known.")
    rect: Rect | None = Field(default=None, description="Geometry {x,y,width,height} in pixels.")
    pid: int | None = Field(default=None, description="Process id backing the window, if known.")


class TreeResult(BaseModel):
    """Windows matched from the layout tree, plus a match count."""

    count: int = Field(description="Number of windows matching the requested filters.")
    windows: list[WindowInfo] = Field(description="Matching leaf windows, in tree order.")
    truncated: bool = Field(
        default=False,
        description="True if the result was trimmed to stay under the size limit.",
    )


class FocusedResult(BaseModel):
    """The currently focused window, or an explicit 'nothing focused' signal."""

    focused: WindowInfo | None = Field(
        description="The focused window, or null when no window holds focus."
    )


class WorkspaceInfo(BaseModel):
    """One workspace as reported by ``GET_WORKSPACES``."""

    num: int = Field(description="Workspace number (-1 for un-numbered named workspaces).")
    name: str = Field(description="Workspace name as shown in the bar.")
    visible: bool = Field(description="Whether the workspace is currently visible on its output.")
    focused: bool = Field(description="Whether the workspace is the focused one.")
    urgent: bool = Field(description="Whether the workspace has the urgency hint set.")
    output: str | None = Field(default=None, description="Output this workspace lives on.")


class WorkspaceListResult(BaseModel):
    """All active workspaces."""

    count: int = Field(description="Number of active workspaces.")
    workspaces: list[WorkspaceInfo] = Field(description="Active workspaces, in i3 order.")


class OutputInfo(BaseModel):
    """One output (monitor) as reported by ``GET_OUTPUTS``."""

    name: str = Field(description="Output name, e.g. 'HDMI-1', 'eDP-1', 'DP-2'.")
    active: bool = Field(description="Whether the output is currently active.")
    primary: bool = Field(description="Whether this is the primary output.")
    current_workspace: str | None = Field(
        default=None, description="Workspace currently shown on this output."
    )
    rect: Rect | None = Field(default=None, description="Output geometry {x,y,width,height}.")


class OutputListResult(BaseModel):
    """All display outputs (monitors)."""

    count: int = Field(description="Number of outputs reported.")
    outputs: list[OutputInfo] = Field(description="Outputs, in i3 order.")


class ConfigResult(BaseModel):
    """A single-call snapshot of i3's version and configuration state."""

    version: str = Field(description="Human-readable i3/Sway version, e.g. '4.25.1'.")
    is_sway: bool = Field(description="True when the running compositor identifies as Sway.")
    loaded_config_path: str | None = Field(
        default=None, description="Path of the loaded config file, if reported."
    )
    config_text: str | None = Field(
        default=None,
        description="Full text of the loaded config, or null when not requested.",
    )
    binding_modes: list[str] = Field(
        default_factory=list, description="Names of all configured binding modes."
    )
    active_binding_mode: str | None = Field(
        default=None,
        description="Currently active binding mode name, or null if unsupported by the WM.",
    )
