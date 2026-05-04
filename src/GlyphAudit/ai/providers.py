"""Provider shims for Claude / OpenAI / Gemini.

Each class wraps the relevant SDK lazily — the SDK is imported only when
the provider is actually used, so users only need to install the SDK
they care about.
"""

from __future__ import annotations

from .config import ProviderConfig


# Reasonable upper bound — health-check responses are short.
MAX_OUTPUT_TOKENS = 2000


class ProviderError(Exception):
    """Raised when a provider call fails (network, auth, SDK missing)."""


def get_provider(config: ProviderConfig):
    """Return a provider instance ready to call .summarize()."""
    if config.name == "claude":
        return _ClaudeProvider(config)
    if config.name == "openai":
        return _OpenAIProvider(config)
    if config.name == "gemini":
        return _GeminiProvider(config)
    raise ValueError(f"Unknown provider: {config.name!r}")


# ---------------------------------------------------------------------------

class _ClaudeProvider:
    install_hint = "pip install anthropic"

    def __init__(self, config: ProviderConfig):
        self.config = config

    def summarize(self, prompt: str) -> str:
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise ProviderError(
                f"`anthropic` SDK not installed. Run: {self.install_hint}"
            ) from e

        client = anthropic.Anthropic(api_key=self.config.api_key)
        try:
            message = client.messages.create(
                model=self.config.model,
                max_tokens=MAX_OUTPUT_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            raise ProviderError(f"Claude API call failed: {e}") from e

        # response.content is a list of content blocks; join text blocks
        parts = []
        for block in message.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts).strip()


class _OpenAIProvider:
    install_hint = "pip install openai"

    def __init__(self, config: ProviderConfig):
        self.config = config

    def summarize(self, prompt: str) -> str:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise ProviderError(
                f"`openai` SDK not installed. Run: {self.install_hint}"
            ) from e

        client = OpenAI(api_key=self.config.api_key)
        try:
            response = client.chat.completions.create(
                model=self.config.model,
                max_tokens=MAX_OUTPUT_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            raise ProviderError(f"OpenAI API call failed: {e}") from e

        return (response.choices[0].message.content or "").strip()


class _GeminiProvider:
    install_hint = "pip install google-generativeai"

    def __init__(self, config: ProviderConfig):
        self.config = config

    def summarize(self, prompt: str) -> str:
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as e:
            raise ProviderError(
                f"`google-generativeai` SDK not installed. Run: {self.install_hint}"
            ) from e

        try:
            genai.configure(api_key=self.config.api_key)
            model = genai.GenerativeModel(self.config.model)
            response = model.generate_content(
                prompt,
                generation_config={"max_output_tokens": MAX_OUTPUT_TOKENS},
            )
        except Exception as e:
            raise ProviderError(f"Gemini API call failed: {e}") from e

        return (response.text or "").strip()
