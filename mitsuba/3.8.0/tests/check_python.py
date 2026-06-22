import importlib
import os
import sys
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


def expected_variants() -> set[str]:
    variants = set(BASE_EXPECTED_VARIANTS)
    if sys.platform != "darwin":
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


def render_tiny_scene(mi, dr, variant: str) -> None:
    mi.set_variant(variant)
    scene = mi.load_dict(make_tiny_cornell_box(mi))
    image = mi.render(scene, spp=1)
    dr.eval(image)

    shape = tuple(getattr(image, "shape", ()))
    if shape[:2] != (4, 4):
        raise SystemExit(f"Unexpected {variant} render shape: {shape}")


def main() -> None:
    configure_drjit_llvm_path()
    dr = importlib.import_module("drjit")
    mi = importlib.import_module("mitsuba")

    config = importlib.import_module("mitsuba.config")
    built_variants = set(config.MI_VARIANTS)
    variants = expected_variants()
    missing = variants - built_variants
    if missing:
        raise SystemExit(f"Missing Mitsuba variants: {sorted(missing)}")

    for variant in sorted(variants):
        mi.set_variant(variant)
        if mi.variant() != variant:
            raise SystemExit(f"Failed to activate Mitsuba variant {variant!r}")

    render_tiny_scene(mi, dr, "scalar_rgb")
    if "llvm_ad_rgb" in variants:
        render_tiny_scene(mi, dr, "llvm_ad_rgb")


if __name__ == "__main__":
    main()
