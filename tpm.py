from __future__ import annotations

import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

for local_site in [ROOT / ".pydeps", *ROOT.glob(".venv/lib/python*/site-packages")]:
    if local_site.exists():
        site.addsitedir(str(local_site))

from tennis_pro_manager.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
