#!/usr/bin/env python3
"""Smoke-test package consumption from the configured Anaconda label."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


CHANNELS = {
    "local-artifacts": [],
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
    "local-artifacts": None,
    "test-label": "https://conda.anaconda.org/anderslanglands/label/test",
    "default-label": "https://conda.anaconda.org/anderslanglands",
}


def local_channel_uri(path: str) -> str:
    return Path(path).resolve().as_uri()


def channels_for_target(target: str, local_channel: str | None) -> list[str]:
    if target == "local-artifacts":
        if not local_channel:
            raise SystemExit("--local-channel is required with --target local-artifacts.")
        return [local_channel_uri(local_channel), "conda-forge"]
    if local_channel:
        raise SystemExit("--local-channel is only valid with --target local-artifacts.")
    return CHANNELS[target]


def channel_priority_for_recipe(recipe: Path) -> str:
    if len(recipe.parts) >= 2 and recipe.parts[-2] == "openusd-typhoon":
        return "disabled"
    return "strict"


def write_manifest(
    path: Path,
    package: dict[str, object],
    platform: str,
    channels: list[str],
    channel_priority: str,
    run_cmake_consumer: bool,
) -> None:
    channel_lines = "\n".join(f'  "{channel}",' for channel in channels)
    extra_deps = ""
    if run_cmake_consumer:
        extra_deps = '\ncmake = ">=3.20"\nninja = "*"\nc-compiler = "*"\ncxx-compiler = "*"'

    path.write_text(
        f"""[workspace]
name = "{package['name']}-{package['version']}-{platform}-smoke"
channels = [
{channel_lines}
]
platforms = ["{platform}"]
channel-priority = "{channel_priority}"

[dependencies]
{package['name']} = {{ version = "=={package['version']}", build = "{package['build']}" }}{extra_deps}
""",
        encoding="utf-8",
    )


def pixi(*args: str, env: dict[str, str] | None = None) -> None:
    subprocess_env = None
    if env is not None:
        subprocess_env = {**os.environ, **env}
    subprocess.run(["pixi", *args], check=True, env=subprocess_env)


def pixi_json(*args: str) -> object:
    completed = subprocess.run(["pixi", *args], check=True, stdout=subprocess.PIPE, text=True)
    return json.loads(completed.stdout)


def remove_tree_best_effort(path: Path) -> None:
    last_error: OSError | None = None
    for attempt in range(8):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            time.sleep(min(0.25 * (2**attempt), 2.0))
    print(f"Warning: failed to remove temporary smoke directory {path}: {last_error}", file=sys.stderr)


def check_installed_package(
    manifest: Path,
    package: dict[str, object],
    *,
    target: str,
    local_channel: str | None,
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
    checks: dict[str, object] = {
        "version": package["version"],
        "build": package["build"],
        "subdir": package["subdir"],
        "file_name": package["file_name"],
    }
    for key, expected in checks.items():
        if installed.get(key) != expected:
            raise SystemExit(
                f"Installed {package['name']} {key} was {installed.get(key)!r}, expected {expected!r}."
            )

    source = installed.get("source")
    expected_source = EXPECTED_SOURCE[target]
    if expected_source is not None and source != expected_source:
        raise SystemExit(f"Installed {package['name']} source was {source!r}, expected {expected_source!r}.")
    if target == "local-artifacts":
        expected_prefix = local_channel_uri(str(local_channel)).rstrip("/")
        expected_package = Path(str(local_channel)) / str(package["path"])
        if not expected_package.is_file():
            raise SystemExit(f"Manifest-listed local package does not exist: {expected_package}")
        if not isinstance(source, str) or not source.rstrip("/").startswith(expected_prefix):
            raise SystemExit(
                f"Installed {package['name']} source was {source!r}, expected local channel {expected_prefix!r}."
            )


def package_needs_consumer_test(root_package: str, package: dict[str, object], recipe: Path) -> bool:
    if not (recipe / "tests" / "CMakeLists.txt").is_file():
        return False

    name = str(package["name"])
    if root_package == "openqmc" and name == "openqmc-header-only":
        return True
    if root_package == "openvdb" and name == "nanovdb":
        return True
    if root_package == "opensubdiv" and name in {"opensubdiv-gpu", "opensubdiv-cuda"}:
        return True
    return name == root_package or name.endswith("-dev")


def cmake_consumer_args(root_package: str, package: dict[str, object], platform: str) -> list[str]:
    name = str(package["name"])
    if root_package == "openexr":
        args = [f"-DOPENEXR_CONSUMER_EXPECT_VERSION={package['version']}"]
        if name in {"openexr", "openexr-dev"}:
            args.append("-DOPENEXR_CONSUMER_EXPECT_FULL=ON")
        return args
    if root_package == "opensubdiv":
        if name in {"opensubdiv", "opensubdiv-dev"}:
            return ["-DOPENSUBDIV_CONSUMER_EXPECT_CPU_ONLY=ON"]
        if name in {"opensubdiv-gpu", "opensubdiv-gpu-dev"}:
            args = ["-DOPENSUBDIV_CONSUMER_REQUIRE_GPU=ON"]
            if platform.startswith(("linux-", "win-")):
                args.extend(
                    [
                        "-DOPENSUBDIV_CONSUMER_REQUIRE_OPENGL=ON",
                        "-DOPENSUBDIV_CONSUMER_REQUIRE_TBB=ON",
                        "-DOPENSUBDIV_CONSUMER_FORBID_CUDA=ON",
                        "-DOPENSUBDIV_CONSUMER_FORBID_METAL=ON",
                    ]
                )
            elif platform.startswith("osx-"):
                args.extend(
                    [
                        "-DOPENSUBDIV_CONSUMER_REQUIRE_METAL=ON",
                        "-DOPENSUBDIV_CONSUMER_FORBID_CUDA=ON",
                    ]
                )
            return args
        if name in {"opensubdiv-cuda", "opensubdiv-cuda-dev"}:
            args = ["-DOPENSUBDIV_CONSUMER_REQUIRE_GPU=ON", "-DOPENSUBDIV_CONSUMER_REQUIRE_CUDA=ON"]
            if platform.startswith(("linux-", "win-")):
                args.extend(
                    [
                        "-DOPENSUBDIV_CONSUMER_REQUIRE_OPENGL=ON",
                        "-DOPENSUBDIV_CONSUMER_REQUIRE_TBB=ON",
                        "-DOPENSUBDIV_CONSUMER_FORBID_METAL=ON",
                    ]
                )
            return args
    if root_package == "openqmc" and name == "openqmc-header-only":
        return ["-DOPENQMC_CONSUMER_EXPECT_HEADER_ONLY=ON"]
    if root_package == "openvdb":
        if name in {"openvdb", "openvdb-dev"}:
            return ["-DBUILD_NANOVDB_CONSUMER=OFF"]
        if name in {"nanovdb", "nanovdb-dev"}:
            return ["-DBUILD_OPENVDB_CONSUMER=OFF"]
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
        "-DCMAKE_BUILD_TYPE=Release",
        *cmake_consumer_args(root_package, package, str(package.get("subdir", ""))),
    )
    pixi("run", "--manifest-path", str(manifest), "cmake", "--build", str(build))
    pixi(
        "run",
        "--manifest-path",
        str(manifest),
        "ctest",
        "--test-dir",
        str(build),
        "--output-on-failure",
    )


def run_optix_dev_windows_checks(manifest: Path, recipe: Path) -> None:
    tests = recipe.resolve() / "tests"
    prefix = manifest.parent / ".pixi" / "envs" / "default"
    if not prefix.is_dir():
        raise SystemExit(f"Expected pixi environment prefix does not exist: {prefix}")
    script_env = {
        "CONDA_PREFIX": str(prefix),
        "PREFIX": str(prefix),
        "LIBRARY_PREFIX": str(prefix / "Library"),
    }
    powershell_args = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
    ]
    pixi(
        "run",
        "--manifest-path",
        str(manifest),
        *powershell_args,
        str(tests / "check_windows_stub_payload.ps1"),
        env=script_env,
    )
    batch_check = tests / "check_optix_batch_env.ps1"
    batch_wrapper = manifest.parent / "check-optix-batch-env.bat"
    batch_wrapper.write_text(
        "\n".join(
            [
                "@echo off",
                'call "%PREFIX%\\etc\\conda\\activate.d\\optix-dev.bat"',
                "if errorlevel 1 exit /b %errorlevel%",
                f'powershell -NoProfile -ExecutionPolicy Bypass -File "{batch_check}"',
                "if errorlevel 1 exit /b %errorlevel%",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pixi(
        "run",
        "--manifest-path",
        str(manifest),
        "cmd",
        "/d",
        "/c",
        str(batch_wrapper),
        env=script_env,
    )
    pixi(
        "run",
        "--manifest-path",
        str(manifest),
        *powershell_args,
        str(tests / "check_optix_powershell.ps1"),
        env=script_env,
    )


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
    parser.add_argument("--local-channel")
    parser.add_argument("--artifact-manifest", required=True)
    args = parser.parse_args()

    recipe = Path(args.recipe)
    if len(recipe.parts) < 2:
        raise SystemExit(f"Recipe directory {recipe} should look like package/version.")

    artifact_manifest = load_artifact_manifest(Path(args.artifact_manifest), recipe, args.platform)
    root_package = recipe.parts[-2]
    channels = channels_for_target(args.target, args.local_channel)
    channel_priority = channel_priority_for_recipe(recipe)
    for package in artifact_manifest["packages"]:
        tmp = Path(tempfile.mkdtemp(prefix=f"{package['name']}-{package['version']}-smoke-"))
        try:
            run_consumer = package_needs_consumer_test(root_package, package, recipe)
            manifest = tmp / "pixi.toml"
            write_manifest(manifest, package, args.platform, channels, channel_priority, run_consumer)
            pixi("install", "--manifest-path", str(manifest))
            check_installed_package(manifest, package, target=args.target, local_channel=args.local_channel)
            if root_package == "optix-dev" and package["name"] == "optix-dev" and args.platform == "win-64":
                run_optix_dev_windows_checks(manifest, recipe)
            if run_consumer:
                run_cmake_consumer(manifest, recipe, root_package, package, tmp)
        finally:
            remove_tree_best_effort(tmp)

    print(
        f"Smoke-tested {len(artifact_manifest['packages'])} package(s) from "
        f"{args.target} for {recipe} on {args.platform}.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
