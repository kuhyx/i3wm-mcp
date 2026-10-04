# Needs the host's i3/Sway IPC socket and X11 DISPLAY to reach the running
# window manager (see README "Requirements"). Run with:
#   docker run --network host \
#     -e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix \
#     -v "$I3SOCK:$I3SOCK" -e I3SOCK \
#     i3wm-mcp
FROM python:3.13-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY . .
# pyproject.toml pins only mcp>=1.12 with no lockfile, so a fresh resolve
# can land on a release with breaking API changes (mcp 2.0.0 dropped
# mcp.server.fastmcp.FastMCP, which server.py imports). Pin to the version
# already verified working in the host venv (~/i3wm-mcp/.venv). Invoke the
# venv's python directly rather than `uv run`, which re-syncs against
# pyproject.toml's looser bound on every invocation and would silently
# undo this pin at container start.
RUN uv sync --no-dev && uv pip install "mcp==1.28.1"

ENTRYPOINT ["/app/.venv/bin/python", "-m", "i3wm_mcp"]
