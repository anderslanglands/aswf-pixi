import importlib
import os
import sys
from pathlib import Path

import drjit as dr
import mitsuba as mi


EXPECTED_VARIANTS = {
    "scalar_rgb",
    "scalar_spectral",
    "scalar_spectral_polarized",
    "llvm_ad_rgb",
    "llvm_ad_mono",
    "llvm_ad_mono_polarized",
    "llvm_ad_spectral",
    "llvm_ad_spectral_polarized",
    "cuda_ad_rgb",
    "cuda_ad_mono",
    "cuda_ad_mono_polarized",
    "cuda_ad_spectral",
    "cuda_ad_spectral_polarized",
}


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


def make_tiny_cornell_box() -> dict:
    scene_dict = mi.cornell_box()
    scene_dict["integrator"]["max_depth"] = 2
    scene_dict["sensor"]["sampler"]["sample_count"] = 1
    scene_dict["sensor"]["film"]["width"] = 4
    scene_dict["sensor"]["film"]["height"] = 4
    return scene_dict


def main() -> None:
    configure_drjit_llvm_path()

    config = importlib.import_module("mitsuba.config")
    built_variants = set(config.MI_VARIANTS)
    missing = EXPECTED_VARIANTS - built_variants
    if missing:
        raise SystemExit(f"Missing Mitsuba variants: {sorted(missing)}")

    for variant in sorted(EXPECTED_VARIANTS):
        mi.set_variant(variant)
        if mi.variant() != variant:
            raise SystemExit(f"Failed to activate Mitsuba variant {variant!r}")

    mi.set_variant("scalar_rgb")
    scene = mi.load_dict(make_tiny_cornell_box())
    image = mi.render(scene, spp=1)
    dr.eval(image)

    shape = tuple(getattr(image, "shape", ()))
    if shape[:2] != (4, 4):
        raise SystemExit(f"Unexpected scalar_rgb render shape: {shape}")


if __name__ == "__main__":
    main()
