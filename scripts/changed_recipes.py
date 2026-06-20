#!/usr/bin/env python3
"""Extract changed package/version recipe selectors from path lists."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def changed_recipe_selectors(paths: list[str], root: Path = Path(".")) -> list[str]:
    selectors: list[str] = []
    seen: set[str] = set()

    for raw_path in paths:
        path = Path(raw_path.strip())
        if len(path.parts) < 3:
            continue

        recipe = Path(path.parts[0]) / path.parts[1]
        if recipe.is_absolute() or ".." in recipe.parts:
            continue
        if not (root / recipe / "recipe.yaml").is_file():
            continue

        selector = recipe.as_posix()
        if selector not in seen:
            selectors.append(selector)
            seen.add(selector)

    return selectors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("paths", nargs="*", help="Changed file paths. Reads stdin when omitted.")
    args = parser.parse_args()

    paths = args.paths
    if not paths:
        paths = [line.rstrip("\n") for line in sys.stdin if line.strip()]

    print(",".join(changed_recipe_selectors(paths, args.root)))


if __name__ == "__main__":
    main()
