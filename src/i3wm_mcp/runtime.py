"""The server object, the i3 gateway, and the shared tool-annotation presets.

Everything here is process-wide state that the tool modules need but that would
create an import cycle if it lived in :mod:`i3wm_mcp.server` (the facade imports
the tool modules, so the tool modules cannot import the facade).

The module-level :data:`backend` is the single i3 gateway. Tests replace it with
an :class:`~i3wm_mcp.backend.I3Backend` wired to a fake connection, so tool
modules must reach it as ``runtime.backend`` at call time -- a
``from .runtime import backend`` would bind the object at import time and never
see the replacement.
"""

from __future__ import annotations

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from . import __version__
from .backend import I3Backend

# mcp 2.x renamed FastMCP to MCPServer and gave it a real `version` argument,
# so the advertised version no longer has to be poked into a private attribute.
mcp = MCPServer("i3wm-mcp", version=__version__)

# Single i3 gateway. Reassigned by tests to point at a fake connection.
backend: I3Backend = I3Backend()

# Annotation presets ---------------------------------------------------------
READ = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)
MUTATE = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False
)
MUTATE_IDEMPOTENT = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)
DESTRUCTIVE = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False
)
DESTRUCTIVE_OPEN = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True
)
