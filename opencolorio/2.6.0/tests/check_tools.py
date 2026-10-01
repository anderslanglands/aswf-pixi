from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path


TOOLS = (
    "ocioarchive",
    "ociobakelut",
    "ociocheck",
    "ociochecklut",
    "ocioconvert",
    "ociocpuinfo",
    "ociodisplay",
    "ociolutimage",
    "ociomakeclf",
    "ociomergeconfigs",
    "ocioperf",
    "ociowrite",
)

HELP_COMMANDS = {
    "ocioarchive": ["ocioarchive", "--help"],
    "ociobakelut": ["ociobakelut", "--help"],
    "ociocheck": ["ociocheck", "--help"],
    "ociochecklut": ["ociochecklut", "--help"],
    "ocioconvert": ["ocioconvert", "--help"],
    "ociodisplay": ["ociodisplay", "-h"],
    "ociolutimage": ["ociolutimage"],
    "ociomakeclf": ["ociomakeclf", "--help"],
    "ociomergeconfigs": ["ociomergeconfigs", "--help"],
    "ocioperf": ["ocioperf", "--help"],
    "ociowrite": ["ociowrite", "--help"],
}


def run_for_text(command: list[str], expected: str) -> str:
    result = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )
    if expected not in result.stdout.lower():
        raise SystemExit(
            f"{command!r} did not print expected text {expected!r}; "
            f"exit code {result.returncode}, output:\n{result.stdout}"
        )
    return result.stdout


def linked_libraries(path: str) -> str:
    system = platform.system()
    if system == "Linux":
        return subprocess.run(
            ["ldd", path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
        ).stdout
    if system == "Darwin":
        return subprocess.run(
            ["otool", "-L", path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
        ).stdout
    return ""


missing = [tool for tool in TOOLS if shutil.which(tool) is None]
if missing:
    raise SystemExit(f"Missing OpenColorIO tools: {missing}")

cpuinfo = subprocess.run(
    ["ociocpuinfo"],
    check=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    timeout=30,
)
if "hassse2" not in cpuinfo.stdout.lower():
    raise SystemExit(f"ociocpuinfo output did not look valid:\n{cpuinfo.stdout}")

for tool, command in HELP_COMMANDS.items():
    expected = "help:" if tool == "ociodisplay" else "usage"
    run_for_text(command, expected)

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    exr = tmp / "lut.exr"
    spi3d = tmp / "lut.spi3d"

    subprocess.run(
        [
            "ociolutimage",
            "--generate",
            "--cubesize",
            "2",
            "--maxwidth",
            "16",
            "--output",
            os.fspath(exr),
        ],
        check=True,
        timeout=30,
    )
    if not exr.exists() or exr.stat().st_size == 0:
        raise SystemExit("ociolutimage did not write a non-empty EXR file")

    subprocess.run(
        [
            "ociolutimage",
            "--extract",
            "--cubesize",
            "2",
            "--input",
            os.fspath(exr),
            "--output",
            os.fspath(spi3d),
        ],
        check=True,
        timeout=30,
    )
    if not spi3d.exists() or spi3d.stat().st_size == 0:
        raise SystemExit("ociolutimage did not read the EXR file back into a LUT")

for tool in TOOLS:
    libraries = linked_libraries(shutil.which(tool) or "")
    if "openimageio" in libraries.lower():
        raise SystemExit(f"{tool} links against OpenImageIO:\n{libraries}")
