# Attribution

This project is **derived from
[`caninja/i3wm-mcp`](https://github.com/caninja/i3wm-mcp)** by Fredrik Nilsen
Edler, used under the MIT License.

## What was carried over (in spirit)

- The idea of an MCP server exposing i3wm control to LLM clients.
- The convention of per-tool `annotations` (`readOnlyHint`, `destructiveHint`,
  `idempotentHint`, `openWorldHint`, `title`) and Pydantic-validated inputs with
  range/length constraints.

## What this rewrite changes

- **Transport:** migrated from shelling out to the `i3-msg` CLI to the async
  [`i3ipc`](https://github.com/altdesktop/i3ipc-python) library (genuine
  non-blocking I/O, Sway/Wayland compatibility, `app_id` surfaced).
- **Tool surface:** consolidated the upstream's 43 tools into 13 distinct,
  non-overlapping tools, with rarely-used verbs routed through a guarded
  `run_command` escape hatch.
- **Inputs:** flat, individually-described parameters instead of a single nested
  wrapper model, for full parameter-schema coverage.
- **Outputs:** typed Pydantic return models, so every tool advertises an
  `outputSchema`.
- **Quality scaffolding:** dependency manifest, `ruff`/`mypy`, a test suite with
  100% coverage, CI, and a local tool-definition-quality proxy check.

The upstream MIT copyright is retained in [LICENSE](LICENSE).
