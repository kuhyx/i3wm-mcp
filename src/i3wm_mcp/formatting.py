"""Pure shaping helpers: i3ipc objects -> our pydantic models.

Everything here is deliberately duck-typed (``getattr`` with defaults) so the
functions work both with real :mod:`i3ipc` objects and with the lightweight
fakes used in tests. No function in this module performs I/O.
"""

from __future__ import annotations

import re
from typing import Any

from .models import OutputInfo, WindowInfo, WorkspaceInfo

# Cap on how many windows a single tree query returns, to keep responses small
# for the model. Callers receive ``truncated=True`` when this bites.
MAX_WINDOWS = 200

# Node types that are structural (never a user-facing application window).
_STRUCTURAL_TYPES = {"root", "output", "workspace", "dockarea"}


def _rect(obj: Any) -> dict[str, int] | None:
    """Extract an i3 rect object into a plain ``{x,y,width,height}`` dict."""
    rect = getattr(obj, "rect", None)
    if rect is None:
        return None
    try:
        return {
            "x": int(rect.x),
            "y": int(rect.y),
            "width": int(rect.width),
            "height": int(rect.height),
        }
    except (AttributeError, TypeError, ValueError):  # pragma: no cover - defensive
        return None


def _is_floating(con: Any) -> bool:
    """Interpret i3ipc's ``floating`` string ('user_on'/'auto_off'/...) as a bool."""
    value = getattr(con, "floating", None)
    return bool(value) and str(value).endswith("_on")


def _is_fullscreen(con: Any) -> bool:
    """A non-zero ``fullscreen_mode`` means the container is fullscreen."""
    return bool(getattr(con, "fullscreen_mode", 0))


def _is_window(con: Any) -> bool:
    """Whether a tree node is an actual application window (vs. a split/container)."""
    if getattr(con, "window", None) is not None:
        return True
    return getattr(con, "app_id", None) is not None


def con_to_window(
    con: Any, *, workspace: str | None = None, output: str | None = None
) -> WindowInfo:
    """Convert an i3ipc container into a :class:`WindowInfo`."""
    return WindowInfo(
        id=int(getattr(con, "id", 0)),
        name=getattr(con, "name", None),
        type=getattr(con, "type", None),
        window_class=getattr(con, "window_class", None),
        window_instance=getattr(con, "window_instance", None),
        app_id=getattr(con, "app_id", None),
        window_role=getattr(con, "window_role", None),
        marks=list(getattr(con, "marks", []) or []),
        focused=bool(getattr(con, "focused", False)),
        urgent=bool(getattr(con, "urgent", False)),
        floating=_is_floating(con),
        fullscreen=_is_fullscreen(con),
        layout=getattr(con, "layout", None),
        workspace=workspace,
        output=output,
        rect=_rect(con),
        pid=getattr(con, "pid", None),
    )


def _matches(window: WindowInfo, con: Any, filters: dict[str, Any]) -> bool:
    """Return True if a window satisfies every provided filter.

    String filters are treated as case-insensitive regular expressions matched
    against the relevant field; ``floating``/``urgent`` are exact booleans;
    ``workspace`` matches the owning workspace name.
    """
    checks: list[tuple[Any, str | None]] = [
        (filters.get("window_class"), window.window_class),
        (filters.get("title"), window.name),
        (filters.get("instance"), window.window_instance),
        (filters.get("role"), window.window_role),
    ]
    for pattern, value in checks:
        if pattern is not None and (value is None or not re.search(pattern, value, re.IGNORECASE)):
            return False

    ws_filter = filters.get("workspace")
    if ws_filter is not None and (
        window.workspace is None or not re.search(ws_filter, window.workspace, re.IGNORECASE)
    ):
        return False

    if filters.get("floating") is not None and window.floating is not filters["floating"]:
        return False
    return not (filters.get("urgent") is not None and window.urgent is not filters["urgent"])


def collect_windows(root: Any, filters: dict[str, Any]) -> tuple[list[WindowInfo], bool]:
    """Walk the tree from ``root``, returning matching windows and a truncated flag.

    The walk tracks the current output and workspace names as it descends, so
    each :class:`WindowInfo` is annotated with its location without relying on
    i3ipc parent back-references.
    """
    matched: list[WindowInfo] = []
    truncated = False

    def walk(node: Any, output: str | None, workspace: str | None) -> None:
        nonlocal truncated
        node_type = getattr(node, "type", None)
        name = getattr(node, "name", None)
        if node_type == "dockarea":
            # Dock windows (i3bar, panels) live here; they are not user windows.
            return
        if node_type == "output":
            output = name
        elif node_type == "workspace":
            workspace = name

        if node_type not in _STRUCTURAL_TYPES and _is_window(node):
            window = con_to_window(node, workspace=workspace, output=output)
            if _matches(window, node, filters):
                if len(matched) >= MAX_WINDOWS:
                    truncated = True
                    return
                matched.append(window)

        for child in list(getattr(node, "nodes", []) or []):
            walk(child, output, workspace)
        for child in list(getattr(node, "floating_nodes", []) or []):
            walk(child, output, workspace)

    walk(root, None, None)
    return matched, truncated


def find_focused(root: Any) -> WindowInfo | None:
    """Return the focused window from the tree, or None if nothing is focused."""
    windows, _ = collect_windows(root, {})
    for window in windows:
        if window.focused:
            return window
    return None


def workspace_to_info(ws: Any) -> WorkspaceInfo:
    """Convert an i3ipc workspace reply into a :class:`WorkspaceInfo`."""
    return WorkspaceInfo(
        num=int(getattr(ws, "num", -1)),
        name=str(getattr(ws, "name", "")),
        visible=bool(getattr(ws, "visible", False)),
        focused=bool(getattr(ws, "focused", False)),
        urgent=bool(getattr(ws, "urgent", False)),
        output=getattr(ws, "output", None),
    )


def output_to_info(out: Any) -> OutputInfo:
    """Convert an i3ipc output reply into an :class:`OutputInfo`."""
    return OutputInfo(
        name=str(getattr(out, "name", "")),
        active=bool(getattr(out, "active", False)),
        primary=bool(getattr(out, "primary", False)),
        current_workspace=getattr(out, "current_workspace", None),
        rect=_rect(out),
    )
