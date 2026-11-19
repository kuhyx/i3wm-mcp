#!/bin/bash

# ============================================================================
# Deploy i3wm-mcp to this machine.
#
# The one place it runs is kuhy's checkout ~/src/i3wm-mcp: its .venv holds an
# editable install that the Claude MCP config (`i3wm` server) spawns, and
# ~/.local/bin/i3wm-mcp is the `run:` launcher. This script fast-forwards the
# checkout to origin/main, re-syncs the venv to the pinned deps, points the
# launcher at the venv, then fails unless an MCP handshake lists the tools.
# Idempotent; never uninstalls anything. Refuses a dirty or diverged checkout
# instead of touching kuhy's work.
# ============================================================================

set -euo pipefail

readonly REPO="${I3WM_MCP_REPO:-$HOME/src/i3wm-mcp}"
readonly VENV="$REPO/.venv"
readonly LAUNCHER="${I3WM_MCP_LAUNCHER:-$HOME/.local/bin/i3wm-mcp}"
readonly MIN_TOOLS="${I3WM_MCP_MIN_TOOLS:-10}"

die() { echo "deploy: $*" >&2; exit 1; }

update_checkout() {
    [[ -d "$REPO/.git" || -f "$REPO/.git" ]] || die "no git checkout at $REPO"
    [[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] \
        || die "$REPO has uncommitted changes; not touching it"
    git -C "$REPO" fetch -q origin main
    git -C "$REPO" merge -q --ff-only origin/main \
        || die "$REPO diverged from origin/main; fast-forward refused"
}

sync_venv() {
    [[ -x "$VENV/bin/python" ]] || uv venv -q --python 3.14 "$VENV"
    uv pip install -q --python "$VENV/bin/python" -e "${REPO}[dev]"
}

link_launcher() {
    mkdir -p "$(dirname "$LAUNCHER")"
    ln -sfn "$VENV/bin/i3wm-mcp" "$LAUNCHER"
    [[ "$(readlink -f "$LAUNCHER")" == "$(readlink -f "$VENV/bin/i3wm-mcp")" ]] \
        || die "launcher $LAUNCHER does not resolve to $VENV/bin/i3wm-mcp"
}

main() {
    update_checkout
    sync_venv
    link_launcher
    "$VENV/bin/python" "$REPO/scripts/deploy_health.py" --min-tools "$MIN_TOOLS" "$LAUNCHER"
    echo "deploy: $(git -C "$REPO" rev-parse --short HEAD) live at $LAUNCHER"
}

main "$@"
