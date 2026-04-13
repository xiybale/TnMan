from __future__ import annotations

import runpy
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def add_local_sites() -> None:
    preferred_paths = []

    local_dep_dir = ROOT / ".pydeps"
    if local_dep_dir.exists():
        preferred_paths.append(str(local_dep_dir))

    preferred_paths.extend(str(site_packages) for site_packages in ROOT.glob(".venv/lib/python*/site-packages"))

    for path in reversed(preferred_paths):
        if path not in sys.path:
            sys.path.insert(0, path)

    for path in preferred_paths:
        site.addsitedir(path)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2 or args[0] != "-m":
        print("usage: python_with_local_deps.py -m <module> [args...]", file=sys.stderr)
        return 2

    add_local_sites()
    module_name = args[1]
    sys.argv = [module_name, *args[2:]]
    runpy.run_module(module_name, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
