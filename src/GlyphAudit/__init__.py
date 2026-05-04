"""Font coverage and width comparison tool.

Compares a working font against one or more reference fonts using a
three-tier match: codepoint, feature variant, and internal-only.

Designed to be lifted out of this repo as a standalone package — keep
imports inside this package and avoid leaking host-project assumptions.
"""

__version__ = "0.1.0"

from .model import FontView, FEATURE_SUFFIXES
from .loaders import load_font
from .comparator import TieredComparator, ComparisonResult
from .report import write_markdown

__all__ = [
    "FontView",
    "FEATURE_SUFFIXES",
    "load_font",
    "TieredComparator",
    "ComparisonResult",
    "write_markdown",
    "__version__",
]
