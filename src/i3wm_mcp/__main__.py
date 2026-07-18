"""Console entry point: run the i3wm-mcp server over stdio.

Usage::

    python -m i3wm_mcp        # or the installed `i3wm-mcp` script

FastMCP's ``run()`` defaults to the stdio transport, which is what MCP clients
(Claude Code, Claude Desktop, the MCP Inspector) spawn and speak to.
"""

from __future__ import annotations

from .server import mcp


def main() -> None:
    """Start the MCP server on the stdio transport."""
    mcp.run()


if __name__ == "__main__":  # pragma: no cover - exercised via the process, not imports
    main()
