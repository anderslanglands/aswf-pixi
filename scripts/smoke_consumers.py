#!/usr/bin/env python3
"""Smoke-test package consumption from the configured Anaconda label."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


CHANNELS = {
    "test-label": [
        "https://conda.anaconda.org/anderslanglands/label/test",
        "https://conda.anaconda.org/anderslanglands",
        "conda-forge",
    ],
    "default-label": [
        "https://conda.anaconda.org/anderslanglands",
        "conda-forge",
    ],
}

EXPECTED_SOURCE = {
    "test-label": "https://conda.anaconda.org/anderslanglands/label/test",
    "default-label": "https://conda.anaconda.org/anderslanglands",
}


def write_manifest(
    path: Path,
    package: dict[str, object],
    platform: str,
    target: str,
    run_cmake_consumer: bool,
) -> None:
    channels = "\n".join(f'  "{channel}",' for channel in CHANNELS[target])
    extra_deps = ""
    if run_cmake_consumer:
        extra_deps = '\ncmake = ">=3.20"\nninja = "*"\nc-compiler = "*"\ncxx-compiler = "*"'

    path.write_text(
        f"""[workspace]
name = "{package['name']}-{package['version']}-{platform}-smoke"
channels = [
{channels}
]
platforms = ["{platform}"]
channel-priority = "strict"

[dependencies]
{package['name']} = {{ version = "=={package['version']}", build = "{package['build']}" }}{extra_deps}
""",
        encoding="utf-8",
    )


def pixi(*args: str) -> None:
    subprocess.run(["pixi", *args], check=True)


def pixi_json(*args: str) -> object:
    completed = subprocess.run(["pixi", *args], check=True, stdout=subprocess.PIPE, text=True)
    return json.loads(completed.stdout)


def check_installed_package(
    manifest: Path,
    package: dict[str, object],
    *,
    target: str,
) -> None:
    installed_packages = pixi_json(
        "list",
        "--json",
        "--manifest-path",
        str(manifest),
        str(package["name"]),
    )
    matches = [item for item in installed_packages if item["name"] == package["name"]]
    if len(matches) != 1:
        raise SystemExit(f"Expected one installed {package['name']} package, found {len(matches)}.")

    installed = matches[0]
    checks = {
        "version": package["version"],
        "build": package["build"],
        "subdir": package["subdir"],
        "file_name": package["file_name"],
        "source": EXPECTED_SOURCE[target],
    }
    for key, expected in checks.items():
        if installed.get(key) != expected:
            raise SystemExit(
                f"Installed {package['name']} {key} was {installed.get(key)!r}, expected {expected!r}."
            )


def package_needs_consumer_test(root_package: str, package: dict[str, object], recipe: Path) -> bool:
    if not (recipe / "tests" / "CMakeLists.txt").is_file():
        return False

    name = str(package["name"])
    return name == root_package or name.endswith("-dev")


def cmake_consumer_args(root_package: str, package: dict[str, object]) -> list[str]:
    name = str(package["name"])
    if root_package == "openexr" and name in {"openexr", "openexr-dev"}:
        return ["-DOPENEXR_CONSUMER_EXPECT_FULL=ON"]
    return []


def run_cmake_consumer(manifest: Path, recipe: Path, root_package: str, package: dict[str, object], tmp: Path) -> None:
    source = recipe.resolve() / "tests"
    build = tmp / f"build-{package['name']}"
    pixi(
        "run",
        "--manifest-path",
        str(manifest),
        "cmake",
        "-S",
        str(source),
        "-B",
        str(build),
        "-G",
        "Ninja",
        *cmake_consumer_args(root_package, package),
    )
    pixi("run", "--manifest-path", str(manifest), "cmake", "--build", str(build))


def load_artifact_manifest(path: Path, recipe: Path, platform: str) -> dict[str, object]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["recipe"] != recipe.as_posix():
        raise SystemExit(f"Artifact manifest recipe is {manifest['recipe']}, expected {recipe}.")
    if manifest["platform"] != platform:
        raise SystemExit(f"Artifact manifest platform is {manifest['platform']}, expected {platform}.")
    if not manifest.get("packages"):
        raise SystemExit(f"Artifact manifest {path} does not list any packages.")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--target", choices=sorted(CHANNELS), required=True)
    parser.add_argument("--artifact-manifest", required=True)
    args = parser.parse_args()

    recipe = Path(args.recipe)
    if len(recipe.parts) < 2:
        raise SystemExit(f"Recipe directory {recipe} should look like package/version.")

    artifact_manifest = load_artifact_manifest(Path(args.artifact_manifest), recipe, args.platform)
    root_package = recipe.parts[-2]
    for package in artifact_manifest["packages"]:
        with tempfile.TemporaryDirectory(prefix=f"{package['name']}-{package['version']}-smoke-") as tmp_raw:
            tmp = Path(tmp_raw)
            run_consumer = package_needs_consumer_test(root_package, package, recipe)
            manifest = tmp / "pixi.toml"
            write_manifest(manifest, package, args.platform, args.target, run_consumer)
            pixi("install", "--manifest-path", str(manifest))
            check_installed_package(manifest, package, target=args.target)
            if run_consumer:
                run_cmake_consumer(manifest, recipe, root_package, package, tmp)

    print(
        f"Smoke-tested {len(artifact_manifest['packages'])} package(s) from "
        f"{args.target} for {recipe} on {args.platform}.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
