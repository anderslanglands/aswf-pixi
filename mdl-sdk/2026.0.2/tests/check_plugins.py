import ctypes
import os
from pathlib import Path
import sys


def plugin_path(name: str) -> Path:
    if os.name == "nt":
        return Path(os.environ["LIBRARY_BIN"]) / f"{name}.dll"
    return Path(os.environ["PREFIX"]) / "lib" / f"{name}.so"


def main() -> int:
    for name in sys.argv[1:]:
        path = plugin_path(name)
        if not path.is_file():
            print(f"Missing plugin: {path}", file=sys.stderr)
            return 1
        ctypes.CDLL(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
