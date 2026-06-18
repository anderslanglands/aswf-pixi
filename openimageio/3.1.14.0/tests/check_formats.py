#!/usr/bin/env python3
"""Check that external OpenImageIO format plugins are installed and usable."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
import subprocess


ROUNDTRIP_EXTENSIONS = {
    "gif": "gif",
    "webp": "webp",
    "jpeg2000": "j2c",
    "jpegxl": "jxl",
    "heif": "heif",
}


def plugin_dir() -> Path:
    library_bin = os.environ.get("LIBRARY_BIN")
    if library_bin:
        return Path(library_bin)
    return Path(os.environ["PREFIX"]) / "lib"


def normalized(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def require_packaged_plugin_path() -> None:
    expected = normalized(plugin_dir())
    configured = os.environ.get("OPENIMAGEIO_PLUGIN_PATH", "")
    paths = [normalized(path) for path in configured.split(os.pathsep) if path]
    if expected not in paths:
        raise SystemExit(
            "OPENIMAGEIO_PLUGIN_PATH does not include the package plugin directory "
            f"{plugin_dir()}: {configured!r}"
        )


def matching_plugins(fmt: str) -> list[Path]:
    candidates = []
    for path in plugin_dir().glob(f"{fmt}.imageio.*"):
        if path.suffix.lower() not in {".lib", ".pdb", ".exp"}:
            candidates.append(path)
    return candidates


def run(*args: str) -> str:
    completed = subprocess.run(
        [*args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return completed.stdout


def parse_format_list(output: str) -> set[str]:
    formats: set[str] = set()
    for line in output.lower().splitlines():
        match = re.match(r"^\s+([a-z0-9_+-]+)\s+:", line)
        if match:
            formats.add(match.group(1))
    return formats


def check_discovery(expected: list[str]) -> None:
    completed = subprocess.run(
        ["oiiotool", "--list-formats"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    formats = parse_format_list(completed.stdout)
    missing_formats = [fmt for fmt in expected if fmt not in formats]
    if missing_formats:
        raise SystemExit(
            "oiiotool did not list expected format(s): "
            + ", ".join(missing_formats)
            + "\n"
            + completed.stdout
        )


def check_roundtrip(fmt: str) -> None:
    ext = ROUNDTRIP_EXTENSIONS[fmt]
    path = Path(f"checker.{ext}")
    run("oiiotool", "--pattern", "checker", "8x8", "3", "-d", "uint8", "-o", str(path))
    run("oiiotool", "--info", str(path))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("formats", nargs="+")
    parser.add_argument(
        "--roundtrip",
        action="append",
        default=[],
        choices=sorted(ROUNDTRIP_EXTENSIONS),
        help="Also write and read back a small file for this writable format.",
    )
    args = parser.parse_args()

    expected = [fmt.lower() for fmt in args.formats]
    roundtrip = [fmt.lower() for fmt in args.roundtrip]

    require_packaged_plugin_path()

    missing_files = [fmt for fmt in expected if not matching_plugins(fmt)]
    if missing_files:
        missing = ", ".join(missing_files)
        raise SystemExit(f"Missing plugin files for: {missing}")

    check_discovery(expected)

    for fmt in roundtrip:
        check_roundtrip(fmt)


if __name__ == "__main__":
    main()
