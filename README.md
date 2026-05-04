# GlyphAudit

A small CLI tool for comparing a target font against one or more reference fonts.

Designed to answer: **"how does my font compare to a known reference, glyph-by-glyph and variant-by-variant?"**

The comparison is tiered so that every glyph in the target font is accounted for, even unencoded ones (small caps, stylistic alternates, oldstyle figures, etc.).

## Install

```bash
pip install -e .                         # core only — works for TTF/OTF references
pip install -e ".[glyphs]"               # add glyphsLib for .glyphspackage / .glyphs sources
pip install -e ".[ai]"                   # add anthropic / openai / google-generativeai for --ai
pip install -e ".[all]"                  # everything
```

Once installed, the `glyph-audit` console command is available, equivalent to `python -m GlyphAudit`.

## What it does

For each target master and its paired reference, the tool produces three sections in the report:

| Tier | What it covers | How it pairs |
|---|---|---|
| **1 — Codepoint** | Every encoded glyph in the target font | By Unicode codepoint |
| **2 — Variant** | Working glyphs whose name ends in a recognised feature suffix (`.smcp`, `.ss01`, `.onum`, …) | By `(source codepoint, feature tag)`. Reference's variant is found via its compiled GSUB table (TTF/system) or its own naming convention (Glyphs source). |
| **3 — Internal-only** | Working glyphs that have no codepoint and no recognised feature suffix (components, locl variants, ligature parts) | Listed for completeness — no attempt to match. |

Within tier 1 and tier 2, every row is tagged `match` / `mismatch` / `missing-in-reference` / `no-advance` so a quick scan of the report surfaces real anomalies instead of expected differences.

## Reference sources

The tool accepts three kinds of reference, distinguished by the value passed to `--pair`:

| Value form | Loader |
|---|---|
| `path/to/Helvetica.ttf` or `.otf` | TTF/OTF — reads cmap, hmtx, and GSUB |
| `path/to/MyTypeface.glyphspackage` or `.glyphs` | Glyphs source — uses glyphsLib, derives variants from name suffixes |
| `Family-system` *(suffix `-system`)* | Installed system font. Family and style accept either a space (`Helvetica Bold-system`) or a hyphen (`Helvetica-Bold-system`). |

Target font accepts the same forms.

### Variable font axis pinning

Append `@axis=value[,axis=value]` to any spec (file path or system) to pin a variable font at a design-space location. The reference is instantiated at that point before reading widths and GSUB:

```bash
--pair Regular="Inter[wght].ttf@wght=400"
--pair Bold="Inter-system@wght=700"
--pair Display="VarFont.ttf@wght=900,wdth=125"
```

Pinning fails with a clear error if the file isn't a variable font, or if a requested axis tag isn't in the file's `fvar`. Glyphs sources don't accept the `@axis=...` form — use `--pair MASTER_NAME=...` to select a master instead.

### Reusable instance map (config)

For projects with several weights, define each as `[instances.NAME]` in `~/.glyph-audit/config.toml` and pass `--from-config` instead of typing `--pair` every time:

```toml
[instances.Regular]
ref = "Reference-Regular.ttf"

[instances.Bold]
ref = "Inter[wght].ttf"
axis = { wght = 700 }

[instances.Light]
ref = "Inter-Light-system"
```

```bash
python -m GlyphAudit \
    --target sources/MyTypeface.glyphspackage \
    --from-config
```

`--from-config` adds to any explicit `--pair` flags, so you can mix CLI and config entries. See `examples/config.toml.example` for the full schema.

## Default CLI flags via config

Frequently-used flags (`--output`, `--filter`, `--tolerance`, `--title`, `--ai`, `--prompt`, `--no-normalize-upm`, `--from-config`) can live in a `[defaults]` section so you don't retype them:

```toml
[defaults]
filter      = "ready"
tolerance   = 1.0
title       = "MyTypeface Coverage"
ai          = "claude"
from_config = true
```

Precedence (highest first): explicit CLI flag → `[defaults]` in config → built-in fallback. With the table above you can run:

```bash
python -m GlyphAudit --target sources/MyTypeface.glyphspackage
```

…and get a `ready`-filtered, AI-summarised report against whichever pairs `[instances.*]` defines. Pass `--filter all` on the CLI to override the config and get an unfiltered run.

### Output filename

If you don't pass `--output` (and the config doesn't set one), the report path defaults to:

- `glyph-audit-report.md` — no filter
- `glyph-audit-filtered.md` — when `--filter` is anything other than `all`

The actual filter (`yellow`, `ready`, etc.) is recorded in the report header, so the filename stays stable across filter changes.

## Install

Requires Python 3.9+, plus:

```
fontTools
glyphsLib   # only if you load Glyphs sources
```

## Usage

```bash
python -m GlyphAudit \
    --target sources/MyTypeface.glyphspackage \
    --pair Regular=sources/reference/Reference-Regular.ttf \
    --pair Bold=sources/reference/Reference-Bold.ttf \
    --output coverage-report.md
```

A `--pair` is `MASTER_NAME=REFERENCE`. The master name selects which target master to compare; the reference is loaded once and compared against just that master. Repeat `--pair` for additional weights.

### System-font reference

```bash
python -m GlyphAudit \
    --target MyFont.ttf \
    --pair Default="Helvetica-system" \
    --output report.md
```

### Cross-format

```bash
python -m GlyphAudit \
    --target sources/MyTypeface.glyphspackage \
    --pair Bold=sources/reference/Reference-Bold.ttf \
    --pair Bold-vs-system="Helvetica Bold-system" \
    --output report.md
```

(Run the same master twice against different references in one report.)

### Options

| Flag | Default | Notes |
|---|---|---|
| `--target PATH` | required | Target font (TTF / OTF / .glyphspackage / .glyphs / system) |
| `--pair NAME=REF` | repeatable | One per master to compare. Required unless `--from-config` is given. REF accepts `@axis=value` suffix for VF pinning. |
| `--from-config` | off | Build pairs from `[instances.NAME]` entries in the config file. Adds to any explicit `--pair` flags. |
| `--output PATH` | `glyph-audit-report.md` (or `glyph-audit-filtered.md` when `--filter` is active) | Markdown output path |
| `--tolerance N` | `1.0` | Max acceptable advance-width delta in font units (or per-1000-UPM if normalising) |
| `--no-normalize-upm` | off | Compare raw advances instead of per-1000-UPM-normalized values |
| `--title TEXT` | "Glyph Audit Report" | Top-level report heading |
| `--filter NAME` | `all` | Restrict target font to glyphs marked with a Glyphs colour (`yellow`, `light-green`, `green`, `ready`). Only effective for `.glyphs` / `.glyphspackage` target sources; ignored for TTFs. |
| `--ai PROVIDER` | off | Add an AI-written health-check summary at the top of the report. Provider is one of `claude`, `openai`, `gemini`. Requires the provider's SDK and an API key (see "AI summary" below). |
| `--prompt PATH` | bundled default | Custom prompt template for the AI summary. Defaults to `prompts/health_check.md` inside the package. |
| `--config PATH` | `~/.glyph-audit/config.toml` | Override AI config file location. |

### Filter values (Glyphs colour palette)

| `--filter` | Glyphs colour index | Conventional meaning |
|---|---|---|
| `yellow` | 3 | Ready for testing |
| `light-green` | 4 | Passed inspection |
| `green` | 5 | Production-ready |
| `ready` | 3 OR 4 | Either of the above |
| `all` *(default)* | — | No filtering |

### Exit codes

- `0` — all matched within tolerance
- `1` — at least one mismatch
- `2` — load error

## AI summary

When `--ai PROVIDER` is set, the tool sends a compact text rendering of the comparison results (counts, top-delta mismatches, Tier 3 orphan variants) to the chosen LLM and prepends its response as an `## AI Health Check` section at the top of the report. The default prompt at `prompts/health_check.md` instructs the model to surface anomalies (duplicate-unicode glyphs, missing base glyphs, systematic spacing drift) in plain English.

### First-time setup

```bash
mkdir -p ~/.glyph-audit
cp scripts/GlyphAudit/examples/config.toml.example ~/.glyph-audit/config.toml
$EDITOR ~/.glyph-audit/config.toml      # paste your key(s)
```

Only the providers you use need a section filled in. Missing provider sections fall back to environment variables: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`.

### Required SDKs

Install only the SDK for the provider you actually use:

```bash
pip install anthropic              # for --ai claude
pip install openai                 # for --ai openai
pip install google-generativeai    # for --ai gemini
```

If the SDK isn't installed, the tool prints the matching `pip install` command and writes a fallback "_AI summary unavailable: …_" section so the rest of the report still reaches you.

### Project-local config

If you'd rather keep keys per-project (e.g. different teams), pass `--config PATH`:

```bash
python -m GlyphAudit ... --config .glyph-audit.toml
```

**Add the local config to `.gitignore`** — the file holds plaintext API keys. The user-level default (`~/.glyph-audit/config.toml`) sits outside any repo, so it can't be accidentally committed.

### Custom prompt

```bash
python -m GlyphAudit ... --ai claude --prompt my_prompt.md
```

Recognised placeholders the tool substitutes into the prompt: `{report_data}`, `{filter_label}`, `{tolerance}`, `{pair_count}`. Anything else is left untouched, so prompts can include their own free-form `{…}` markers.

## Reading the report

Each target/reference pairing gets one section. The section starts with counts, then lists mismatches (sorted by severity — largest delta first). Missing-in-reference lists are grouped by Unicode block to make scope obvious at a glance. Tier 3 (internal-only) glyphs are bucketed by note so component/ligature noise stays separated.

## Lifting this into a standalone repo

This package is self-contained — it imports only `fontTools` and (optionally) `glyphsLib`, with no host-project paths. To extract:

1. Move `GlyphAudit/` to its new repo root (or under `src/GlyphAudit/`).
2. Add a minimal `pyproject.toml` declaring the dependencies above.
3. Optionally expose a console script in `pyproject.toml` so `glyph-audit` works without `python -m`.

The CLI module accepts only paths and reference specs — there's no implicit "look in `sources/`" behaviour to unwind.

## Limitations

- Tier 2 currently walks `SingleSubst` GSUB lookups only. Variants implemented as `MultipleSubst`, `LigatureSubst`, or contextual lookups won't be matched on the reference side. (This is the right default for `smcp`/`ss0X`/`onum` and the like, which are almost always single substitutions.)
- The system-font loader matches by `name` table family + subfamily. Variable fonts and TTC/OTC collections are read by file path; named instances aren't unfolded.
- Sidebearings (LSB / RSB) aren't compared in this tool — only advance widths. Add a similar comparator if needed.
- `--ai` sends a summary of mismatch data to a third-party API. Don't enable it on fonts whose existence is confidential. The tool sends only glyph names, codepoints, and advance widths — no outline data — but the host you're querying may log and retain that text indefinitely.
