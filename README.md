# Using the Channel with Pixi

Use the conda channel URL:

```toml
[workspace]
channels = [
  "https://conda.anaconda.org/anderslanglands",
  "conda-forge",
]
platforms = ["linux-64", "win-64", "osx-arm64"]

[dependencies]
materialx = ">=1.39.4,<1.40"
```

If you are configuring Pixi in `pyproject.toml`, use the same channel values under
`[tool.pixi.workspace]` and dependencies under `[tool.pixi.dependencies]`.

For packages published only to the test label, put the test-label channel first:

```toml
[workspace]
channels = [
  "https://conda.anaconda.org/anderslanglands/label/test",
  "https://conda.anaconda.org/anderslanglands",
  "conda-forge",
]
platforms = ["linux-64", "win-64", "osx-arm64"]
```

# Upstream Release Automation

The `Check upstream releases` workflow runs nightly and can also be started manually. It checks the upstream GitHub releases for the package recipe directories in this repo, copies the semantically closest existing version recipe when a newer numbered release is found, updates the version/tag/source hash, and opens or refreshes one PR per created package/version recipe from `automation/upstream-release-prs/<package>/<version>`.

By default, each generated recipe PR dispatches the existing package build workflow for only that recipe selector with `publish_target = test-label` and smoke tests enabled. When that exact branch/head SHA succeeds for a smoke-tested test-label run, the `Merge upstream release PR` workflow merges the matching PR to `main`. That merge triggers the `Promote upstream releases` workflow, which creates a promotion ref at the merge commit and dispatches the existing package build workflow from that ref with `publish_target = default-label`, so production uploads still pass through the `anaconda-production` environment gate. Automatic PR creation uses `UPSTREAM_RELEASE_PR_TOKEN` when configured, otherwise `GITHUB_TOKEN`; build dispatch and auto-merge require `UPSTREAM_RELEASE_PR_TOKEN` in GitHub Actions so the dispatched build and merged PR can trigger downstream workflows. If repository settings block GitHub Actions from creating PRs, the workflow leaves each branch in place, reports a manual PR URL, and still dispatches the test-label build when the token is available.

The `UPSTREAM_RELEASE_PR_TOKEN` secret should be a fine-grained token limited to this repository with Contents read/write, Pull requests read/write, and Actions read/write permissions.

Generated upstream-release PRs update package version lists as one README bullet per recipe version. `README.md` uses Git's union merge driver so concurrent generated PRs that add different version bullets are unlikely to conflict; the updater rewrites the targeted package block from the actual recipe directories, which keeps repeated runs idempotent and normalizes duplicate or out-of-order bullets.

If a generated upstream release PR fails, commit the fix to that PR branch and rerun the test-label workflow against the same branch and recipe selector:

```bash
gh workflow run build-packages.yml \
  --ref automation/upstream-release-prs/<package>/<version> \
  -f recipes="<package>/<version>" \
  -f platforms="default" \
  -f publish_target="test-label" \
  -f build_number="" \
  -f run_smoke_tests="true"
```

# Packages

## FLIP Evaluator

Recipe versions:
- `1.7`

FLIP Evaluator provides the FLIP image difference metric as a Python extension and command-line tool.

- `flip-evaluator`: Python extension module and `flip` command-line tool, built for Python 3.10 through 3.14.

## GoldenEye

Recipe versions:
- `0.1.0`
- `0.2.0`
- `0.3.0`
- `0.4.0`

GoldenEye is a pytest-based runner for USD render regression suites, with image comparison and HTML report viewing.

- `goldeneye`: Python command-line tool and pytest plugin, built for Python 3.10 through 3.14. It depends on `flip-evaluator ==1.7` and `openusd-typhoon` so the default Typhoon renderer works out of the box. Until `openusd-typhoon` is promoted, consumers should keep the test label available after the main Anders channel.

## Imath

Recipe versions:
- `3.2.2`

Imath is a C++ math library for 2D and 3D graphics.

- `imath-lib`: Shared Imath runtime libraries only.
- `imath-dev`: C++ headers, CMake package files, pkg-config metadata, and Windows import libraries. Depends on the matching `imath-lib`.
- `imath`: Default metapackage for C++ consumers. Depends on the matching `imath-lib` and `imath-dev`.

## OpenEXR

Recipe versions:
- `3.4.12`
- `3.4.13`

OpenEXR provides high dynamic-range image file format libraries and tools.

- `openexr-core-lib`: C OpenEXRCore runtime library plus runtime dependencies on Imath, libdeflate, zlib, and OpenJPH.
- `openexr-core-dev`: C OpenEXRCore headers, CMake package files, and Windows import libraries. Depends on the matching `openexr-core-lib` and Imath development package.
- `openexr-lib`: C++ OpenEXR runtime libraries, including OpenEXR, OpenEXRUtil, Iex, and IlmThread. Depends on the matching `openexr-core-lib`.
- `openexr-dev`: C++ OpenEXR headers, CMake package files, pkg-config metadata, and Windows import libraries. Depends on the matching `openexr-core-dev` and `openexr-lib`.
- `openexr-tools`: Command-line tools such as `exrinfo`, `exrheader`, and `exrmakepreview`. Depends on the matching `openexr-lib`.
- `openexr-python`: Python bindings for OpenEXR, built per Python version, with NumPy support. Depends on the matching `openexr-lib`.
- `openexr`: Default metapackage for C++ tool consumers. Depends on the matching `openexr-lib`, `openexr-dev`, and `openexr-tools`.

## OpenColorIO

Recipe versions:
- `2.5.1`
- `2.5.2`

OpenColorIO is a color management solution for motion picture production.

- `opencolorio-lib`: Shared OpenColorIO runtime library and setup script. Depends on Imath, expat, minizip, pystring, yaml-cpp, and zlib runtime libraries.
- `opencolorio-dev`: C++ headers, CMake package files, pkg-config metadata, and Windows import libraries. Depends on the matching `opencolorio-lib`.
- `opencolorio-tools`: Command-line tools built with `OCIO_USE_OIIO_FOR_APPS=OFF`, so image tools use OpenEXR rather than OpenImageIO. Depends on the matching `opencolorio-lib`, Little CMS, and OpenEXR runtime libraries; `ociodisplay` also requires the platform OpenGL/GLEW/GLUT stack at build time.
- `opencolorio-python`: Python bindings for OpenColorIO, built for Python 3.10 through 3.14. Depends on the matching `opencolorio-lib`.
- `opencolorio`: Default metapackage for C++ consumers. Depends on the matching `opencolorio-lib` and `opencolorio-dev`.

## OpenVDB and NanoVDB

Recipe versions:
- `13.0.0`

OpenVDB provides sparse volumetric data structures, file I/O, and tools. NanoVDB provides compact mostly read-only VDB grids for GPU-friendly and header-only workflows.

- `openvdb-lib`: Shared OpenVDB runtime library. Depends on Boost, Blosc, TBB, and zlib runtime libraries.
- `openvdb-dev`: C++ headers and CMake package files. Depends on the matching `openvdb-lib`.
- `openvdb-tools`: Core command-line tools, currently `vdb_print` and `vdb_lod`. Depends on the matching `openvdb-lib`.
- `openvdb-guitools`: GUI/render tools, currently `vdb_view` and `vdb_render`, with PNG and OpenEXR output support enabled for `vdb_render`. Depends on the matching `openvdb-lib`.
- `openvdb-python`: Python bindings for OpenVDB, built for Python 3.11 through 3.14. Depends on the matching `openvdb-lib`.
- `openvdb`: Default metapackage for C++ consumers. Depends on the matching `openvdb-lib`, `openvdb-dev`, and `openvdb-tools`; Python bindings, GUI/render tools, and NanoVDB are opt-in.
- `nanovdb-dev`: Standalone NanoVDB headers. Does not depend on OpenVDB.
- `nanovdb-tools`: Standalone NanoVDB command-line tools, currently `nanovdb_print` and `nanovdb_validate`. Does not depend on OpenVDB.
- `nanovdb-openvdb-tools`: NanoVDB/OpenVDB bridge tool, currently `nanovdb_convert`. Depends on the matching `openvdb-lib`.
- `nanovdb`: Default metapackage for standalone NanoVDB consumers. Depends on the matching `nanovdb-dev` and `nanovdb-tools`; OpenVDB conversion is opt-in.

## MaterialX

Recipe versions:
- `1.39.4`
- `1.39.5`

MaterialX is an open standard for transferring rich material and look-development content.

- `materialx-lib`: Shared MaterialX runtime libraries plus installed MaterialX libraries and resources. Includes the GLSL, MSL, OSL, and MDL generator libraries; 1.39.5 also includes Slang generator libraries. Render modules remain opt-in.
- `materialx-dev`: C++ headers, CMake package files, and Windows import libraries for the base and generator targets. Depends on the matching `materialx-lib`.
- `materialx-render`: Core render library plus platform render backends such as GLSL/OpenGL, hardware helpers, macOS MSL/Metal when available, render resources, headers, and supplemental CMake targets. Depends on the matching `materialx-dev` and Linux OpenGL/X11 development packages.
- `materialx-render-osl`: OSL render backend. For 1.39.5 this also includes generated OSO support files and `MaterialXGenOsl_LibsToOso`. Depends on `materialx-render`, OpenShadingLanguage, and OpenImageIO.
- `materialx-render-mdl`: MDL convenience package for consumers that want MaterialX MDL generation together with the MDL SDK toolchain. Upstream MaterialX 1.39.x does not install a `MaterialXRenderMdl` library.
- `materialx-render-slang`: Slang render backend, available for 1.39.5 and newer recipe versions that include upstream Slang renderer sources; 1.39.4 does not provide this package. Depends on `materialx-render` and `shader-slang-dev 2026.11`; the recipe fetches the matching `shader-slang/slang-rhi` source at the pinned Slang submodule revision, packages the public RHI headers, and consumes the `slang` CMake package exported by `shader-slang-dev`.
- `materialx-guitools`: MaterialX viewer and graph editor executables. Depends on `materialx-render`; the recipe uses a git checkout with submodules because the release tarball does not include the GUI submodule payloads.
- `materialx-python`: Python bindings for MaterialX, built for Python 3.10 through 3.14. Depends on the matching `materialx-lib`. Generator Python modules are included; render Python modules and upstream helper scripts that require disabled render modules are not included.
- `materialx`: Default metapackage for complete base consumers. Depends on the matching `materialx-lib`, `materialx-dev`, and compatible `materialx-python`; render, renderer-specific dependencies, and GUI tools are opt-in.

## libuhdr

Recipe versions:
- `1.4.0`

libuhdr is Google's reference codec for the JPEG/R gain map based Ultra HDR image format.

- `libuhdr-lib`: Shared libuhdr runtime library. Depends on libjpeg-turbo.
- `libuhdr-dev`: Public `ultrahdr_api.h` header, pkg-config metadata, and Windows import library. Depends on the matching `libuhdr-lib`.
- `libuhdr`: Default metapackage for C++ consumers. Depends on the matching `libuhdr-lib` and `libuhdr-dev`.

## Ptex

Recipe versions:
- `2.5.1`
- `2.5.2`

Ptex is Walt Disney Animation Studios' per-face texture mapping system for production rendering.

- `ptex-lib`: Shared Ptex runtime library. Depends on libdeflate.
- `ptex-dev`: Public headers, CMake package files, pkg-config metadata, and Windows import library. Depends on the matching `ptex-lib`; also carries zlib as a development dependency because upstream's installed CMake config still calls `find_package(ZLIB)`.
- `ptex-tools`: Command-line utility package, currently `ptxinfo`. Depends on the matching `ptex-lib`.
- `ptex`: Default metapackage for C++ and tool consumers. Depends on the matching `ptex-lib`, `ptex-dev`, and `ptex-tools`.

## Partio

Recipe versions:
- `1.20.0`

Partio is Walt Disney Animation Studios' particle file I/O and manipulation library.

- `partio-lib`: Shared Partio runtime library with zlib support.
- `partio-dev`: Public headers and recipe-side CMake package metadata exporting `Partio::partio` plus lowercase `partio` config-mode aliases and the `partio::partio` compatibility target. Depends on the matching `partio-lib`.
- `partio-tools`: Headless command-line tools, currently `partattr`, `partconvert`, and `partinfo`. Depends on the matching `partio-lib`.
- `partio-python`: SWIG Python bindings for Partio, built for Python 3.10 through 3.14. Depends on the matching `partio-lib`.
- `partio`: Default metapackage for C++ and headless tool consumers. Depends on the matching `partio-lib`, `partio-dev`, and `partio-tools`; Python bindings and GUI tools are opt-in or omitted for now.

## OpenQMC

Recipe versions:
- `0.7.1`

OpenQMC provides Quasi-Monte Carlo sampling APIs for rendering and graphics applications.

- `openqmc-lib`: Shared OpenQMC runtime library for the binary table build.
- `openqmc-dev`: Headers, installed table include fragments, CMake package files, and Windows import library for the binary table build. Depends on the matching `openqmc-lib` and conflicts with `openqmc-header-only`.
- `openqmc-header-only`: Header-only CMake package exporting `OpenQMC::OpenQMC` without `OQMC_ENABLE_BINARY` or a shared runtime library. Conflicts with `openqmc-dev`.
- `openqmc`: Default metapackage matching the old pixi-recipes behavior. Depends on the matching `openqmc-lib` and `openqmc-dev`; use `openqmc-header-only` to opt into the interface-library flavor.

## OpenSubdiv

Recipe versions:
- `3.7.0`

OpenSubdiv provides subdivision surface evaluation libraries for CPU and GPU workflows.

- `opensubdiv-lib`: CPU-only implementation library. On Linux and macOS this carries the shared `osdCPU` runtime library; on Windows upstream 3.7.0 installs a static `osdCPU.lib` rather than a DLL.
- `opensubdiv-dev`: CPU-only headers, CMake package files, and Unix static archives. Depends on the matching `opensubdiv-lib` and conflicts with the GPU and CUDA development flavors.
- `opensubdiv`: Default CPU-only metapackage for C++ consumers. Depends on the matching `opensubdiv-lib` and `opensubdiv-dev`.
- `opensubdiv-gpu-lib`: Non-CUDA graphics API GPU implementation libraries, carrying both `osdCPU` and `osdGPU`. Linux and Windows builds enable OpenGL, GLEW, GLFW, and TBB with CUDA and Metal disabled; macOS builds enable Metal, OpenGL, GLEW, GLFW, and TBB with CUDA disabled. Windows packages may carry static `osdCPU.lib`/`osdGPU.lib` rather than DLLs.
- `opensubdiv-gpu-dev`: Non-CUDA GPU headers and CMake package files. Depends on the matching `opensubdiv-gpu-lib` and conflicts with the CPU and CUDA development flavors.
- `opensubdiv-gpu`: Non-CUDA GPU compatibility/default metapackage. Depends on the matching `opensubdiv-gpu-lib` and `opensubdiv-gpu-dev`, and conflicts with `opensubdiv` and `opensubdiv-cuda`.
- `opensubdiv-cuda-lib`: CUDA-enabled implementation libraries, carrying both `osdCPU` and `osdGPU`. Linux and Windows builds use the CUDA 12.9 package line and enable CUDA, OpenGL, GLEW, GLFW, and TBB; macOS CUDA outputs are not built.
- `opensubdiv-cuda-dev`: CUDA-enabled headers and CMake package files. Depends on the matching `opensubdiv-cuda-lib` and conflicts with the CPU and non-CUDA GPU development flavors.
- `opensubdiv-cuda`: CUDA-enabled compatibility/default metapackage. Depends on the matching `opensubdiv-cuda-lib` and `opensubdiv-cuda-dev`, and conflicts with `opensubdiv` and `opensubdiv-gpu`.

## SeExpr

Recipe versions:
- `3.0.1`

SeExpr is an embeddable expression evaluation engine for graphics applications.

- `seexpr-lib`: Core SeExpr2 runtime library. On Windows, upstream 3.0.1 builds a static library rather than a DLL.
- `seexpr-dev`: C++ headers and CMake package files. Depends on the matching `seexpr-lib`.
- `seexpr-tools`: Non-GUI command-line utilities, currently upstream's `eval` and `listVar` tools under `share/SeExpr2/utils`. Depends on the matching `seexpr-lib`.
- `seexpr`: Default metapackage for C++ consumers. Depends on the matching `seexpr-lib` and `seexpr-dev`; tools, Python bindings, Qt editor/UI, LLVM backend, docs, and demos are not included by default.

## Shader Slang

Recipe versions:
- `2026.11`
- `2026.12`
- `2026.12.1`
- `2026.12.2`
- `2026.13`

Shader Slang is a shading language and compiler for real-time graphics, with code generation for APIs such as Vulkan, Direct3D, Metal, CUDA, and CPU-oriented workflows.

- `shader-slang-lib`: Shared Slang runtime/compiler libraries, runtime-loaded Slang modules, and installed standard modules. Uses conda-forge `glslang` for SPIR-V output; DXIL/DXC and slang-LLVM support are disabled in this first source-built package.
- `shader-slang-dev`: C++ headers, CMake package files, pkg-config metadata on Unix, and Windows import libraries. Depends on the matching `shader-slang-lib` and `shader-slang-tools` because upstream's installed CMake target set exports `slangc`.
- `shader-slang-tools`: Headless command-line tools: `slang`, `slangc`, `slangd`, and `slangi`. Depends on the matching `shader-slang-lib`.
- `shader-slang`: Default metapackage for compiler and C++ consumers. Depends on the matching runtime, development surface, and tools.

## OpenImageIO

Recipe versions:
- `2.5.19.1`
- `3.0.19.1`
- `3.0.20.0`
- `3.1.14.0`
- `3.1.14.1`
- `3.1.15.0`

OpenImageIO provides image file I/O libraries, command-line tools, texture utilities, and optional format plugins.

- `openimageio-lib`: Shared OpenImageIO and OpenImageIO_Util runtime libraries with common formats embedded, including OpenEXR, TIFF, JPEG, PNG/ICO, BMP, DPX, HDR, PNM, PSD, SGI, TGA, Cineon, DDS, FITS, IFF, RLA, Softimage, Zfile, null, and terminal output. JPEG support is built with libuhdr for 3.0.19.1 and 3.1.14.0; 2.5.19.1 predates that upstream integration.
- `openimageio-dev`: C++ headers, CMake package files, pkg-config metadata, and Windows import libraries. Depends on the matching `openimageio-lib`.
- `openimageio-tools`: Headless command-line tools: `oiiotool`, `maketx`, `iconvert`, `idiff`, `igrep`, and `iinfo`. Depends on the matching `openimageio-lib`.
- `openimageio-python`: Python bindings for OpenImageIO, built for Python 3.10 through 3.14. Depends on the matching `openimageio-lib`.
- `openimageio-format-gif`: GIF format plugin.
- `openimageio-format-webp`: WebP format plugin.
- `openimageio-format-jpeg2000`: JPEG 2000 format plugin with OpenJPEG and OpenJPH support.
- `openimageio-format-jpegxl`: JPEG XL format plugin for 3.0.19.1 and 3.1.14.0. Upstream 2.5.19.1 does not provide this plugin.
- `openimageio-format-heif`: HEIF/HEIC/AVIF format plugin.
- `openimageio-format-raw`: LibRaw camera RAW input plugin.
- `openimageio-format-dicom`: DICOM input plugin.
- `openimageio-format-ffmpeg`: FFmpeg movie input plugin.
- `openimageio-format-openvdb`: OpenVDB input plugin. Depends on the matching OpenVDB runtime package.
- `openimageio`: Default metapackage for C++ and tool consumers. Depends on the matching `openimageio-lib`, `openimageio-dev`, and `openimageio-tools`; Python bindings and extra format plugins are opt-in.

## OpenUSD

Recipe versions:
- `26.05`

OpenUSD provides Pixar Universal Scene Description libraries, schemas, tools, Python modules, and imaging integrations.

Python-enabled OpenUSD packages constrain Python 3.14 to the normal `cp314` ABI rather than conda-forge's free-threaded `cp314t` variant.

- `openusd-minimal-lib`: Minimal non-Python runtime libraries and plugin resources. Depends only on MaterialX, OpenSubdiv, and TBB runtime packages.
- `openusd-minimal-dev`: Minimal non-Python headers, CMake package files, and Windows import libraries. Depends on the matching `openusd-minimal-lib` plus MaterialX/OpenSubdiv/TBB development packages.
- `openusd-minimal-tools`: Minimal non-Python command-line tools such as `usdcat`. Depends on the matching `openusd-minimal-lib`.
- `openusd-minimal-python`: Minimal Python-enabled OpenUSD package containing runtime libraries, development files, tools, and `pxr` Python modules in one package. It uses only MaterialX, OpenSubdiv, TBB, and Python/Jinja dependencies and is mutually exclusive with the non-Python minimal split packages.
- `openusd`: Full Python-enabled OpenUSD package containing runtime libraries, development files, tools, `pxr` Python modules, USD imaging, `usdview`, GUI dependencies, MaterialX render support, and supported plugins. It is mutually exclusive with all `openusd-minimal-*` packages.

## OpenUSD Typhoon

Recipe versions:
- `26.05.8.4bdd4b656`

OpenUSD Typhoon packages the NVIDIA Omniverse `typhoon-anders` branch at commit `4bdd4b656` as a test-label-only preview package. The Typhoon version format is `26.05.<recipe-build-serial>.<short-commit>`, where the serial starts at `1` and increments for each new Typhoon package definition; the current version is `26.05.8.4bdd4b656`. Rattler normalizes `+` and `-` separators in versions to `.`, so the version uses dot separators. Typhoon builds use channels ordered as test label, Anders, then conda-forge with channel priority disabled so dependencies can fall back across labels.

OpenUSD Typhoon uses the same Python 3.14 normal `cp314` ABI constraint as OpenUSD, rather than allowing conda-forge's free-threaded `cp314t` variant.

- `openusd-typhoon`: Full Python-enabled OpenUSD package derived from the latest full `openusd` package recipe. It contains runtime libraries, development files, tools, `pxr` Python modules, USD imaging, `usdview`, GUI dependencies, MaterialX render support, OpenQMC-backed hdEmbree support, and supported plugins. It is mutually exclusive with `openusd` and all `openusd-minimal-*` packages. Recipe metadata restricts publishing to `test-label`.

## OpenShadingLanguage

Recipe versions:
- `1.15.5.0`

OpenShadingLanguage provides a production shading language, compiler, runtime libraries, and OpenImageIO integration.

- `openshadinglanguage-lib`: Shared OSL runtime libraries for CPU rendering. Depends on OpenImageIO, Imath, Partio, pugixml, libxml2, zlib, zstd, and LLVM/Clang runtime libraries.
- `openshadinglanguage-dev`: C++ headers, CMake package files, pkg-config metadata, and Windows import libraries. Depends on the matching `openshadinglanguage-lib` and `openshadinglanguage-tools` because upstream exports `oslc` and `oslinfo` in its CMake target set.
- `openshadinglanguage-tools`: Headless command-line tools, currently `oslc` and `oslinfo`, plus installed standard shader headers.
- `openshadinglanguage-guitools`: Qt-dependent GUI tools, currently `osltoy`. Depends on the matching `openshadinglanguage-lib` and Qt 6.
- `openshadinglanguage-python`: Python `oslquery` bindings, built for Python 3.10 through 3.14. Depends on the matching `openshadinglanguage-lib` and `openimageio-python`.
- `openimageio-format-osl`: OpenImageIO input plugin for procedural OSL images (`.osl`, `.oso`, `.oslgroup`, and `.oslbody`). Depends on the matching OSL runtime and OpenImageIO runtime.
- `openshadinglanguage`: Default metapackage for C++ and headless tool consumers. Depends on the matching `openshadinglanguage-lib`, `openshadinglanguage-dev`, and `openshadinglanguage-tools`; Python bindings, GUI tools, and OIIO plugin are opt-in.
- `openshadinglanguage-cuda-*` and `openimageio-format-osl-cuda`: Linux-only CUDA-enabled flavor built with `osl_gpu=cuda`. These packages install the same upstream CMake target names as the CPU flavor and are mutually exclusive with the CPU packages. They are intended for explicit local/private builds rather than the default publish path.

## MDL SDK

Recipe versions:
- `2026.0.0`

The NVIDIA Material Definition Language SDK provides the MDL compiler, runtime SDK APIs, image plugins, command-line tools, and Python bindings.

- `mdl-sdk-lib`: Runtime loadable modules for both the full SDK (`libmdl_sdk`) and lower-level Core API (`libmdl_core`). PTX/CUDA code generation is part of this normal runtime API surface and does not use a separate CUDA library flavor.
- `mdl-sdk-dev`: Public C++ headers and upstream CMake package files. Depends on the matching runtime, tools, and standard plugin packages because upstream exports all of those targets in one CMake target set.
- `mdl-sdk-tools`: Headless command-line tools: `mdlc`, `mdlm`, `mdltlc`, `i18n`, and `mdl_distiller_cli`.
- `mdl-sdk-plugin-dds`: DDS image plugin.
- `mdl-sdk-plugin-openimageio`: OpenImageIO image plugin. Depends on the matching MDL SDK runtime and OpenImageIO runtime.
- `mdl-sdk-plugin-distiller`: MDL distiller plugin.
- `mdl-sdk-python`: Python bindings (`pymdlsdk` and `pymdl`), built for Python 3.10 through 3.14. Depends on the matching runtime and standard plugins.
- `mdl-sdk`: Default metapackage for C++ and headless tool consumers. Depends on the matching runtime, development surface, tools, and standard plugins; Python bindings are opt-in.

## OptiX SDK

Recipe versions:
- `9.1.0`

The OptiX SDK recipe is a download stub around NVIDIA's public `optix-dev` header repository. The conda artifact does not redistribute NVIDIA headers; activation downloads the pinned GitHub archive into the active environment.

- `optix-dev`: Linux and Windows development stub package installing activation hooks and minimal `OptiXConfig.cmake`. On activation it downloads `NVIDIA/optix-dev` tag `v9.1.0`, verifies the archive checksum, and installs the headers under `$CONDA_PREFIX/opt/optix-dev-9.1.0` on Unix or `$CONDA_PREFIX/Library/opt/optix-dev-9.1.0` on Windows.

## pbrt

Recipe versions:
- `4.0.0`

pbrt is the physically based rendering system described by the PBRT book.

- `pbrt`: CPU-only command-line application package installing `pbrt`, `imgtool`, `pspec`, `plytool`, and `cyhair2pbrt`.
- `pbrt-optix`: Linux and Windows CUDA/OptiX application package built with `optix-dev 9.1.*`, CUDA 13.2, `cuda-nvcc`, and a fixed `PBRT_GPU_SHADER_MODEL=sm_75` so package builds do not require probing a local GPU. It installs the same command names as `pbrt` and is mutually exclusive with the CPU-only package.
