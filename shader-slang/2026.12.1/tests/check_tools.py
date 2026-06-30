from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SHADER_SOURCE = """StructuredBuffer<float> buffer0;
StructuredBuffer<float> buffer1;
RWStructuredBuffer<float> result;

[shader(\"compute\")]
[numthreads(1, 1, 1)]
void computeMain(uint3 threadId : SV_DispatchThreadID)
{
    uint index = threadId.x;
    result[index] = buffer0[index] + buffer1[index];
}
"""


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def require_success(command: list[str]) -> str:
    result = run(command)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise SystemExit(output)
    return output


def main() -> None:
    is_windows = sys.platform.startswith("win")
    prefix = Path(os.environ["LIBRARY_PREFIX"] if is_windows else os.environ["PREFIX"])
    bin_dir = prefix / "bin"
    exe_suffix = ".exe" if is_windows else ""

    slangc = bin_dir / f"slangc{exe_suffix}"
    slangd = bin_dir / f"slangd{exe_suffix}"
    slangi = bin_dir / f"slangi{exe_suffix}"
    slang_dispatcher = bin_dir / f"slang{exe_suffix}"
    for tool in (slangc, slangd, slangi, slang_dispatcher):
        if not tool.is_file():
            raise SystemExit(f"Missing Slang tool: {tool}")

    slangc_version = require_success([str(slangc), "-version"])
    if "2026.12.1" not in slangc_version:
        raise SystemExit(slangc_version)

    slang_version = require_success([str(slang_dispatcher), "version"])
    if "2026.12.1" not in slang_version:
        raise SystemExit(slang_version)

    slangi_help = require_success([str(slangi), "--help"])
    if "Usage:" not in slangi_help:
        raise SystemExit(slangi_help)

    slangd_builtin_module = require_success([str(slangd), "--print-builtin-module", "core"])
    if "__Dynamic" not in slangd_builtin_module:
        raise SystemExit("slangd did not print the builtin core module.")

    with tempfile.TemporaryDirectory(prefix="shader-slang-tools-") as tmpdir:
        tmp = Path(tmpdir)
        shader = tmp / "hello-world.slang"
        shader.write_text(SHADER_SOURCE, encoding="utf-8")

        glsl = tmp / "hello-world.glsl"
        glsl_result = run(
            [
                str(slangc),
                str(shader),
                "-profile",
                "glsl_450",
                "-target",
                "glsl",
                "-o",
                str(glsl),
                "-entry",
                "computeMain",
            ]
        )
        if glsl_result.returncode != 0:
            raise SystemExit(glsl_result.stdout + glsl_result.stderr)
        glsl_text = glsl.read_text(encoding="utf-8")
        if "gl_GlobalInvocationID" not in glsl_text:
            raise SystemExit(glsl_text)
        glslang_validator = shutil.which("glslangValidator")
        if glslang_validator is None:
            raise SystemExit("glslangValidator was not available in the test environment.")
        require_success([glslang_validator, "-S", "comp", str(glsl)])

        spirv = tmp / "hello-world.spv"
        spirv_result = run(
            [
                str(slangc),
                str(shader),
                "-profile",
                "glsl_450",
                "-target",
                "spirv",
                "-o",
                str(spirv),
                "-entry",
                "computeMain",
            ]
        )
        if spirv_result.returncode != 0:
            raise SystemExit(spirv_result.stdout + spirv_result.stderr)
        if spirv.read_bytes()[:4] != b"\x03\x02\x23\x07":
            raise SystemExit("SPIR-V output did not start with the expected magic number.")
        spirv_val = shutil.which("spirv-val")
        if spirv_val is None:
            raise SystemExit("spirv-val was not available in the test environment.")
        require_success([spirv_val, str(spirv)])


if __name__ == "__main__":
    main()
