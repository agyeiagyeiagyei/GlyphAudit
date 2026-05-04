"""Tiered comparator for font coverage.

Each `compare` produces a `ComparisonResult` with:

  Tier 1 — codepoint matches  : every encoded working glyph
  Tier 2 — variant matches    : every working glyph whose name has a
                                recognised feature suffix (.smcp etc.)
  Tier 3 — internal-only      : working glyphs that have neither an
                                encoding nor a recognised suffix; these
                                cannot be matched against the reference.

Inside each tier, rows are tagged matched / mismatched / missing so the
report can highlight problems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .model import FontView, parse_variant_suffix


GlyphFilter = Callable[[str], bool]


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class CodepointRow:
    codepoint: int
    char: str
    working_name: str
    working_advance: Optional[int]
    reference_name: Optional[str]
    reference_advance: Optional[int]
    delta: Optional[float]
    status: str  # 'match' | 'mismatch' | 'missing-in-reference' | 'no-advance'


@dataclass
class VariantRow:
    base_codepoint: int
    base_char: str
    feature: str
    working_name: str
    working_advance: Optional[int]
    reference_name: Optional[str]
    reference_advance: Optional[int]
    delta: Optional[float]
    status: str  # 'match' | 'mismatch' | 'missing-in-reference' | 'no-advance'


@dataclass
class InternalRow:
    glyph_name: str
    note: str  # 'unencoded-no-suffix' | 'unknown-base' | 'orphan-suffix'


@dataclass
class ComparisonResult:
    working_label: str
    reference_label: str
    tolerance_units: float
    filter_label: Optional[str] = None
    """Description of the working-glyph filter applied, e.g. 'yellow' or
    'ready (yellow + light-green)'. None if no filter was applied."""

    codepoint_rows: list[CodepointRow] = field(default_factory=list)
    variant_rows:   list[VariantRow]   = field(default_factory=list)
    internal_rows:  list[InternalRow]  = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        def by_status(rows):
            return {
                "match":                sum(1 for r in rows if r.status == "match"),
                "mismatch":             sum(1 for r in rows if r.status == "mismatch"),
                "missing-in-reference": sum(1 for r in rows if r.status == "missing-in-reference"),
                "no-advance":           sum(1 for r in rows if r.status == "no-advance"),
            }
        return {
            "tier1": by_status(self.codepoint_rows),
            "tier2": by_status(self.variant_rows),
            "tier3": {"internal": len(self.internal_rows)},
        }


# ---------------------------------------------------------------------------
# The comparator itself
# ---------------------------------------------------------------------------

class TieredComparator:
    def __init__(self, tolerance_units: float = 1.0,
                 normalize_upm: bool = True):
        """tolerance_units is in *normalized* (per-1000-UPM) units when
        normalize_upm is True; otherwise it's raw font units."""
        self.tolerance = tolerance_units
        self.normalize = normalize_upm

    def compare(self, working: FontView, reference: FontView,
                pair_label: str = "",
                working_filter: Optional[GlyphFilter] = None,
                filter_label: Optional[str] = None) -> ComparisonResult:
        result = ComparisonResult(
            working_label=f"{working.label} ({pair_label})" if pair_label else working.label,
            reference_label=reference.label,
            tolerance_units=self.tolerance,
            filter_label=filter_label,
        )

        self._tier1_codepoints(working, reference, result, working_filter)
        self._tier2_variants(working, reference, result, working_filter)
        self._tier3_internal(working, result, working_filter)
        return result

    # ----- Tier 1 -----------------------------------------------------------

    def _tier1_codepoints(self, w: FontView, r: FontView, result: ComparisonResult,
                          working_filter: Optional[GlyphFilter]):
        for cp in sorted(w.cmap):
            w_name = w.cmap[cp]
            if working_filter and not working_filter(w_name):
                continue
            w_adv  = w.advances.get(w_name)
            r_name = r.cmap.get(cp)
            r_adv  = r.advances.get(r_name) if r_name else None

            char = chr(cp) if 0x20 <= cp <= 0x10FFFF and not 0xD800 <= cp <= 0xDFFF else "·"
            row = CodepointRow(
                codepoint=cp,
                char=char,
                working_name=w_name,
                working_advance=w_adv,
                reference_name=r_name,
                reference_advance=r_adv,
                delta=None,
                status="match",
            )
            row.delta, row.status = self._classify(w, r, w_adv, r_adv,
                                                   ref_present=r_name is not None)
            result.codepoint_rows.append(row)

    # ----- Tier 2 -----------------------------------------------------------

    def _tier2_variants(self, w: FontView, r: FontView, result: ComparisonResult,
                        working_filter: Optional[GlyphFilter]):
        # Iterate working glyphs whose names parse as a feature variant.
        for name in sorted(w.all_glyph_names):
            if working_filter and not working_filter(name):
                continue
            parsed = parse_variant_suffix(name)
            if not parsed:
                continue
            base_name, feature = parsed

            # Find the source codepoint of the base glyph in the working font.
            base_cp = None
            for cp, gname in w.cmap.items():
                if gname == base_name:
                    base_cp = cp
                    break
            if base_cp is None:
                # Variant of an unencoded base — can't pair to a reference codepoint.
                result.internal_rows.append(InternalRow(
                    glyph_name=name,
                    note=f"variant of unencoded base '{base_name}'",
                ))
                continue

            w_adv = w.advances.get(name)
            r_name = r.variant_name(base_cp, feature)
            r_adv  = r.advances.get(r_name) if r_name else None

            char = chr(base_cp) if 0x20 <= base_cp <= 0x10FFFF and not 0xD800 <= base_cp <= 0xDFFF else "·"
            row = VariantRow(
                base_codepoint=base_cp,
                base_char=char,
                feature=feature,
                working_name=name,
                working_advance=w_adv,
                reference_name=r_name,
                reference_advance=r_adv,
                delta=None,
                status="match",
            )
            row.delta, row.status = self._classify(w, r, w_adv, r_adv,
                                                   ref_present=r_name is not None)
            result.variant_rows.append(row)

    # ----- Tier 3 -----------------------------------------------------------

    def _tier3_internal(self, w: FontView, result: ComparisonResult,
                        working_filter: Optional[GlyphFilter]):
        # Glyphs that have no codepoint AND no recognised feature suffix.
        encoded_names = set(w.cmap.values())
        variant_names = set()
        for name in w.all_glyph_names:
            if parse_variant_suffix(name):
                variant_names.add(name)
        for name in sorted(w.all_glyph_names):
            if working_filter and not working_filter(name):
                continue
            if name in encoded_names or name in variant_names:
                continue
            result.internal_rows.append(InternalRow(
                glyph_name=name,
                note="unencoded, no feature suffix",
            ))

    # ----- Shared classification logic -------------------------------------

    def _classify(self, w: FontView, r: FontView,
                  w_adv: Optional[int], r_adv: Optional[int],
                  ref_present: bool) -> tuple[Optional[float], str]:
        if not ref_present:
            return None, "missing-in-reference"
        if w_adv is None or r_adv is None:
            return None, "no-advance"

        if self.normalize and w.upm != r.upm:
            wn = w_adv * 1000.0 / w.upm
            rn = r_adv * 1000.0 / r.upm
            delta = wn - rn
        else:
            delta = float(w_adv) - float(r_adv)

        return delta, ("match" if abs(delta) <= self.tolerance else "mismatch")
