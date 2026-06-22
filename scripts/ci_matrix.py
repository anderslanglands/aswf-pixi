#!/usr/bin/env python3
"""Prepare a GitHub Actions matrix for package builds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


RUNNERS = {
    "linux-64": "ubuntu-latest",
    "osx-64": "macos-15-intel",
    "osx-arm64": "macos-15",
    "win-64": "windows-latest",
}

DEFAULT_PLATFORMS = ["linux-64", "win-64", "osx-arm64"]

RECIPE_SUPPORTED_PLATFORMS = {
    "optix-dev": {"linux-64", "win-64"},
}


BUILD_NUMBER_RE = re.compile(r"[0-9]+")
AUTO_BUILD_NUMBER = "auto"


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_platforms(value: str) -> list[str]:
    platforms = split_csv(value)
    if not platforms:
        raise SystemExit("No platforms were requested.")
    if len(platforms) == 1 and platforms[0] == "all":
        return list(RUNNERS)
    if len(platforms) == 1 and platforms[0] == "default":
        return DEFAULT_PLATFORMS

    unknown = sorted(set(platforms) - set(RUNNERS))
    if unknown:
        known = ", ".join(sorted(RUNNERS))
        raise SystemExit(f"Unsupported platform(s): {', '.join(unknown)}. Supported: {known}, default, all.")
    return platforms


def validate_recipe_path(recipe: Path) -> None:
    recipe_file = recipe / "recipe.yaml"
    if recipe.is_absolute() or ".." in recipe.parts:
        raise SystemExit(f"Recipe directory {recipe} must be a relative package/version path.")
    if len(recipe.parts) != 2:
        raise SystemExit(f"Recipe directory {recipe} should look like package/version.")
    if not recipe_file.is_file():
        raise SystemExit(f"Recipe directory {recipe} does not contain recipe.yaml.")


def expand_recipe_selector(selector: str) -> list[Path]:
    recipe = Path(selector)
    if recipe.is_absolute() or ".." in recipe.parts:
        raise SystemExit(f"Recipe directory {recipe} must be a relative package/version path.")

    if "*" not in selector:
        if (recipe / "recipe.yaml").is_file():
            return [recipe]

        if len(recipe.parts) == 1 and recipe.is_dir():
            matches = [
                candidate
                for candidate in sorted(recipe.iterdir(), key=lambda path: path.name)
                if candidate.is_dir() and (candidate / "recipe.yaml").is_file()
            ]
            if matches:
                return matches

        return [recipe]

    if len(recipe.parts) != 2 or recipe.parts[-1] != "*" or any("*" in part for part in recipe.parts[:-1]):
        raise SystemExit(f"Recipe wildcard selector {recipe} must look like package/*.")

    package_dir = recipe.parent
    if not package_dir.is_dir():
        raise SystemExit(f"Recipe wildcard selector {recipe} did not match a package directory.")

    matches = [
        candidate
        for candidate in sorted(package_dir.iterdir(), key=lambda path: path.name)
        if candidate.is_dir() and (candidate / "recipe.yaml").is_file()
    ]
    if not matches:
        raise SystemExit(f"Recipe wildcard selector {recipe} did not match any version recipes.")
    return matches


def parse_recipes(value: str) -> list[Path]:
    recipes: list[Path] = []
    seen: set[str] = set()
    selectors = split_csv(value)
    if not selectors:
        raise SystemExit("No recipes were requested.")

    for selector in selectors:
        for recipe in expand_recipe_selector(selector):
            validate_recipe_path(recipe)
            key = recipe.as_posix()
            if key not in seen:
                recipes.append(recipe)
                seen.add(key)
    return recipes


def validate_build_number(value: str) -> None:
    if value in {"", AUTO_BUILD_NUMBER}:
        return
    if not BUILD_NUMBER_RE.fullmatch(value):
        raise SystemExit("Build number must be empty, auto, or a non-negative integer.")


def validate_publish_target(value: str) -> None:
    if value not in {"artifact-only", "test-label", "default-label"}:
        raise SystemExit(
            "Publish target must be one of artifact-only, test-label, or default-label."
        )


def parse_resolved_build_numbers(
    value: str,
    recipes: list[Path],
    requested_build_number: str,
) -> dict[str, str]:
    validate_build_number(requested_build_number)
    recipe_keys = {recipe.as_posix() for recipe in recipes}
    if not value:
        if requested_build_number == AUTO_BUILD_NUMBER:
            raise SystemExit("Auto build numbers must be resolved before preparing the matrix.")
        return {recipe_key: requested_build_number for recipe_key in recipe_keys}

    try:
        raw_build_numbers: Any = json.loads(value)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Resolved build numbers must be a JSON object: {exc}") from exc

    if not isinstance(raw_build_numbers, dict):
        raise SystemExit("Resolved build numbers must be a JSON object.")

    raw_keys = {str(key) for key in raw_build_numbers}
    missing = sorted(recipe_keys - raw_keys)
    unknown = sorted(raw_keys - recipe_keys)
    if missing:
        raise SystemExit(f"Missing resolved build number(s) for: {', '.join(missing)}")
    if unknown:
        raise SystemExit(f"Resolved build number(s) provided for unknown recipe(s): {', '.join(unknown)}")

    build_numbers: dict[str, str] = {}
    for recipe_key in sorted(recipe_keys):
        build_number = str(raw_build_numbers[recipe_key])
        if build_number and not BUILD_NUMBER_RE.fullmatch(build_number):
            raise SystemExit(f"Resolved build number for {recipe_key} must be empty or a non-negative integer.")
        build_numbers[recipe_key] = build_number
    return build_numbers


def matrix(
    recipes: list[Path],
    platforms: list[str],
    build_numbers: dict[str, str],
) -> dict[str, list[dict[str, str]]]:
    include: list[dict[str, str]] = []
    for recipe in recipes:
        recipe_key = recipe.as_posix()
        package = recipe.parts[-2]
        version = recipe.parts[-1]
        supported_platforms = RECIPE_SUPPORTED_PLATFORMS.get(package)
        recipe_platforms = [
            platform
            for platform in platforms
            if supported_platforms is None or platform in supported_platforms
        ]
        if not recipe_platforms:
            supported = ", ".join(sorted(supported_platforms or RUNNERS))
            requested = ", ".join(platforms)
            raise SystemExit(
                f"Recipe {recipe_key} does not support any requested platforms "
                f"({requested}). Supported: {supported}."
            )

        for platform in recipe_platforms:
            include.append(
                {
                    "recipe": recipe_key,
                    "package": package,
                    "version": version,
                    "platform": platform,
                    "runner": RUNNERS[platform],
                    "artifact": f"{package}-{version}-{platform}",
                    "build_number": build_numbers[recipe_key],
                }
            )
    return {"include": include}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipes", required=True)
    parser.add_argument("--platforms", required=True)
    parser.add_argument("--build-number", default="")
    parser.add_argument("--publish-target", required=True)
    parser.add_argument("--resolved-build-numbers", default="")
    args = parser.parse_args()

    recipes = parse_recipes(args.recipes)
    platforms = parse_platforms(args.platforms)
    validate_publish_target(args.publish_target)
    build_numbers = parse_resolved_build_numbers(
        args.resolved_build_numbers,
        recipes,
        args.build_number,
    )
    print(json.dumps(matrix(recipes, platforms, build_numbers), sort_keys=True))


if __name__ == "__main__":
    main()
