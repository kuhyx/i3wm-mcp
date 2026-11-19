"""Deploy health check: speak MCP to an installed i3wm-mcp launcher.

Spawns the given command over stdio, runs the MCP handshake, lists the tools
and exits 0 only when the server answers with at least ``--min-tools`` tools.
The handshake does not touch i3, so this works headless and in CI.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def count_tools(command: str) -> int:
    """Return how many tools the server behind ``command`` advertises."""
    params = StdioServerParameters(command=command, args=[])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.list_tools()
        return len(result.tools)


def main() -> int:
    """Parse arguments, run the check, report the tool count."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", help="launcher to spawn, e.g. ~/.local/bin/i3wm-mcp")
    parser.add_argument("--min-tools", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    try:
        count = asyncio.run(asyncio.wait_for(count_tools(args.command), args.timeout))
    except (OSError, TimeoutError) as exc:
        print(f"health: FAIL ({exc!r})", file=sys.stderr)
        return 1
    if count < args.min_tools:
        print(f"health: FAIL ({count} tools < {args.min_tools})", file=sys.stderr)
        return 1
    print(f"health: ok ({count} tools)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
