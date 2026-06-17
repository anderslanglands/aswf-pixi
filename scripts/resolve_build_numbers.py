#!/usr/bin/env python3
"""Resolve package build numbers before CI builds artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import ci_matrix


PACKAGE_FILES_URL = "https://api.anaconda.org/package/anderslanglands/{package}/files"

NAME_RE = re.compile(r"^name:\s*(.+?)\s*(?:#.*)?$")
QUOTE_RE = re.compile(r"^['\"](.*)['\"]$")

PackageFilesFetcher = Callable[[str], list[dict[str, Any]]]


def parse_name_value(line: str) -> str | None:
    match = NAME_RE.match(line)
    if not match:
        return None
    value = match.group(1).strip()
    quoted = QUOTE_RE.match(value)
    if quoted:
        return quoted.group(1)
    return value


def recipe_package_names(recipe: Path) -> list[str]:
    recipe_file = recipe / "recipe.yaml"
    lines = recipe_file.read_text(encoding="utf-8").splitlines()
    recipe_name: str | None = None
    package_names: list[str] = []
    in_recipe = False
    in_outputs = False
    current_output_kind: str | None = None

    for raw_line in lines:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0:
            key = line.split(":", 1)[0]
            in_recipe = key == "recipe"
            in_outputs = key == "outputs"
            current_output_kind = None
            continue

        if in_recipe and indent == 2:
            name = parse_name_value(line)
            if name:
                recipe_name = name
            continue

        if not in_outputs:
            continue

        output_match = re.match(r"^-\s+(package|staging):", line)
        if indent == 2 and output_match:
            current_output_kind = output_match.group(1)
            continue

        if current_output_kind == "package" and indent == 6:
            name = parse_name_value(line)
            if name:
                package_names.append(name)

    if package_names:
        return list(dict.fromkeys(package_names))
    if recipe_name:
        return [recipe_name]
    raise SystemExit(f"Could not find package name(s) in {recipe_file}.")


def package_files_url(package_name: str) -> str:
    return PACKAGE_FILES_URL.format(package=package_name)


def fetch_package_files(url: str) -> list[dict[str, Any]]:
    try:
        with urlopen(url, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            return []
        raise SystemExit(f"Failed to fetch {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise SystemExit(f"Failed to fetch {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse Anaconda package file listing from {url}: {exc}") from exc

    if isinstance(payload, list):
        return [record for record in payload if isinstance(record, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("files"), list):
        return [record for record in payload["files"] if isinstance(record, dict)]
    raise SystemExit(f"Unexpected Anaconda package file listing shape from {url}.")


def record_subdir(record: dict[str, Any]) -> str:
    attrs = record.get("attrs", {})
    if isinstance(attrs, dict) and attrs.get("subdir"):
        return str(attrs["subdir"])

    basename = str(record.get("basename", ""))
    if "/" in basename:
        return basename.split("/", 1)[0]
    return ""


def record_version(record: dict[str, Any]) -> str:
    if record.get("version"):
        return str(record["version"])

    attrs = record.get("attrs", {})
    if isinstance(attrs, dict) and attrs.get("version"):
        return str(attrs["version"])
    return ""


def record_build_number(record: dict[str, Any]) -> int | None:
    attrs = record.get("attrs", {})
    if isinstance(attrs, dict):
        record = {**record, **attrs}

    build_number = record.get("build_number")
    if isinstance(build_number, int):
        return build_number
    if isinstance(build_number, str) and ci_matrix.BUILD_NUMBER_RE.fullmatch(build_number):
        return int(build_number)

    build = str(record.get("build", ""))
    maybe_number = build.rsplit("_", 1)[-1]
    if ci_matrix.BUILD_NUMBER_RE.fullmatch(maybe_number):
        return int(maybe_number)
    return None


def next_build_number(
    recipe: Path,
    platforms: list[str],
    target: str,
    fetcher: PackageFilesFetcher = fetch_package_files,
) -> int:
    package_names = set(recipe_package_names(recipe))
    version = recipe.parts[-1]
    subdirs = set([*platforms, "noarch"])
    existing_build_numbers: list[int] = []

    # Anaconda rejects re-uploading the same basename even when the existing
    # file only has a different label, so inspect all files for each output
    # package instead of only the selected target label's repodata.
    for package_name in sorted(package_names):
        for record in fetcher(package_files_url(package_name)):
            if record_version(record) != version:
                continue
            if record_subdir(record) not in subdirs:
                continue
            build_number = record_build_number(record)
            if build_number is not None:
                existing_build_numbers.append(build_number)

    if not existing_build_numbers:
        return 0
    return max(existing_build_numbers) + 1


def resolve_build_numbers(
    recipes: list[Path],
    platforms: list[str],
    target: str,
    requested_build_number: str,
    fetcher: PackageFilesFetcher = fetch_package_files,
) -> dict[str, str]:
    ci_matrix.validate_build_number(requested_build_number)
    ci_matrix.validate_publish_target(target)

    if requested_build_number and requested_build_number != ci_matrix.AUTO_BUILD_NUMBER:
        return {recipe.as_posix(): requested_build_number for recipe in recipes}

    if target == "artifact-only":
        if requested_build_number == ci_matrix.AUTO_BUILD_NUMBER:
            raise SystemExit("Automatic build number resolution requires test-label or default-label.")
        return {recipe.as_posix(): "" for recipe in recipes}

    return {
        recipe.as_posix(): str(next_build_number(recipe, platforms, target, fetcher))
        for recipe in recipes
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipes", required=True)
    parser.add_argument("--platforms", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--build-number", default="")
    args = parser.parse_args()

    recipes = ci_matrix.parse_recipes(args.recipes)
    platforms = ci_matrix.parse_platforms(args.platforms)
    build_numbers = resolve_build_numbers(recipes, platforms, args.target, args.build_number)
    print(json.dumps(build_numbers, sort_keys=True))


if __name__ == "__main__":
    main()
