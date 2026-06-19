from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "sample.pts"


def run(*args: str) -> str:
    completed = subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return completed.stdout


def require(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f"Expected {expected!r} in output:\n{text}")


info = run("partinfo", str(FIXTURE))
require(info, "Number of particles:  2")
require(info, "VECTOR")
require(info, "position")

attr = run("partattr", str(FIXTURE), "position")
require(attr, "position[0]=(1,3,2)")
require(attr, "position[1]=(4,6,5)")

converted = Path("partio_tools_copy.pda.gz")
run("partconvert", str(FIXTURE), str(converted))

converted_info = run("partinfo", str(converted))
require(converted_info, "Number of particles:  2")
require(converted_info, "position")

converted_attr = run("partattr", str(converted), "position")
require(converted_attr, "position[0]=(1,3,2)")
require(converted_attr, "position[1]=(4,6,5)")
