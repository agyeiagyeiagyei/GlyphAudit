"""Prompt loading and rendering.

The prompt is a markdown template with `{placeholder}` markers. We
collapse the comparison results into a compact text block and inject it
in place of `{report_data}`.
"""

from __future__ import annotations

import os
from typing import Iterable, Optional

from ..comparator import ComparisonResult


# Default prompt ships in the package at prompts/health_check.md
DEFAULT_PROMPT_FILENAME = "health_check.md"

# How many top-delta mismatches to surface per tier per pair.
MAX_TIER1_MISMATCHES = 30
MAX_TIER2_MISMATCHES = 30


def load_prompt(prompt_path: Optional[str] = None) -> str:
    """Load the prompt template text. If no path given, load the bundled default."""
    if prompt_path is None:
        prompt_path = _default_prompt_path()
    if not os.path.isfile(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    with open(prompt_path, encoding="utf-8") as f:
        return f.read()


def render(prompt_text: str, results: Iterable[ComparisonResult]) -> str:
    """Substitute {report_data} (and a few simple metadata fields)
    into the prompt text. Unknown placeholders are left intact so that
    user-supplied prompts can include their own free-form content."""
    results_list = list(results)
    context = {
        "report_data": _format_results(results_list),
        "pair_count": str(len(results_list)),
        "filter_label": results_list[0].filter_label if results_list and results_list[0].filter_label else "(none — full font)",
        "tolerance":   str(results_list[0].tolerance_units) if results_list else "1.0",
    }
    return _safe_format(prompt_text, context)


# ---------------------------------------------------------------------------

def _format_results(results: list[ComparisonResult]) -> str:
    """Compact text rendering of the mismatch picture across all pairs."""
    blocks: list[str] = []
    for r in results:
        c = r.counts()
        t1, t2 = c["tier1"], c["tier2"]
        blocks.append(f"## {r.target_label} → {r.reference_label}")
        if r.filter_label:
            blocks.append(f"Filter: {r.filter_label}")
        blocks.append(
            f"Tier 1 (codepoint): {t1['match']} match, {t1['mismatch']} mismatch, "
            f"{t1['missing-in-reference']} missing-in-reference, {t1['no-advance']} no-advance"
        )
        blocks.append(
            f"Tier 2 (variant): {t2['match']} match, {t2['mismatch']} mismatch, "
            f"{t2['missing-in-reference']} missing-in-reference, {t2['no-advance']} no-advance"
        )
        blocks.append(f"Tier 3 (internal-only): {c['tier3']['internal']} glyph(s)")

        # Top tier-1 mismatches
        t1_mm = sorted(
            (row for row in r.codepoint_rows if row.status == "mismatch"),
            key=lambda row: -abs(row.delta or 0),
        )[:MAX_TIER1_MISMATCHES]
        if t1_mm:
            blocks.append("\nTier 1 mismatches (top by |Δ|):")
            blocks.append("U+      char  target_name                    w_adv   r_adv   delta")
            for row in t1_mm:
                blocks.append(
                    f"U+{row.codepoint:04X}  {row.char:<3}  {row.target_name:<32} "
                    f"{_fmt(row.target_advance)}  {_fmt(row.reference_advance)}  "
                    f"{_fmt_delta(row.delta)}"
                )

        # Tier-1 missing-in-reference (just count + a sample)
        t1_missing = [row for row in r.codepoint_rows if row.status == "missing-in-reference"]
        if t1_missing:
            sample = ", ".join(
                f"U+{row.codepoint:04X} {row.target_name}"
                for row in t1_missing[:15]
            )
            extra = "" if len(t1_missing) <= 15 else f" (and {len(t1_missing) - 15} more)"
            blocks.append(f"\nTier 1 missing-in-reference: {len(t1_missing)} total. Sample: {sample}{extra}")

        # Top tier-2 mismatches
        t2_mm = sorted(
            (row for row in r.variant_rows if row.status == "mismatch"),
            key=lambda row: -abs(row.delta or 0),
        )[:MAX_TIER2_MISMATCHES]
        if t2_mm:
            blocks.append("\nTier 2 mismatches (top by |Δ|):")
            blocks.append("feature  base_U+  char  target_name                    w_adv   r_adv   delta")
            for row in t2_mm:
                blocks.append(
                    f"{row.feature:<7}  U+{row.base_codepoint:04X}   {row.base_char:<3}  "
                    f"{row.target_name:<32} {_fmt(row.target_advance)}  "
                    f"{_fmt(row.reference_advance)}  {_fmt_delta(row.delta)}"
                )

        # Tier-3 high-signal: variants of unencoded bases (those are real bugs)
        orphan_variants = [
            row for row in r.internal_rows
            if row.note.startswith("variant of unencoded base")
        ]
        if orphan_variants:
            blocks.append(f"\nTier 3 — variants of unencoded bases ({len(orphan_variants)}):")
            for row in orphan_variants[:30]:
                blocks.append(f"  {row.glyph_name}  ({row.note})")

        blocks.append("")
    return "\n".join(blocks)


def _fmt(value) -> str:
    return f"{value:>6}" if value is not None else "    —"


def _fmt_delta(value) -> str:
    if value is None:
        return "     —"
    return f"{value:+7g}"


def _default_prompt_path() -> str:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, "prompts", DEFAULT_PROMPT_FILENAME)


def _safe_format(template: str, mapping: dict[str, str]) -> str:
    """Substitute {key} with mapping[key] for known keys; leave unknown
    `{...}` markers untouched so a user prompt can use literal braces or
    other markers we don't recognise."""
    out = template
    for k, v in mapping.items():
        out = out.replace("{" + k + "}", v)
    return out
