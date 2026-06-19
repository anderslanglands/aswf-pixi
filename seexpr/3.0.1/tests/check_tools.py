from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def main() -> None:
    is_windows = sys.platform.startswith("win")
    prefix = Path(os.environ["LIBRARY_PREFIX"] if is_windows else os.environ["PREFIX"])
    suffix = ".exe" if is_windows else ""
    utils_dir = prefix / "share" / "SeExpr2" / "utils"
    eval_tool = utils_dir / f"eval{suffix}"
    list_var_tool = utils_dir / f"listVar{suffix}"

    if not eval_tool.is_file():
        raise SystemExit(f"Missing SeExpr eval utility: {eval_tool}")
    if not list_var_tool.is_file():
        raise SystemExit(f"Missing SeExpr listVar utility: {list_var_tool}")

    eval_result = subprocess.run(
        [str(eval_tool), "1+2"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if eval_result.returncode != 0:
        raise SystemExit(eval_result.stdout + eval_result.stderr)
    if "sum 15" not in eval_result.stderr:
        raise SystemExit(eval_result.stdout + eval_result.stderr)

    list_result = subprocess.run(
        [str(list_var_tool)],
        check=False,
        input="$x=1;$x+2\nq\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if list_result.returncode != 0:
        raise SystemExit(list_result.stdout + list_result.stderr)
    if "number of variable refs: 1" not in list_result.stdout:
        raise SystemExit(list_result.stdout + list_result.stderr)


if __name__ == "__main__":
    main()
