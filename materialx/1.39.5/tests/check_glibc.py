import json
import os
from pathlib import Path
import re
import subprocess
import sys


package = sys.argv[1]
maximum = tuple(map(int, sys.argv[2].split(".")))
prefix = Path(os.environ["PREFIX"])
records = list((prefix / "conda-meta").glob(f"{package}-*.json"))
assert len(records) == 1, records

record = json.loads(records[0].read_text())
versions = []
for relative_path in record["files"]:
    path = prefix / relative_path
    if not path.is_file():
        continue
    result = subprocess.run(
        ["readelf", "--version-info", path],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    versions.extend(
        tuple(map(int, match.split(".")))
        for match in re.findall(r"Name: GLIBC_([0-9.]+)", result.stdout)
    )

assert versions, f"No GLIBC symbol versions found in {package} files"
assert max(versions) <= maximum, (package, max(versions), maximum)
