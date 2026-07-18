#!/usr/bin/env python3
"""Local, deterministic proxy for Glama's Tool Definition Quality Score (TDQS).

Glama's real scorer runs an LLM over each tool for the subjective dimensions
(purpose/guidelines/etc.). We cannot reproduce that offline, but we *can* enforce
the deterministic parts it checks — the hard gates and structural signals — so a
regression is caught before publishing. This script:

* fails (exit 1) on any hard-gate violation (missing/tautological description,
  annotation-contradiction, undescribed parameters, missing outputSchema);
* warns on soft signals (very short/long descriptions, no sibling reference,
  tool count outside 3-15, inconsistent naming);
* prints a per-tool table plus the coherence-relevant server checks.

It is intentionally strict: passing here is necessary, not sufficient, for a
Grade-A score. Run: ``python scripts/rubric_check.py``.
"""

from __future__ import annotations

import re
import sys

import anyio

from i3wm_mcp.server import mcp

# Verbs that imply mutation; a read-only tool whose description uses them would
# contradict its readOnlyHint (Glama's instant transparency=1 gate).
_MUTATION_VERBS = re.compile(
    r"\b(close|kill|launch|delete|remove|move|set|toggle|focus|rename|exec|run|create|switch)\b",
    re.IGNORECASE,
)
_SNAKE_VERB_NOUN = re.compile(r"^[a-z]+_[a-z_]+$")


async def _load() -> list:
    return await mcp.list_tools()


def _tool_names(tools: list) -> set[str]:
    return {t.name for t in tools}


def check() -> int:
    """Run all checks and return a process exit code (0 = pass)."""
    tools = anyio.run(_load)
    names = _tool_names(tools)
    errors: list[str] = []
    warnings: list[str] = []

    print(f"{'TOOL':22} {'DESC':>4} {'PARAMS':>6} {'COV%':>5} {'OUT':>3} {'RO':>5} {'DES':>4}")
    print("-" * 60)

    for t in sorted(tools, key=lambda x: x.name):
        desc = t.description or ""
        props = (t.inputSchema or {}).get("properties", {})
        described = [k for k, v in props.items() if v.get("description")]
        coverage = 100 if not props else round(100 * len(described) / len(props))
        ann = t.annotations
        read_only = getattr(ann, "readOnlyHint", None)
        destructive = getattr(ann, "destructiveHint", None)

        print(
            f"{t.name:22} {len(desc):>4} {len(props):>6} {coverage:>5} "
            f"{'Y' if t.outputSchema else 'N':>3} {str(read_only):>5} {str(destructive):>4}"
        )

        # --- Hard gates -------------------------------------------------
        if not desc:
            errors.append(f"{t.name}: missing description (TDQS hard gate).")
        if desc and desc.strip().lower() == t.name.replace("_", " ").lower():
            errors.append(f"{t.name}: tautological description (purpose capped at 2).")
        if coverage < 100:
            errors.append(f"{t.name}: parameter-schema coverage {coverage}% (<100%).")
        if t.outputSchema is None:
            errors.append(f"{t.name}: no outputSchema.")
        if ann is None or None in (
            read_only,
            destructive,
            getattr(ann, "idempotentHint", None),
            getattr(ann, "openWorldHint", None),
        ):
            errors.append(f"{t.name}: incomplete annotations (need all four hints).")
        if read_only and _MUTATION_VERBS.search(desc) and "read-only" not in desc.lower():
            # A read-only tool that describes its own mutation would contradict the
            # annotation (Glama's transparency=1 gate). We trust an explicit
            # "read-only" affirmation, since mutation-shaped words otherwise appear
            # legitimately as parameter names, nouns, or references to sibling tools.
            errors.append(f"{t.name}: readOnly tool lacks a 'read-only' affirmation.")

        # --- Soft signals ----------------------------------------------
        if len(desc) < 120:
            warnings.append(f"{t.name}: description short ({len(desc)}c); risk of under-spec.")
        if len(desc) > 700:
            warnings.append(f"{t.name}: description long ({len(desc)}c); risk of bloat.")
        siblings = [n for n in names if n != t.name and f"`{n}`" in desc]
        if not siblings and len(tools) > 1:
            warnings.append(f"{t.name}: names no sibling tool (weakens guidelines/disambiguation).")
        if not _SNAKE_VERB_NOUN.match(t.name):
            warnings.append(f"{t.name}: name is not verb_noun snake_case.")

    # --- Coherence-level checks -----------------------------------------
    print("\nServer-level (coherence):")
    count_ok = 3 <= len(tools) <= 15
    print(f"  tool count: {len(tools)} ({'in 3-15 ✓' if count_ok else 'OUT OF 3-15 ✗'})")
    if not count_ok:
        errors.append(f"tool count {len(tools)} outside the 3-15 coherence sweet spot.")
    has_reads = any(getattr(t.annotations, "readOnlyHint", False) for t in tools)
    has_mutations = any(not getattr(t.annotations, "readOnlyHint", True) for t in tools)
    print(f"  has read tools: {has_reads} · has mutation tools: {has_mutations}")
    if not (has_reads and has_mutations):
        warnings.append("server lacks both read and mutation tools (completeness).")

    # --- Report ----------------------------------------------------------
    print("\n" + "=" * 60)
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠ {w}")
    if errors:
        print(f"\nERRORS ({len(errors)}) — hard-gate failures:")
        for e in errors:
            print(f"  ✗ {e}")
        print("\nRESULT: FAIL")
        return 1
    print("\nRESULT: PASS — all deterministic TDQS gates satisfied.")
    print("(Subjective dimensions are still LLM-graded by Glama; this is a floor, not the score.)")
    return 0


if __name__ == "__main__":
    sys.exit(check())
