#!/usr/bin/env python3
"""Exercise the default OpenImageIO format plugin set through oiiotool."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess


CORE_PLUGIN_FORMATS = {
    "bmp",
    "cineon",
    "dds",
    "dpx",
    "fits",
    "hdr",
    "ico",
    "iff",
    "jpeg",
    "null",
    "openexr",
    "png",
    "pnm",
    "psd",
    "rla",
    "sgi",
    "softimage",
    "targa",
    "term",
    "tiff",
    "zfile",
}

OPTIONAL_PLUGIN_FORMATS = {
    "dicom",
    "ffmpeg",
    "gif",
    "heif",
    "jpeg2000",
    "openvdb",
    "raw",
    "webp",
}


def plugin_dir() -> Path:
    library_bin = os.environ.get("LIBRARY_BIN")
    if library_bin:
        return Path(library_bin)
    return Path(os.environ["PREFIX"]) / "lib"


def ensure_core_formats_are_embedded() -> None:
    external_core_plugins = []
    for fmt in CORE_PLUGIN_FORMATS:
        external_core_plugins.extend(plugin_dir().glob(f"{fmt}.imageio.*"))
    external_core_plugins = [
        path
        for path in external_core_plugins
        if path.suffix.lower() not in {".lib", ".pdb", ".exp"}
    ]
    if external_core_plugins:
        raise SystemExit(
            "Core formats should be embedded in openimageio-lib, not packaged "
            "as external plugin DSOs:\n"
            + "\n".join(str(path) for path in sorted(external_core_plugins))
        )


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


def ensure_optional_formats_are_external() -> None:
    formats = parse_format_list(run("oiiotool", "--list-formats"))
    embedded_optional = sorted(OPTIONAL_PLUGIN_FORMATS & formats)
    if embedded_optional:
        raise SystemExit(
            "Optional formats should be absent from openimageio-lib unless their "
            "plugin packages are installed: "
            + ", ".join(embedded_optional)
        )


def ensure_core_formats_are_registered() -> None:
    formats = parse_format_list(run("oiiotool", "--list-formats"))
    missing_core = sorted(CORE_PLUGIN_FORMATS - formats)
    if missing_core:
        raise SystemExit(
            "Core formats should be registered by openimageio-lib: "
            + ", ".join(missing_core)
        )


def make_and_info(path: str, datatype: str = "uint8") -> str:
    run("oiiotool", "--pattern", "checker", "8x8", "3", "-d", datatype, "-o", path)
    return run("oiiotool", "--info", path).lower()


def main() -> None:
    ensure_core_formats_are_embedded()
    ensure_core_formats_are_registered()
    ensure_optional_formats_are_external()

    checks = {
        "checker.png": "png",
        "checker.tif": "tiff",
        "checker.jpg": "jpeg",
        "constant.exr": "openexr",
    }
    for path, expected in checks.items():
        datatype = "half" if path.endswith(".exr") else "uint8"
        info = make_and_info(path, datatype)
        if expected not in info:
            raise SystemExit(f"{path} did not report expected format {expected!r}:\n{info}")


if __name__ == "__main__":
    main()
