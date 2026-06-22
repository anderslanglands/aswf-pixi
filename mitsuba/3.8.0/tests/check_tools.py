import os
import subprocess
import sys
import uuid
from pathlib import Path


SCENE_XML = """<scene version="3.0.0">
    <integrator type="path">
        <integer name="max_depth" value="2"/>
    </integrator>
    <sensor type="perspective">
        <float name="fov" value="45"/>
        <transform name="to_world">
            <lookat origin="0, 0, 3" target="0, 0, 0" up="0, 1, 0"/>
        </transform>
        <sampler type="independent">
            <integer name="sample_count" value="1"/>
        </sampler>
        <film type="hdrfilm">
            <integer name="width" value="4"/>
            <integer name="height" value="4"/>
            <string name="pixel_format" value="rgb"/>
        </film>
    </sensor>
    <shape type="rectangle">
        <transform name="to_world">
            <translate x="0" y="0" z="0"/>
        </transform>
        <emitter type="area">
            <rgb name="radiance" value="1, 1, 1"/>
        </emitter>
    </shape>
</scene>
"""


def configure_drjit_llvm_path() -> None:
    if "DRJIT_LIBLLVM_PATH" in os.environ:
        return

    prefix = Path(sys.prefix)
    candidates = [
        prefix / "lib" / "libLLVM-22.so",
        prefix / "lib" / "libLLVM.so",
        prefix / "Library" / "bin" / "LLVM-C.dll",
        prefix / "Library" / "bin" / "LLVM.dll",
        prefix / "lib" / "libLLVM.dylib",
    ]
    for candidate in candidates:
        if candidate.is_file():
            os.environ["DRJIT_LIBLLVM_PATH"] = str(candidate)
            return


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"Command failed with exit code {result.returncode}: {command!r}\n"
            f"{result.stdout}"
        )
    return result


def main() -> None:
    configure_drjit_llvm_path()

    help_result = run_checked(["mitsuba", "--help"])
    if "Mitsuba" not in help_result.stdout:
        raise SystemExit("mitsuba --help did not print the expected help text")
    if "scalar_rgb" not in help_result.stdout or "llvm_ad_rgb" not in help_result.stdout:
        raise SystemExit("mitsuba --help did not list the expected variants")

    if sys.platform.startswith("win"):
        return

    render_variant = "llvm_ad_rgb"
    token = uuid.uuid4().hex
    scene = Path.cwd() / f"mitsuba-smoke-{token}.xml"
    output = Path.cwd() / f"mitsuba-smoke-{token}.exr"
    try:
        scene.write_text(SCENE_XML, encoding="utf-8")
        run_checked(["mitsuba", "-m", render_variant, "-o", str(output), str(scene)])
        if not output.is_file() or output.stat().st_size == 0:
            raise SystemExit("mitsuba CLI did not produce a non-empty render output")
        if output.read_bytes()[:4] != b"\x76\x2f\x31\x01":
            raise SystemExit("mitsuba CLI did not produce an OpenEXR render output")
    finally:
        scene.unlink(missing_ok=True)
        output.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
