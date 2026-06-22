import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile


prefix = pathlib.Path(os.environ["PREFIX"])
records = sorted((prefix / "conda-meta").glob("optix-dev-9.1.0-*.json"))
if not records:
    raise SystemExit("Could not find optix-dev conda-meta record")

record = json.loads(records[-1].read_text(encoding="utf-8"))
files = set(record.get("files", []))
paths_data = record.get("paths_data", {})
for entry in paths_data.get("paths", []):
    path = entry.get("_path") or entry.get("path")
    if path:
        files.add(path)

allowed_payload_names = {"README.txt", "optix-dev-activate.ps1"}
for package_file in sorted(files):
    normalized = package_file.replace("\\", "/")
    name = pathlib.PurePosixPath(normalized).name
    if normalized.startswith(("include/", "Library/include/")):
        raise SystemExit(f"optix-dev package redistributes include payload: {normalized}")
    if normalized.startswith(("opt/", "Library/opt/")):
        raise SystemExit(f"optix-dev package redistributes opt payload: {normalized}")
    if normalized.startswith(("share/optix-dev/", "Library/share/optix-dev/")) and name not in allowed_payload_names:
        raise SystemExit(f"optix-dev package redistributes non-stub share payload: {normalized}")
    if name in {
        "optix.h",
        "optix_host.h",
        "optix_stubs.h",
        "optix_types.h",
        "optix_function_table_definition.h",
        "LICENSE.txt",
        "license_info.txt",
        "README.md",
    }:
        raise SystemExit(f"optix-dev package redistributes NVIDIA optix-dev payload: {normalized}")
    if name.endswith((".tar", ".tar.gz", ".tgz", ".zip")):
        raise SystemExit(f"optix-dev package redistributes an archive payload: {normalized}")

if sys.platform == "win32":
    helper = prefix / "Library" / "share" / "optix-dev" / "optix-dev-activate.ps1"
    helper_text = helper.read_text(encoding="utf-8")
    for forbidden in ("Get-FileHash", "Expand-Archive"):
        if forbidden in helper_text:
            raise SystemExit(f"Windows activation helper depends on module-backed cmdlet: {forbidden}")
    for expected in (
        "System.Net.WebClient",
        "System.Security.Cryptography.SHA256",
        "System.IO.Compression.ZipFile",
    ):
        if expected not in helper_text:
            raise SystemExit(f"Windows activation helper is missing self-contained API use: {expected}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        fake_prefix = tmp_path / "prefix"
        fake_library_prefix = fake_prefix / "Library"
        fake_temp = tmp_path / "temp"
        fake_prefix.mkdir()
        fake_library_prefix.mkdir()
        fake_temp.mkdir()

        bad_archive = tmp_path / "not-optix-dev.zip"
        bad_archive.write_text("not the optix-dev archive\n", encoding="utf-8")
        test_helper = tmp_path / "optix-dev-activate.ps1"
        test_helper.write_text(
            re.sub(
                r'\$optixDevArchiveUrl = ".*"',
                f'$optixDevArchiveUrl = "{bad_archive.resolve().as_uri()}"',
                helper_text,
                count=1,
            ),
            encoding="utf-8",
        )
        wrapper = tmp_path / "run-helper.ps1"
        helper_literal = str(test_helper).replace("'", "''")
        wrapper.write_text(
            f"""$ErrorActionPreference = "Stop"
function Get-FileHash {{ throw "unexpected Get-FileHash invocation" }}
function Expand-Archive {{ throw "unexpected Expand-Archive invocation" }}
. '{helper_literal}'
""",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["CONDA_PREFIX"] = str(fake_prefix)
        env["PREFIX"] = str(fake_prefix)
        env["LIBRARY_PREFIX"] = str(fake_library_prefix)
        env["TEMP"] = str(fake_temp)
        env["TMP"] = str(fake_temp)

        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wrapper)],
            check=False,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        output = completed.stdout + completed.stderr
        if completed.returncode == 0:
            raise SystemExit("Windows activation succeeded with a fake archive payload")
        if "checksum mismatch" not in output:
            raise SystemExit(f"Windows activation did not fail at checksum verification:\n{output}")
        install_root = fake_library_prefix / "opt" / "optix-dev-9.1.0"
        if install_root.exists():
            raise SystemExit(f"Windows activation left a partial install after checksum failure: {install_root}")
        leftovers = sorted(fake_temp.glob("optix-dev.*"))
        if leftovers:
            formatted = ", ".join(str(path) for path in leftovers)
            raise SystemExit(f"Windows activation left temporary directories after checksum failure: {formatted}")
