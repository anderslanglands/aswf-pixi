from __future__ import annotations

import pathlib
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

TIMEOUT_SECONDS = 60
EXPECT_GPU = os.environ.get("PBRT_EXPECT_GPU") == "1"
GPU_LIBRARY_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"^(lib)?cuda(\.so(\..*)?|\.dylib|\.dll)?$",
        r"^(lib)?cudart(_static)?(\.so(\..*)?|\.a|\.dylib|64(_\d+)?\.dll|\.dll)?$",
        r"^(lib)?nvidia-ml(\.so(\..*)?|\.dylib|\.dll)?$",
        r"^nvml\.dll$",
        r"^(lib)?nvtx.*(\.so(\..*)?|\.dylib|\.dll)?$",
        r"^nvtoolsext.*(\.dll|\.lib)?$",
        r"^(lib)?optix.*(\.so(\..*)?|\.dylib|\.dll|\.lib)?$",
    )
)


def run_command(command: list[str], *, cwd: pathlib.Path | None = None, input: str | None = None) -> str:
    completed = subprocess.run(
        command,
        check=False,
        cwd=cwd,
        input=input,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    output = completed.stdout + completed.stderr
    assert completed.returncode == 0, f"{command!r} exited with {completed.returncode}:\n{output}"
    return output


def run_tool(command: list[str], expected: str, *, allowed_returncodes: set[int] = {0}) -> str:
    executable = shutil.which(command[0])
    assert executable, f"{command[0]} was not found on PATH"

    completed = subprocess.run(
        [executable, *command[1:]],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    output = completed.stdout + completed.stderr
    assert completed.returncode in allowed_returncodes, (
        f"{command!r} exited with {completed.returncode}:\n{output}"
    )
    assert expected in output, f"{command!r} output did not contain {expected!r}:\n{output}"
    return output


def pe_import_names(executable: pathlib.Path) -> list[str]:
    data = executable.read_bytes()
    assert data[:2] == b"MZ", f"{executable} is not a PE executable"
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    assert data[pe_offset : pe_offset + 4] == b"PE\0\0", f"{executable} has no PE header"

    coff_offset = pe_offset + 4
    section_count = struct.unpack_from("<H", data, coff_offset + 2)[0]
    optional_size = struct.unpack_from("<H", data, coff_offset + 16)[0]
    optional_offset = coff_offset + 20
    magic = struct.unpack_from("<H", data, optional_offset)[0]
    if magic == 0x10B:
        data_directories_offset = optional_offset + 96
    elif magic == 0x20B:
        data_directories_offset = optional_offset + 112
    else:
        raise AssertionError(f"{executable} has unknown PE optional header magic {magic:#x}")

    import_rva = struct.unpack_from("<I", data, data_directories_offset + 8)[0]
    assert import_rva, f"{executable} has no PE import directory"

    sections = []
    section_offset = optional_offset + optional_size
    for index in range(section_count):
        offset = section_offset + 40 * index
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, offset + 8
        )
        sections.append((virtual_address, max(virtual_size, raw_size), raw_offset))

    def rva_to_offset(rva: int) -> int:
        for virtual_address, size, raw_offset in sections:
            if virtual_address <= rva < virtual_address + size:
                return raw_offset + (rva - virtual_address)
        raise AssertionError(f"could not map PE RVA {rva:#x} in {executable}")

    def read_c_string(offset: int) -> str:
        end = data.index(b"\0", offset)
        return data[offset:end].decode("ascii", errors="replace")

    imports: list[str] = []
    descriptor_offset = rva_to_offset(import_rva)
    while True:
        original_first_thunk, timestamp, forwarder_chain, name_rva, first_thunk = struct.unpack_from(
            "<IIIII", data, descriptor_offset
        )
        if not any((original_first_thunk, timestamp, forwarder_chain, name_rva, first_thunk)):
            break
        imports.append(read_c_string(rva_to_offset(name_rva)))
        descriptor_offset += 20
    return imports


def linkage_report(executable: str) -> str:
    if sys.platform.startswith("linux"):
        linkage_tool = shutil.which("ldd")
        assert linkage_tool, "ldd was not found on PATH"
        return run_command([linkage_tool, executable])
    elif sys.platform == "darwin":
        linkage_tool = shutil.which("otool")
        assert linkage_tool, "otool was not found on PATH"
        return run_command([linkage_tool, "-L", executable])
    elif sys.platform == "win32":
        return "\n".join(pe_import_names(pathlib.Path(executable)))
    return ""


def linked_library_names(report: str) -> list[str]:
    names: list[str] = []
    for line in report.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        token = stripped.split()[0]
        if token == "statically":
            continue
        names.append(pathlib.PurePath(token).name.lower())
    return names


def gpu_linked_libraries(names: list[str]) -> list[str]:
    return [
        name
        for name in names
        if any(pattern.match(name) for pattern in GPU_LIBRARY_PATTERNS)
    ]


def verify_linkage(
    executable: str,
    *,
    requires_openexr: bool = False,
    allow_gpu: bool = False,
    requires_gpu: bool = False,
) -> None:
    output = linkage_report(executable)
    libraries = linked_library_names(output)
    if requires_openexr:
        assert any("openexr" in library for library in libraries), output

    linked_gpu_libraries = gpu_linked_libraries(libraries)
    if requires_gpu:
        assert linked_gpu_libraries, f"{executable} does not appear to link CUDA/OptiX support:\n{output}"
    if not allow_gpu:
        assert not linked_gpu_libraries, (
            f"{executable} links GPU-only libraries in a CPU-only package: "
            f"{linked_gpu_libraries}\n{output}"
        )


def probe_gpu_entrypoint(pbrt: str, scene: pathlib.Path, image: pathlib.Path, tmp_path: pathlib.Path) -> None:
    completed = subprocess.run(
        [pbrt, "--gpu", scene.as_posix()],
        check=False,
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    output = completed.stdout + completed.stderr
    if completed.returncode == 0:
        assert image.is_file(), "pbrt --gpu completed without writing the expected EXR output"
        return

    lower_output = output.lower()
    compiled_out_markers = (
        "compiled without",
        "cuda support is not",
        "cuda support not",
        "gpu support is not",
        "gpu support not",
        "optix support is not",
        "optix support not",
        "not built with",
        "not compiled with",
        "unknown option",
        "unrecognized",
    )
    assert not any(marker in lower_output for marker in compiled_out_markers), output
    driver_path_markers = (
        "cuda error",
        "cuda driver",
        "cuda device",
        "optix error",
        "optix initialization",
        "optix device",
        "no cuda-capable device",
        "no device",
        "driver version",
    )
    assert any(
        marker in lower_output for marker in driver_path_markers
    ), f"pbrt --gpu failed before reaching an identifiable GPU/driver path:\n{output}"


def assert_installed_tool(name: str) -> str:
    executable = shutil.which(name)
    assert executable, f"{name} was not found on PATH"

    prefix = os.environ.get("CONDA_PREFIX") or os.environ.get("PREFIX")
    if prefix:
        executable_path = pathlib.Path(executable).resolve()
        prefix_path = pathlib.Path(prefix).resolve()
        try:
            executable_path.relative_to(prefix_path)
        except ValueError as exc:
            raise AssertionError(
                f"{name} resolved to {executable_path}, outside active prefix {prefix_path}"
            ) from exc

    return executable


def image_rgb_values(imgtool: str, image: pathlib.Path) -> list[tuple[float, float, float]]:
    output = run_command([imgtool, "cat", "--csv", image.as_posix()])
    pixels: list[tuple[float, float, float]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        values = [float(value) for value in line.split(",")]
        assert len(values) >= 3, f"expected at least RGB channels from imgtool cat:\n{output}"
        assert all(math.isfinite(value) for value in values[:3]), output
        pixels.append((values[0], values[1], values[2]))

    assert pixels, f"imgtool cat printed no pixels for {image}:\n{output}"
    return pixels


def smoke_render(tmp_path: pathlib.Path) -> pathlib.Path:
    pbrt = assert_installed_tool("pbrt")
    imgtool = assert_installed_tool("imgtool")
    pspec = assert_installed_tool("pspec")
    plytool = assert_installed_tool("plytool")
    verify_linkage(
        pbrt,
        requires_openexr=True,
        allow_gpu=EXPECT_GPU,
        requires_gpu=EXPECT_GPU,
    )
    for executable in (imgtool, pspec, plytool):
        verify_linkage(executable, requires_openexr=True, allow_gpu=EXPECT_GPU)

    image = tmp_path / "smoke.exr"
    scene = tmp_path / "smoke.pbrt"
    scene_text = "\n".join(
        [
            'Film "rgb" "integer xresolution" [3] "integer yresolution" [3]',
            f'    "string filename" "{image.as_posix()}"',
            'Sampler "independent" "integer pixelsamples" [8]',
            'Integrator "path" "integer maxdepth" [1]',
            "LookAt 0 0 0  0 0 1  0 1 0",
            'Camera "orthographic" "float screenwindow" [-1 1 -1 1]',
            "WorldBegin",
            'AreaLightSource "diffuse" "rgb L" [10 0 0] "bool twosided" [true]',
            'Shape "trianglemesh"',
            '    "point3 P" [-0.9 -0.9 1  0.9 -0.9 1  0 0.9 1]',
            '    "integer indices" [0 1 2]',
        ]
    )
    scene.write_text(scene_text, encoding="utf-8")

    run_command([pbrt, scene.as_posix()], cwd=tmp_path)
    assert image.is_file(), "pbrt did not write the expected EXR output"

    output = run_command([imgtool, "info", image.as_posix()])
    assert "resolution (3, 3)" in output, output

    pixels = image_rgb_values(imgtool, image)
    assert len(pixels) == 9, f"expected 9 pixels from a 3x3 render, got {len(pixels)}: {pixels}"
    pixel_maxima = [max(pixel) for pixel in pixels]
    pixel_abs_maxima = [max(abs(channel) for channel in pixel) for pixel in pixels]
    assert max(pixel_maxima) > 0.5, (
        "rendered image did not contain a bright visible area-light triangle: "
        f"{pixels}"
    )
    assert min(pixel_abs_maxima) < 0.001, (
        "rendered image did not preserve a black background outside the triangle: "
        f"{pixels}"
    )
    assert max(pixel_maxima) - min(pixel_maxima) > 0.5, (
        "rendered image did not contain distinct foreground/background pixel values: "
        f"{pixels}"
    )

    if EXPECT_GPU:
        gpu_image = tmp_path / "smoke-gpu.exr"
        gpu_scene = tmp_path / "smoke-gpu.pbrt"
        gpu_scene.write_text(
            scene_text.replace(image.as_posix(), gpu_image.as_posix()),
            encoding="utf-8",
        )
        probe_gpu_entrypoint(pbrt, gpu_scene, gpu_image, tmp_path)

    return image


def smoke_pspec(tmp_path: pathlib.Path) -> None:
    pspec = assert_installed_tool("pspec")
    imgtool = assert_installed_tool("imgtool")

    outbase = tmp_path / "grid-spectrum"
    run_command(
        [
            pspec,
            "grid",
            "--npoints",
            "4",
            "--nsets",
            "1",
            "--resolution",
            "5",
            "--outbase",
            outbase.as_posix(),
        ],
        cwd=tmp_path,
    )
    image = outbase.with_suffix(".exr")
    text = outbase.with_suffix(".txt")
    assert image.is_file(), "pspec did not write its EXR output"
    assert text.is_file() and text.read_text(encoding="utf-8").strip(), (
        "pspec did not write a non-empty radial-average text output"
    )
    output = run_command([imgtool, "info", image.as_posix()])
    assert "resolution (5, 5)" in output, output


def smoke_plytool(tmp_path: pathlib.Path) -> None:
    plytool = assert_installed_tool("plytool")

    mesh = tmp_path / "triangle.ply"
    mesh.write_text(
        "\n".join(
            [
                "ply",
                "format ascii 1.0",
                "element vertex 3",
                "property float x",
                "property float y",
                "property float z",
                "element face 1",
                "property list uchar int vertex_indices",
                "end_header",
                "0 0 0",
                "1 0 0",
                "0 1 0",
                "3 0 1 2",
            ]
        ),
        encoding="utf-8",
    )
    output = run_command([plytool, "info", mesh.as_posix()])
    assert "Triangles: 1" in output, output
    assert "Vertex positions: 3" in output, output
    output = run_command([plytool, "cat", mesh.as_posix()])
    assert "Triangle: 0 1 2" in output, output


def smoke_cyhair2pbrt(tmp_path: pathlib.Path) -> None:
    cyhair2pbrt = assert_installed_tool("cyhair2pbrt")
    verify_linkage(cyhair2pbrt, allow_gpu=EXPECT_GPU)

    hair = tmp_path / "strand.hair"
    converted = tmp_path / "strand.pbrt"
    header = struct.pack(
        "<4sIIIIff3f88s",
        b"HAIR",
        1,  # strands
        5,  # points in the strand
        0x3,  # segment and point data present, defaults for everything else
        5,  # upstream converter loop consumes this many strand points
        0.01,
        1.0,
        0.5,
        0.5,
        0.5,
        b"pbrt package smoke test".ljust(88, b"\0"),
    )
    segments = struct.pack("<H", 5)
    points = struct.pack(
        "<15f",
        0.0,
        0.0,
        0.0,
        0.25,
        0.0,
        0.0,
        0.5,
        0.0,
        0.0,
        0.75,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
    )
    hair.write_bytes(header + segments + points)

    output = run_command([cyhair2pbrt, hair.as_posix(), converted.as_posix()])
    assert "Converted" in output, output
    converted_text = converted.read_text(encoding="utf-8")
    curve_records = re.findall(
        r'Shape "curve".*?"point3 P" \[ ([^\]]+) \].*?"float width0"',
        converted_text,
    )
    assert len(curve_records) == 3, converted_text
    assert converted_text.count('"float width1"') == len(curve_records), converted_text
    for record in curve_records:
        values = [float(value) for value in record.split()]
        assert len(values) == 12, converted_text
        assert all(math.isfinite(value) for value in values), converted_text


def main() -> None:
    pbrt_help = run_tool(["pbrt", "--help"], "usage: pbrt")
    if EXPECT_GPU:
        assert "--gpu" in pbrt_help, "pbrt-optix help output does not expose --gpu"
    else:
        assert "--gpu" not in pbrt_help, "CPU-only pbrt help output unexpectedly exposes --gpu"
    run_tool(["imgtool", "help"], "imgtool <command>")
    run_tool(["pspec", "--help"], "usage: pspec")
    run_tool(["plytool", "help"], "usage: plytool")
    run_tool(["cyhair2pbrt", "--help"], "usage: cyhair2pbrt", allowed_returncodes={0, 1})

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        smoke_render(tmp_path)
        smoke_pspec(tmp_path)
        smoke_plytool(tmp_path)
        smoke_cyhair2pbrt(tmp_path)


if __name__ == "__main__":
    main()
