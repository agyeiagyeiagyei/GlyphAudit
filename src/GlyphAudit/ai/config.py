"""Config loader for the AI feature.

Resolution order for a provider's settings:
    1. Explicit `--config PATH` if provided.
    2. `~/.glyph-audit/config.toml` (default user-level location).
    3. Environment variables (per-provider names).

The config file uses TOML with a `[providers.NAME]` section per provider.
Missing sections fall back to env vars; missing env vars raise.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Optional


DEFAULT_CONFIG_PATH = os.path.expanduser("~/.glyph-audit/config.toml")

# Per-provider env-var fallback for the API key.
PROVIDER_ENV_KEY: dict[str, str] = {
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

# Per-provider default model identifier (overridable via config).
PROVIDER_DEFAULT_MODEL: dict[str, str] = {
    "claude": "claude-sonnet-4-6",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
}


@dataclass
class ProviderConfig:
    name: str          # 'claude' / 'openai' / 'gemini'
    api_key: str
    model: str


def load_provider_config(
    provider: str,
    config_path: Optional[str] = None,
) -> ProviderConfig:
    """Load configuration for one provider, raising if no key is found."""
    if provider not in PROVIDER_ENV_KEY:
        raise ValueError(f"Unknown provider {provider!r}. "
                         f"Expected one of: {', '.join(sorted(PROVIDER_ENV_KEY))}")

    file_section = _load_provider_section(provider, config_path)

    api_key = file_section.get("api_key") if file_section else None
    if not api_key:
        api_key = os.environ.get(PROVIDER_ENV_KEY[provider])

    if not api_key:
        env_var = PROVIDER_ENV_KEY[provider]
        path = config_path or DEFAULT_CONFIG_PATH
        raise ConfigError(
            f"No API key for provider {provider!r}. "
            f"Either set {env_var} or add it under [providers.{provider}] "
            f"in {path}. See examples/config.toml.example for the layout."
        )

    model = (file_section or {}).get("model") or PROVIDER_DEFAULT_MODEL[provider]

    return ProviderConfig(name=provider, api_key=api_key, model=model)


def _load_provider_section(provider: str, config_path: Optional[str]) -> Optional[dict]:
    """Return the [providers.NAME] sub-table from the config file, or None
    if the file (or section) doesn't exist.

    Silently ignores a missing default config file. Raises if an explicit
    `--config` path was passed but isn't readable, since that's clearly
    user intent."""
    explicit = config_path is not None
    path = config_path or DEFAULT_CONFIG_PATH

    if not os.path.isfile(path):
        if explicit:
            raise ConfigError(f"Config file not found: {path}")
        return None

    try:
        if sys.version_info >= (3, 11):
            import tomllib
            with open(path, "rb") as f:
                data = tomllib.load(f)
        else:
            import tomli  # type: ignore
            with open(path, "rb") as f:
                data = tomli.load(f)
    except Exception as e:
        raise ConfigError(f"Failed to parse {path}: {e}") from e

    return (data.get("providers") or {}).get(provider)


class ConfigError(Exception):
    """Raised when configuration cannot be resolved."""
