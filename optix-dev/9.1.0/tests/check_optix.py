import os
import pathlib
import re


prefix = pathlib.Path(os.environ["PREFIX"])
include_dir = prefix / "include"
optix_h = include_dir / "optix.h"
stubs_h = include_dir / "optix_stubs.h"
function_table_h = include_dir / "optix_function_table_definition.h"
config = prefix / "lib" / "cmake" / "OptiX" / "OptiXConfig.cmake"

for path in (optix_h, stubs_h, function_table_h, config):
    if not path.is_file():
        raise SystemExit(f"Missing expected OptiX wrapper file: {path}")

text = optix_h.read_text(encoding="utf-8", errors="replace")
match = re.search(r"^\s*#\s*define\s+OPTIX_VERSION\s+(\d+)\b", text, re.MULTILINE)
if not match:
    raise SystemExit("optix.h does not define OPTIX_VERSION")

version = int(match.group(1))
if version < 90100 or version >= 90200:
    raise SystemExit(f"Expected OptiX 9.1.x headers, found OPTIX_VERSION={version}")

config_text = config.read_text(encoding="utf-8")
for expected in ("OptiX::OptiX", "OptiX_INCLUDE_DIR", "9.1.0"):
    if expected not in config_text:
        raise SystemExit(f"OptiX CMake config is missing {expected!r}")
