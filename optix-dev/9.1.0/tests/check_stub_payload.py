import json
import os
import pathlib


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
