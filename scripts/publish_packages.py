#!/usr/bin/env python3
"""Publish built conda packages to anaconda.org with rattler-build."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

import ci_matrix


CHANNELS = {
    "test-label": "test",
    "default-label": "main",
}


def package_paths(root: Path, target: str) -> list[Path]:
    paths: list[Path] = []
    seen: set[tuple[str, str]] = set()
    manifests = sorted(root.rglob("manifest.json"))
    if not manifests:
        raise SystemExit(f"No artifact manifests found under {root}.")

    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        recipe = Path(str(manifest.get("recipe", "")))
        if recipe.is_absolute() or ".." in recipe.parts or len(recipe.parts) != 2:
            raise SystemExit(f"Unsafe recipe path in {manifest_path}: {recipe}")
        ci_matrix.validate_recipe_publish_target(recipe, target)

        for package in manifest.get("packages", []):
            rel_path = Path(package["path"])
            if rel_path.is_absolute() or ".." in rel_path.parts:
                raise SystemExit(f"Unsafe package path in {manifest_path}: {rel_path}")

            package_path = manifest_path.parent / rel_path
            if not package_path.is_file():
                raise SystemExit(f"Manifest package is missing: {package_path}")
            if package_path.name != package["file_name"]:
                raise SystemExit(f"Manifest filename mismatch for {package_path}")
            if package_path.parent.name != package["subdir"]:
                raise SystemExit(f"Manifest subdir mismatch for {package_path}")

            key = (str(package["subdir"]), str(package["file_name"]))
            if key in seen:
                raise SystemExit(f"Duplicate package across artifact manifests: {package['file_name']}")
            seen.add(key)
            paths.append(package_path)

    if not paths:
        raise SystemExit(f"No publishable packages listed in manifests under {root}.")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=sorted(CHANNELS), required=True)
    parser.add_argument("--root", default="artifacts")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    packages = package_paths(Path(args.root), args.target)

    if not args.dry_run and not os.environ.get("ANACONDA_API_KEY"):
        raise SystemExit("ANACONDA_API_KEY is not set.")

    cmd = [
        "rattler-build",
        "upload",
        "anaconda",
        "--owner",
        "anderslanglands",
        "--channel",
        CHANNELS[args.target],
        *[str(package) for package in packages],
    ]
    if args.dry_run:
        print(" ".join(cmd))
        return

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
