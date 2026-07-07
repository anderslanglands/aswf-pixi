#!/usr/bin/env python3
"""Collect and validate package artifacts produced by one build job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


BUILD_NUMBER_RE = re.compile(r"[0-9]+")


def parse_package_file(path: Path) -> dict[str, object]:
    if path.suffix != ".conda":
        raise ValueError(f"{path} is not a .conda package")

    try:
        name, version, build = path.stem.rsplit("-", 2)
    except ValueError as exc:
        raise ValueError(f"Cannot parse conda package filename: {path.name}") from exc

    build_parts = build.rsplit("_", 1)
    if len(build_parts) != 2 or not build_parts[1].isdigit():
        raise ValueError(f"Cannot parse build number from package filename: {path.name}")

    return {
        "name": name,
        "version": version,
        "build": build,
        "build_number": int(build_parts[1]),
        "subdir": path.parent.name,
        "file_name": path.name,
    }


def collect_packages(output_dir: Path, platform: str) -> list[tuple[Path, dict[str, object]]]:
    packages: list[tuple[Path, dict[str, object]]] = []
    for path in sorted(output_dir.rglob("*.conda")):
        metadata = parse_package_file(path)
        subdir = metadata["subdir"]
        if subdir not in {platform, "noarch"}:
            continue
        if str(metadata["name"]).endswith("-build"):
            continue
        packages.append((path, metadata))
    return packages


def validate_packages(
    packages: list[tuple[Path, dict[str, object]]],
    *,
    recipe: Path,
    platform: str,
    build_number: str,
) -> list[dict[str, object]]:
    if not packages:
        raise SystemExit(f"No publishable .conda packages found for {recipe} on {platform}.")

    expected_version = recipe.parts[-1]
    seen: set[tuple[object, object]] = set()
    records: list[dict[str, object]] = []
    for path, metadata in packages:
        if metadata["version"] != expected_version:
            raise SystemExit(
                f"{metadata['file_name']} has version {metadata['version']}, expected {expected_version}."
            )
        if build_number and str(metadata["build_number"]) != build_number:
            raise SystemExit(
                f"{metadata['file_name']} has build number {metadata['build_number']}, expected {build_number}."
            )

        key = (metadata["subdir"], metadata["file_name"])
        if key in seen:
            raise SystemExit(f"Duplicate package artifact in build output: {metadata['file_name']}")
        seen.add(key)

        records.append({**metadata, "path": path.relative_to(path.parents[1]).as_posix()})

    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--build-number", default="")
    parser.add_argument("--include-package", action="append", default=[])
    args = parser.parse_args()

    if args.build_number and not BUILD_NUMBER_RE.fullmatch(args.build_number):
        raise SystemExit("Build number must be empty or a non-negative integer.")

    recipe = Path(args.recipe)
    if recipe.is_absolute() or ".." in recipe.parts or len(recipe.parts) < 2:
        raise SystemExit(f"Recipe directory {recipe} must be a relative package/version path.")

    output_dir = Path(args.output_dir)
    packages = collect_packages(output_dir, args.platform)
    include_packages = set(args.include_package)
    if include_packages:
        package_names = {str(metadata["name"]) for _, metadata in packages}
        missing = sorted(include_packages - package_names)
        if missing:
            raise SystemExit(f"Requested package(s) were not found in build output: {', '.join(missing)}")
        packages = [
            (path, metadata)
            for path, metadata in packages
            if str(metadata["name"]) in include_packages
        ]
    records = validate_packages(
        packages,
        recipe=recipe,
        platform=args.platform,
        build_number=args.build_number,
    )

    manifest = {
        "recipe": recipe.as_posix(),
        "package": recipe.parts[-2],
        "version": recipe.parts[-1],
        "platform": args.platform,
        "packages": records,
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {manifest_path} with {len(records)} package artifact(s).")


if __name__ == "__main__":
    main()
