import os
import pathlib
import re
import sys


prefix = pathlib.Path(os.environ["PREFIX"])
if sys.platform == "win32":
    library_prefix = pathlib.Path(os.environ.get("LIBRARY_PREFIX", prefix / "Library"))
    activation = prefix / "etc" / "conda" / "activate.d" / "optix-dev.bat"
else:
    library_prefix = prefix
    activation = prefix / "etc" / "conda" / "activate.d" / "optix-dev.sh"

include_dir = pathlib.Path(
    os.environ.get("OPTIX_INCLUDE_DIR", library_prefix / "opt" / "optix-dev-9.1.0" / "include")
)
optix_h = include_dir / "optix.h"
stubs_h = include_dir / "optix_stubs.h"
function_table_h = include_dir / "optix_function_table_definition.h"
config = library_prefix / "lib" / "cmake" / "OptiX" / "OptiXConfig.cmake"
marker = library_prefix / "opt" / "optix-dev-9.1.0" / ".optix-dev-9.1.0-3a29b2254107fdfbb5e6bbad3ec154dd682149121f61e9c406607ac7b52a6ba6.installed"
unexpected_headers = [prefix / "include" / "optix.h", library_prefix / "include" / "optix.h"]

for unexpected_header in unexpected_headers:
    if unexpected_header.exists():
        raise SystemExit(
            f"OptiX headers should not be installed directly in a prefix include directory: {unexpected_header}"
        )

for path in (activation, marker, optix_h, stubs_h, function_table_h, config):
    if not path.is_file():
        raise SystemExit(f"Missing expected OptiX wrapper file: {path}")

expected_hash = "3a29b2254107fdfbb5e6bbad3ec154dd682149121f61e9c406607ac7b52a6ba6"
if marker.read_text(encoding="utf-8").strip() != expected_hash:
    raise SystemExit(f"OptiX marker does not contain the expected archive checksum: {marker}")

try:
    optix_h.relative_to(library_prefix)
except ValueError as exc:
    raise SystemExit(f"Downloaded OptiX header is outside the active library prefix: {optix_h}") from exc

text = optix_h.read_text(encoding="utf-8", errors="replace")
match = re.search(r"^\s*#\s*define\s+OPTIX_VERSION\s+(\d+)\b", text, re.MULTILINE)
if not match:
    raise SystemExit("optix.h does not define OPTIX_VERSION")

version = int(match.group(1))
if version < 90100 or version >= 90200:
    raise SystemExit(f"Expected OptiX 9.1.x headers, found OPTIX_VERSION={version}")

config_text = config.read_text(encoding="utf-8")
for expected in (
    "OptiX::OptiX",
    "OptiX_INCLUDE_DIR",
    "opt/optix-dev-9.1.0",
    "9.1.0",
):
    if expected not in config_text:
        raise SystemExit(f"OptiX CMake config is missing {expected!r}")
