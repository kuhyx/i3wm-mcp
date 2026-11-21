"""Console entry point: run the i3wm-mcp server over stdio.

Usage::

    python -m i3wm_mcp        # or the installed `i3wm-mcp` script

MCPServer's ``run()`` defaults to the stdio transport, which is what MCP clients
(Claude Code, Claude Desktop, the MCP Inspector) spawn and speak to.
"""

from __future__ import annotations

import argparse

from kuhy_credit import credit_line

from .server import mcp


def main(argv: list[str] | None = None) -> None:
    """Start the MCP server on the stdio transport."""
    parser = argparse.ArgumentParser(
        prog="i3wm-mcp",
        description="Run the i3wm-mcp server over stdio.",
        epilog=credit_line(),
    )
    parser.parse_args(argv)
    mcp.run()


if __name__ == "__main__":  # pragma: no cover - exercised via the process, not imports
    main()
