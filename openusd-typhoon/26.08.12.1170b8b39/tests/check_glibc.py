import json
import os
from pathlib import Path
import re
import subprocess


prefix = Path(os.environ["PREFIX"])
records = list((prefix / "conda-meta").glob("openusd-typhoon-*.json"))
assert len(records) == 1, records

record = json.loads(records[0].read_text())
glibc_requirement = next(
    requirement
    for requirement in record["depends"]
    if requirement.startswith("__glibc >=")
)
maximum = tuple(
    map(int, re.match(r"__glibc >=([0-9.]+)", glibc_requirement).group(1).split("."))
)
files = record["files"]
versions = []
for relative_path in files:
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

assert versions, "No GLIBC symbol versions found in openusd-typhoon files"
assert max(versions) <= maximum, (max(versions), maximum)
