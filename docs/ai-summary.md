# AI summary

Pass `--ai PROVIDER` (`claude` / `openai` / `gemini`) to prepend an AI-written health-check summary to the report. The model gets a compact text rendering of the comparison results — counts, top-delta mismatches, Tier 3 orphan variants — and is instructed to surface anomalies (duplicate-unicode glyphs, missing base glyphs, systematic spacing drift) in plain English.

## Setup

### 1. API key

Add a `[providers.NAME]` block to `~/.glyph-audit/config.toml`:

```toml
[providers.claude]
api_key = "sk-ant-..."
```

…or set `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` in the environment.

### 2. Provider SDK

Install only the SDK for the provider you use:

```bash
pip install ".[claude]"     # for --ai claude
pip install ".[openai]"     # for --ai openai
pip install ".[gemini]"     # for --ai gemini
pip install ".[ai]"         # all three
```

If the SDK isn't installed when `--ai` is used, the tool prints the matching `pip install` command and writes a fallback `_AI summary unavailable: …_` block at the top of the report so the rest of the audit still reaches you.

### 3. Run

```bash
glyph-audit --target sources/MyTypeface.glyphspackage --ai claude --from-config
```

Or set it as a default so every run gets one:

```toml
[defaults]
ai = "claude"
```

## Custom prompt

The default prompt at `prompts/health_check.md` instructs the model with a structured brief for font-engineering review. To override:

```bash
glyph-audit --target ... --ai claude --prompt /path/to/my-prompt.md
```

Recognised placeholders the tool substitutes into the prompt:

| Placeholder | Substituted with |
|---|---|
| `{report_data}` | Compact rendering of all mismatches and orphan variants |
| `{filter_label}` | The active filter (`yellow`, `ready`, `(none — full font)`) |
| `{tolerance}` | Numeric tolerance the comparator used |
| `{pair_count}` | How many target/reference pairings are in the report |

Anything else (other `{…}` markers, plain prose) is left untouched, so user prompts can include their own free-form content.

## Privacy

`--ai` sends the comparison summary to the chosen LLM provider. The data sent contains:

- Glyph names, codepoints, and advance widths
- Master labels (Regular / Bold / etc.)
- The active filter and tolerance

The data sent does **not** contain:

- Glyph outlines
- Anchor positions or kerning
- Any source code or file paths beyond the labels you set

Don't enable `--ai` on confidential work — the provider you query may log and retain the prompt indefinitely.
