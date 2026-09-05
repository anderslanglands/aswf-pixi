import os
from pathlib import Path
import subprocess
import sys


def tool_path(name: str) -> Path:
    if os.name == "nt":
        return Path(os.environ["LIBRARY_BIN"]) / f"{name}.exe"
    return Path(os.environ["PREFIX"]) / "bin" / name


def main() -> int:
    for name in ["mdlc", "mdlm", "mdltlc", "i18n", "mdl_distiller_cli"]:
        path = tool_path(name)
        if not path.is_file():
            print(f"Missing tool: {path}", file=sys.stderr)
            return 1

        result = subprocess.run(
            [str(path), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
        )
        output = result.stdout.lower()
        if result.returncode not in {0, 1} or ("usage" not in output and "option" not in output):
            print(f"Unexpected help output from {path}:\n{result.stdout}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
