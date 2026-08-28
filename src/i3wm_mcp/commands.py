"""Helpers for building i3 command strings shared by several tool modules.

Kept separate from the tools themselves so the "exactly one selector" rule and
the criteria-escaping rule have exactly one implementation each; a second copy
is how two tools start disagreeing about how a quote is escaped.
"""

from __future__ import annotations


def escape(value: str) -> str:
    """Escape a value for use inside an i3 criteria double-quoted string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_criteria(
    *,
    window_class: str | None = None,
    title: str | None = None,
    instance: str | None = None,
    mark: str | None = None,
    con_id: int | None = None,
) -> str:
    """Build an i3 ``[...]`` criteria selector, or '' when no field is given."""
    parts: list[str] = []
    if con_id is not None:
        parts.append(f"con_id={int(con_id)}")
    if mark is not None:
        parts.append(f'con_mark="{escape(mark)}"')
    if window_class is not None:
        parts.append(f'class="{escape(window_class)}"')
    if instance is not None:
        parts.append(f'instance="{escape(instance)}"')
    if title is not None:
        parts.append(f'title="{escape(title)}"')
    return f"[{' '.join(parts)}]" if parts else ""


def require_exactly_one(**named: bool) -> str:
    """Return the single truthy option name, or raise if not exactly one is set."""
    chosen = [name for name, present in named.items() if present]
    if len(chosen) != 1:
        options = ", ".join(named)
        raise ValueError(f"Provide exactly one of: {options} (got {len(chosen)}).")
    return chosen[0]
