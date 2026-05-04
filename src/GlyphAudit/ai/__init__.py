"""AI summary subpackage.

Public surface is `summarize(results, provider, ...) -> str`. Everything
else (config loading, prompt rendering, provider SDK shims) is internal.
"""

from .summary import summarize, AIError

__all__ = ["summarize", "AIError"]
