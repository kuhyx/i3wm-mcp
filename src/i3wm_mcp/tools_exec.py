"""The three destructive tools, kept together so their blast radius is one read.

`exec_application` and `run_command` are open-world (arbitrary payloads) and
`kill_window` can discard unsaved work; every description here states the
consequence in full, because the annotation alone is not what a caller reads.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from . import runtime
from .commands import build_criteria
from .models import CommandResult
from .runtime import DESTRUCTIVE, DESTRUCTIVE_OPEN, mcp


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
    annotations=DESTRUCTIVE_OPEN,
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
    return await runtime.backend.run(f"exec {flag}{command}")


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
    annotations=DESTRUCTIVE_OPEN,
)
async def run_command(
    command: Annotated[
        str,
        Field(min_length=1, max_length=2000, description="Raw i3/Sway command payload to send."),
    ],
) -> CommandResult:
    """Send a raw command payload to i3."""
    return await runtime.backend.run(command)


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
    annotations=DESTRUCTIVE,
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
    criteria = build_criteria(
        window_class=window_class, title=title, instance=instance, mark=mark, con_id=con_id
    )
    command = f"{criteria} kill".strip()
    return await runtime.backend.run(command)
