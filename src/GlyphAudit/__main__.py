"""Entry point: `python -m GlyphAudit ...`  (or use the `glyph-audit` console script)."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
