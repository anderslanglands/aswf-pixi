import os
import pathlib
import stat
import subprocess
import tempfile


prefix = pathlib.Path(os.environ["PREFIX"])
activation = prefix / "etc" / "conda" / "activate.d" / "optix-dev.sh"
if not activation.is_file():
    raise SystemExit(f"Missing activation script: {activation}")

script_text = activation.read_text(encoding="utf-8")
expected_url = "https://github.com/NVIDIA/optix-dev/archive/refs/tags/${optix_dev_tag}.tar.gz"
expected_hash = "3a29b2254107fdfbb5e6bbad3ec154dd682149121f61e9c406607ac7b52a6ba6"
for expected in ("v9.1.0", expected_url, expected_hash, "sha256sum", "checksum mismatch"):
    if expected not in script_text:
        raise SystemExit(f"Activation script is missing checksum pinning text: {expected!r}")

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = pathlib.Path(tmp)
    fake_prefix = tmp_path / "prefix"
    fake_bin = tmp_path / "bin"
    fake_tmp = tmp_path / "tmp"
    fake_prefix.mkdir()
    fake_bin.mkdir()
    fake_tmp.mkdir()

    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        """#!/usr/bin/env sh
out=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --output)
      shift
      out="$1"
      ;;
  esac
  shift || true
done
if [ -z "$out" ]; then
  exit 2
fi
printf '%s\n' 'not the optix-dev archive' > "$out"
exit 0
""",
        encoding="utf-8",
    )
    fake_curl.chmod(fake_curl.stat().st_mode | stat.S_IXUSR)

    env = os.environ.copy()
    env["CONDA_PREFIX"] = fake_prefix.as_posix()
    env["PREFIX"] = fake_prefix.as_posix()
    env["PATH"] = fake_bin.as_posix() + os.pathsep + env["PATH"]
    env["TMPDIR"] = fake_tmp.as_posix()

    completed = subprocess.run(
        ["sh", "-c", f'. "{activation}"'],
        check=False,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    output = completed.stdout + completed.stderr
    if completed.returncode == 0:
        raise SystemExit("Activation succeeded with a fake archive payload")
    if "checksum mismatch" not in output:
        raise SystemExit(f"Activation did not fail at checksum verification:\n{output}")
    if (fake_prefix / "opt" / "optix-dev-9.1.0" / "include" / "optix.h").exists():
        raise SystemExit("Activation installed headers after checksum failure")
