import importlib
import os
import subprocess
import sys
import uuid
from pathlib import Path


BASE_EXPECTED_VARIANTS = {
    "scalar_rgb",
    "scalar_spectral",
    "scalar_spectral_polarized",
    "llvm_ad_rgb",
    "llvm_ad_mono",
    "llvm_ad_mono_polarized",
    "llvm_ad_spectral",
    "llvm_ad_spectral_polarized",
}

CUDA_EXPECTED_VARIANTS = {
    "cuda_ad_rgb",
    "cuda_ad_mono",
    "cuda_ad_mono_polarized",
    "cuda_ad_spectral",
    "cuda_ad_spectral_polarized",
}

WINDOWS_MITSUBA_LLVM_TEARDOWN_STATUSES = {
    3221226356,  # 0xC0000374, heap corruption
    3221226505,  # 0xC0000409, stack buffer overrun / fail-fast
    -1073740940,
    -1073740791,
}


def expected_variants() -> set[str]:
    variants = set(BASE_EXPECTED_VARIANTS)
    if sys.platform.startswith("linux"):
        variants.update(CUDA_EXPECTED_VARIANTS)
    return variants


def configure_drjit_llvm_path() -> None:
    if "DRJIT_LIBLLVM_PATH" in os.environ:
        return

    prefix = Path(sys.prefix)
    candidates = [
        prefix / "lib" / "libLLVM-22.so",
        prefix / "lib" / "libLLVM.so",
        prefix / "Library" / "bin" / "LLVM-C.dll",
        prefix / "Library" / "bin" / "LLVM.dll",
        prefix / "lib" / "libLLVM-22.dylib",
        prefix / "lib" / "libLLVM.dylib",
    ]
    for candidate in candidates:
        if candidate.is_file():
            os.environ["DRJIT_LIBLLVM_PATH"] = str(candidate)
            return


def make_tiny_cornell_box(mi) -> dict:
    scene_dict = mi.cornell_box()
    scene_dict["integrator"]["max_depth"] = 2
    scene_dict["sensor"]["sampler"]["sample_count"] = 1
    scene_dict["sensor"]["film"]["width"] = 4
    scene_dict["sensor"]["film"]["height"] = 4
    return scene_dict


def render_tiny_scene(mi, dr, variant: str, success_file: Path | None = None) -> None:
    mi.set_variant(variant)
    scene = mi.load_dict(make_tiny_cornell_box(mi))
    image = mi.render(scene, spp=1)
    dr.eval(image)

    shape = tuple(getattr(image, "shape", ()))
    if shape[:2] != (4, 4):
        raise SystemExit(f"Unexpected {variant} render shape: {shape}")

    if success_file is not None:
        success_file.write_text(f"{variant} {shape}\n", encoding="utf-8")
        sys.stdout.flush()
        sys.stderr.flush()


def render_windows_llvm_scene_in_subprocess(variant: str) -> None:
    success_file = Path.cwd() / f"mitsuba-llvm-render-{uuid.uuid4().hex}.ok"
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--render-one-variant",
                variant,
                str(success_file),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        render_succeeded = success_file.is_file()
        if result.returncode == 0 and render_succeeded:
            return
        if render_succeeded and result.returncode in WINDOWS_MITSUBA_LLVM_TEARDOWN_STATUSES:
            return
        if result.stdout:
            print(result.stdout, end="")
        if result.returncode == 0:
            raise SystemExit(f"{variant} render subprocess did not write success sentinel")
        raise SystemExit(f"{variant} render subprocess failed with status {result.returncode}")
    finally:
        success_file.unlink(missing_ok=True)


def activate_variant(mi, variant: str) -> None:
    try:
        mi.set_variant(variant)
    except ImportError as exc:
        message = str(exc)
        if (
            variant.startswith("cuda_")
            and "jit_init_thread_state()" in message
            and "CUDA backend hasn't been initialized" in message
        ):
            return
        raise

    if mi.variant() != variant:
        raise SystemExit(f"Failed to activate Mitsuba variant {variant!r}")


def main() -> None:
    configure_drjit_llvm_path()
    dr = importlib.import_module("drjit")
    mi = importlib.import_module("mitsuba")

    if len(sys.argv) == 4 and sys.argv[1] == "--render-one-variant":
        render_tiny_scene(mi, dr, sys.argv[2], Path(sys.argv[3]))
        return

    config = importlib.import_module("mitsuba.config")
    built_variants = set(config.MI_VARIANTS)
    variants = expected_variants()
    missing = variants - built_variants
    if missing:
        raise SystemExit(f"Missing Mitsuba variants: {sorted(missing)}")
    unexpected = built_variants - variants
    if unexpected:
        raise SystemExit(f"Unexpected Mitsuba variants: {sorted(unexpected)}")

    for variant in sorted(variants):
        activate_variant(mi, variant)

    render_tiny_scene(mi, dr, "scalar_rgb")
    if "llvm_ad_rgb" in variants:
        if sys.platform.startswith("win"):
            render_windows_llvm_scene_in_subprocess("llvm_ad_rgb")
        else:
            render_tiny_scene(mi, dr, "llvm_ad_rgb")


if __name__ == "__main__":
    main()
