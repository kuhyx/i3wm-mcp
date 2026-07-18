# i3wm-mcp

A [Model Context Protocol](https://modelcontextprotocol.io) server for the
[i3](https://i3wm.org/) window manager (and, via the shared IPC, **Sway**).
It lets an MCP client — Claude Code, Claude Desktop, the MCP Inspector — query
and drive your i3/Sway session through a small set of well-described tools.

The tool definitions are deliberately tuned for a high
[Glama tool-definition-quality score](https://github.com/glama-ai/tool-definition-quality-score):
a consolidated, non-overlapping tool set, every parameter described, typed
output schemas, and honest `readOnlyHint`/`destructiveHint` annotations.

> Derived from [`caninja/i3wm-mcp`](https://github.com/caninja/i3wm-mcp)
> (MIT). See [ATTRIBUTION.md](ATTRIBUTION.md). This rewrite migrates the
> transport from the `i3-msg` CLI to the async `i3ipc` library, consolidates 43
> tools into 13, and adds tests, CI, and output schemas.

## Tools

| Tool | Kind | What it does |
|------|------|--------------|
| `get_tree` | read | List windows from the layout tree, with filters. |
| `get_focused` | read | Details of the currently focused window. |
| `list_workspaces` | read | All active workspaces. |
| `list_outputs` | read | All display outputs (monitors). |
| `get_config` | read | Version + config + binding modes snapshot. |
| `focus_window` | mutate | Focus by direction / criteria / layer / parent-child. |
| `move_window` | mutate | Move a container to a direction / workspace / output / scratchpad / center. |
| `manage_workspace` | mutate | Switch / move-to / rename / navigate workspaces. |
| `set_layout` | mutate | Container layout, split orientation, border style. |
| `toggle_window_state` | mutate | Toggle floating / fullscreen / sticky. |
| `exec_application` | **destructive** | Launch a program via `i3 exec` (arbitrary code). |
| `run_command` | **destructive** | Raw i3/Sway command escape hatch (marks, gaps, bar, reload/restart). |
| `kill_window` | **destructive** | Close the focused or a matched window. |

Rarely-used verbs (marks, i3-gaps, i3bar, scratchpad show/hide, `reload`,
`restart`, and deliberately `exit`) are reached through `run_command` rather
than dedicated tools, keeping the set small and distinct.

## Requirements

- A running **i3** (≥4.x) or **Sway** session.
- **Python ≥ 3.10**.

The server locates the i3/Sway IPC socket from the environment, so it must be
launched **from within your graphical session** (it needs `DISPLAY`, or
`SWAYSOCK`/`I3SOCK`, in its environment). Clients that spawn it from inside the
session — Claude Code, the MCP Inspector — inherit this automatically; a headless
or systemd launch would need those variables passed explicitly.

## Install

```bash
git clone https://github.com/kuhyx/i3wm-mcp
cd i3wm-mcp
python -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
```

## Run

```bash
./.venv/bin/python -m i3wm_mcp        # stdio transport
```

### Register with Claude Code

```bash
claude mcp add i3wm -- /absolute/path/to/i3wm-mcp/.venv/bin/python -m i3wm_mcp
```

### Inspect the tool definitions

```bash
npx @modelcontextprotocol/inspector ./.venv/bin/python -m i3wm_mcp
```

## Develop

```bash
./.venv/bin/python -m pytest        # tests + 100% coverage gate
./.venv/bin/ruff check . && ./.venv/bin/ruff format --check .
./.venv/bin/mypy src
./.venv/bin/python scripts/rubric_check.py   # local TDQS proxy check
```

## Safety

Read tools have no side effects. Mutation tools are reversible. The three
`destructive` tools (`exec_application`, `run_command`, `kill_window`) can run
arbitrary commands, close applications, or — via `run_command` — restart or exit
the session; treat them accordingly and never feed them untrusted input.

## License

MIT — see [LICENSE](LICENSE).
