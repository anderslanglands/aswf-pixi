#!/usr/bin/env python3
"""Prepare a GitHub Actions matrix for package builds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


RUNNERS = {
    "linux-64": "ubuntu-latest",
    "osx-64": "macos-15-intel",
    "osx-arm64": "macos-15",
    "win-64": "windows-latest",
}


BUILD_NUMBER_RE = re.compile(r"[0-9]+")


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_platforms(value: str) -> list[str]:
    platforms = split_csv(value)
    if not platforms:
        raise SystemExit("No platforms were requested.")
    if len(platforms) == 1 and platforms[0] == "all":
        return list(RUNNERS)

    unknown = sorted(set(platforms) - set(RUNNERS))
    if unknown:
        known = ", ".join(sorted(RUNNERS))
        raise SystemExit(f"Unsupported platform(s): {', '.join(unknown)}. Supported: {known}, all.")
    return platforms


def parse_recipes(value: str) -> list[Path]:
    recipes = [Path(item) for item in split_csv(value)]
    if not recipes:
        raise SystemExit("No recipes were requested.")

    for recipe in recipes:
        recipe_file = recipe / "recipe.yaml"
        if recipe.is_absolute() or ".." in recipe.parts:
            raise SystemExit(f"Recipe directory {recipe} must be a relative package/version path.")
        if not recipe_file.is_file():
            raise SystemExit(f"Recipe directory {recipe} does not contain recipe.yaml.")
        if len(recipe.parts) < 2:
            raise SystemExit(f"Recipe directory {recipe} should look like package/version.")
    return recipes


def validate_build_number(value: str) -> None:
    if value and not BUILD_NUMBER_RE.fullmatch(value):
        raise SystemExit("Build number must be empty or a non-negative integer.")


def validate_publish_target(value: str) -> None:
    if value not in {"artifact-only", "test-label", "default-label"}:
        raise SystemExit(
            "Publish target must be one of artifact-only, test-label, or default-label."
        )


def matrix(recipes: list[Path], platforms: list[str]) -> dict[str, list[dict[str, str]]]:
    include: list[dict[str, str]] = []
    for recipe in recipes:
        package = recipe.parts[-2]
        version = recipe.parts[-1]
        for platform in platforms:
            include.append(
                {
                    "recipe": recipe.as_posix(),
                    "package": package,
                    "version": version,
                    "platform": platform,
                    "runner": RUNNERS[platform],
                    "artifact": f"{package}-{version}-{platform}",
                }
            )
    return {"include": include}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipes", required=True)
    parser.add_argument("--platforms", required=True)
    parser.add_argument("--build-number", default="")
    parser.add_argument("--publish-target", required=True)
    args = parser.parse_args()

    recipes = parse_recipes(args.recipes)
    platforms = parse_platforms(args.platforms)
    validate_build_number(args.build_number)
    validate_publish_target(args.publish_target)
    print(json.dumps(matrix(recipes, platforms), sort_keys=True))


if __name__ == "__main__":
    main()
