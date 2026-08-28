"""The i3wm-mcp server: 13 tool definitions over the i3/Sway IPC.

Design choices that matter for tool-definition quality:

* **Flat parameters.** Tools take ``Annotated[T, Field(description=...)]``
  arguments, not a single wrapper model, so every parameter is a described,
  top-level entry in the ``inputSchema``.
* **Typed returns.** Every tool returns a pydantic model from :mod:`.models`, so
  MCPServer emits an ``outputSchema`` and the description need not restate the
  return shape.
* **Honest annotations.** ``read_only_hint``/``destructive_hint`` reflect real
  behaviour and never contradict the prose description.
* **Consolidated surface.** Rarely-used verbs (marks, gaps, i3bar, scratchpad
  show/hide, reload/restart) are reached through the guarded ``run_command``
  escape hatch rather than dedicated tools, keeping the set small and distinct.

This module is a facade. The tools live in four sibling modules grouped by blast
radius -- :mod:`.tools_read`, :mod:`.tools_focus`, :mod:`.tools_layout`,
:mod:`.tools_exec` -- and register themselves on the shared :data:`.runtime.mcp`
server as a side effect of being imported here. Importing all four is therefore
load-bearing, not tidiness: a missing import silently drops tools from the
advertised set, which is what ``tests/test_registry.py`` exists to catch.

The i3 gateway is :data:`i3wm_mcp.runtime.backend`; tests replace *that* name,
not one re-exported here, so a stale alias cannot absorb the patch.
"""

from __future__ import annotations

from .runtime import mcp
from .tools_exec import exec_application, kill_window, run_command
from .tools_focus import focus_window, move_window
from .tools_layout import manage_workspace, set_layout, toggle_window_state
from .tools_read import get_config, get_focused, get_tree, list_outputs, list_workspaces

__all__ = [
    "exec_application",
    "focus_window",
    "get_config",
    "get_focused",
    "get_tree",
    "kill_window",
    "list_outputs",
    "list_workspaces",
    "manage_workspace",
    "mcp",
    "move_window",
    "run_command",
    "set_layout",
    "toggle_window_state",
]
