"""Top-level orchestrator for the AI summary feature."""

from __future__ import annotations

from typing import Iterable, Optional

from ..comparator import ComparisonResult
from .config import load_provider_config, ConfigError
from .prompts import load_prompt, render
from .providers import get_provider, ProviderError


class AIError(Exception):
    """Raised for any user-facing AI failure (config, SDK, or API)."""


def summarize(
    results: Iterable[ComparisonResult],
    provider: str,
    *,
    config_path: Optional[str] = None,
    prompt_path: Optional[str] = None,
) -> str:
    """Run the configured provider against the rendered prompt and
    return the model's response text. Raises AIError on any failure
    so the CLI can fall back gracefully."""
    try:
        provider_config = load_provider_config(provider, config_path=config_path)
    except (ConfigError, ValueError) as e:
        raise AIError(str(e)) from e

    try:
        prompt_template = load_prompt(prompt_path)
    except FileNotFoundError as e:
        raise AIError(str(e)) from e

    prompt = render(prompt_template, results)

    impl = get_provider(provider_config)
    try:
        return impl.summarize(prompt)
    except ProviderError as e:
        raise AIError(str(e)) from e
