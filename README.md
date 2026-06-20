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

By default, each generated recipe PR dispatches the existing package build workflow for only that recipe selector with `publish_target = test-label` and smoke tests enabled. When that exact branch/head SHA succeeds for a smoke-tested test-label run, the `Merge upstream release PR` workflow merges the matching PR to `main`. That merge triggers the `Promote upstream releases` workflow, which creates a promotion ref at the merge commit and dispatches the existing package build workflow from that ref with `publish_target = default-label`, so production uploads still pass through the `anaconda-production` environment gate. Automatic PR creation uses `UPSTREAM_RELEASE_PR_TOKEN` when configured, otherwise `GITHUB_TOKEN`; if repository settings block GitHub Actions from creating PRs, the workflow leaves each branch in place, reports a manual PR URL, and still dispatches the test-label build.

# Packages

## Imath

Recipe versions: `3.2.2`

Imath is a C++ math library for 2D and 3D graphics.

- `imath-lib`: Shared Imath runtime libraries only.
- `imath-dev`: C++ headers, CMake package files, pkg-config metadata, and Windows import libraries. Depends on the matching `imath-lib`.
- `imath`: Default metapackage for C++ consumers. Depends on the matching `imath-lib` and `imath-dev`.

## OpenEXR

Recipe versions: `3.4.12`

OpenEXR provides high dynamic-range image file format libraries and tools.

- `openexr-core-lib`: C OpenEXRCore runtime library plus runtime dependencies on Imath, libdeflate, zlib, and OpenJPH.
- `openexr-core-dev`: C OpenEXRCore headers, CMake package files, and Windows import libraries. Depends on the matching `openexr-core-lib` and Imath development package.
- `openexr-lib`: C++ OpenEXR runtime libraries, including OpenEXR, OpenEXRUtil, Iex, and IlmThread. Depends on the matching `openexr-core-lib`.
- `openexr-dev`: C++ OpenEXR headers, CMake package files, pkg-config metadata, and Windows import libraries. Depends on the matching `openexr-core-dev` and `openexr-lib`.
- `openexr-tools`: Command-line tools such as `exrinfo`, `exrheader`, and `exrmakepreview`. Depends on the matching `openexr-lib`.
- `openexr-python`: Python bindings for OpenEXR, built per Python version, with NumPy support. Depends on the matching `openexr-lib`.
- `openexr`: Default metapackage for C++ tool consumers. Depends on the matching `openexr-lib`, `openexr-dev`, and `openexr-tools`.

## OpenColorIO

Recipe versions: `2.5.1`

OpenColorIO is a color management solution for motion picture production.

- `opencolorio-lib`: Shared OpenColorIO runtime library and setup script. Depends on Imath, expat, minizip, pystring, yaml-cpp, and zlib runtime libraries.
- `opencolorio-dev`: C++ headers, CMake package files, pkg-config metadata, and Windows import libraries. Depends on the matching `opencolorio-lib`.
- `opencolorio-tools`: Command-line tools built with `OCIO_USE_OIIO_FOR_APPS=OFF`, so image tools use OpenEXR rather than OpenImageIO. Depends on the matching `opencolorio-lib`, Little CMS, and OpenEXR runtime libraries; `ociodisplay` also requires the platform OpenGL/GLEW/GLUT stack at build time.
- `opencolorio-python`: Python bindings for OpenColorIO, built for Python 3.10 through 3.14. Depends on the matching `opencolorio-lib`.
- `opencolorio`: Default metapackage for C++ consumers. Depends on the matching `opencolorio-lib` and `opencolorio-dev`.

## OpenVDB and NanoVDB

Recipe versions: `13.0.0`

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

Recipe versions: `1.39.4`

MaterialX is an open standard for transferring rich material and look-development content.

- `materialx-lib`: Shared MaterialX runtime libraries plus installed MaterialX libraries and resources. Render modules are currently disabled.
- `materialx-dev`: C++ headers, CMake package files, and Windows import libraries. Depends on the matching `materialx-lib`.
- `materialx-python`: Python bindings for MaterialX, built for Python 3.10 through 3.14. Depends on the matching `materialx-lib`. Render Python modules and upstream helper scripts that require disabled render modules are not included.
- `materialx`: Default metapackage for complete consumers. Depends on the matching `materialx-lib`, `materialx-dev`, and compatible `materialx-python`.

## libuhdr

Recipe versions: `1.4.0`

libuhdr is Google's reference codec for the JPEG/R gain map based Ultra HDR image format.

- `libuhdr-lib`: Shared libuhdr runtime library. Depends on libjpeg-turbo.
- `libuhdr-dev`: Public `ultrahdr_api.h` header, pkg-config metadata, and Windows import library. Depends on the matching `libuhdr-lib`.
- `libuhdr`: Default metapackage for C++ consumers. Depends on the matching `libuhdr-lib` and `libuhdr-dev`.

## Ptex

Recipe versions: `2.5.1`

Ptex is Walt Disney Animation Studios' per-face texture mapping system for production rendering.

- `ptex-lib`: Shared Ptex runtime library. Depends on libdeflate.
- `ptex-dev`: Public headers, CMake package files, pkg-config metadata, and Windows import library. Depends on the matching `ptex-lib`; also carries zlib as a development dependency because upstream's installed CMake config still calls `find_package(ZLIB)`.
- `ptex-tools`: Command-line utility package, currently `ptxinfo`. Depends on the matching `ptex-lib`.
- `ptex`: Default metapackage for C++ and tool consumers. Depends on the matching `ptex-lib`, `ptex-dev`, and `ptex-tools`.

## Partio

Recipe versions: `1.20.0`

Partio is Walt Disney Animation Studios' particle file I/O and manipulation library.

- `partio-lib`: Shared Partio runtime library with zlib support.
- `partio-dev`: Public headers and recipe-side CMake package metadata exporting `Partio::partio` plus lowercase `partio` config-mode aliases and the `partio::partio` compatibility target. Depends on the matching `partio-lib`.
- `partio-tools`: Headless command-line tools, currently `partattr`, `partconvert`, and `partinfo`. Depends on the matching `partio-lib`.
- `partio-python`: SWIG Python bindings for Partio, built for Python 3.10 through 3.14. Depends on the matching `partio-lib`.
- `partio`: Default metapackage for C++ and headless tool consumers. Depends on the matching `partio-lib`, `partio-dev`, and `partio-tools`; Python bindings and GUI tools are opt-in or omitted for now.

## OpenQMC

Recipe versions: `0.7.1`

OpenQMC provides Quasi-Monte Carlo sampling APIs for rendering and graphics applications.

- `openqmc-lib`: Shared OpenQMC runtime library for the binary table build.
- `openqmc-dev`: Headers, installed table include fragments, CMake package files, and Windows import library for the binary table build. Depends on the matching `openqmc-lib` and conflicts with `openqmc-header-only`.
- `openqmc-header-only`: Header-only CMake package exporting `OpenQMC::OpenQMC` without `OQMC_ENABLE_BINARY` or a shared runtime library. Conflicts with `openqmc-dev`.
- `openqmc`: Default metapackage matching the old pixi-recipes behavior. Depends on the matching `openqmc-lib` and `openqmc-dev`; use `openqmc-header-only` to opt into the interface-library flavor.

## OpenSubdiv

Recipe versions: `3.7.0`

OpenSubdiv provides subdivision surface evaluation libraries for CPU and GPU workflows.

- `opensubdiv-lib`: CPU-only implementation library. On Linux and macOS this carries the shared `osdCPU` runtime library; on Windows upstream 3.7.0 installs a static `osdCPU.lib` rather than a DLL.
- `opensubdiv-dev`: CPU-only headers, CMake package files, and Unix static archives. Depends on the matching `opensubdiv-lib` and conflicts with `opensubdiv-gpu-dev`.
- `opensubdiv`: Default CPU-only metapackage for C++ consumers. Depends on the matching `opensubdiv-lib` and `opensubdiv-dev`.
- `opensubdiv-gpu-lib`: GPU-enabled implementation libraries, carrying both `osdCPU` and `osdGPU`. Linux builds enable OpenGL, GLEW, GLFW, and TBB with CUDA and Metal disabled; macOS builds enable Metal, OpenGL, GLEW, GLFW, and TBB with CUDA disabled. Windows GPU outputs are not built for now.
- `opensubdiv-gpu-dev`: GPU-enabled headers, CMake package files, and Unix static archives. Depends on the matching `opensubdiv-gpu-lib` and conflicts with `opensubdiv-dev`; also carries the TBB and Linux OpenGL development dependencies required by the exported CMake targets.
- `opensubdiv-gpu`: GPU-enabled compatibility/default metapackage. Depends on the matching `opensubdiv-gpu-lib` and `opensubdiv-gpu-dev`, and conflicts with `opensubdiv`.

## SeExpr

Recipe versions: `3.0.1`

SeExpr is an embeddable expression evaluation engine for graphics applications.

- `seexpr-lib`: Core SeExpr2 runtime library. On Windows, upstream 3.0.1 builds a static library rather than a DLL.
- `seexpr-dev`: C++ headers and CMake package files. Depends on the matching `seexpr-lib`.
- `seexpr-tools`: Non-GUI command-line utilities, currently upstream's `eval` and `listVar` tools under `share/SeExpr2/utils`. Depends on the matching `seexpr-lib`.
- `seexpr`: Default metapackage for C++ consumers. Depends on the matching `seexpr-lib` and `seexpr-dev`; tools, Python bindings, Qt editor/UI, LLVM backend, docs, and demos are not included by default.

## OpenImageIO

Recipe versions: `2.5.19.1`, `3.0.19.1`, `3.1.14.0`

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

## OpenShadingLanguage

Recipe versions: `1.15.5.0`

OpenShadingLanguage provides a production shading language, compiler, runtime libraries, and OpenImageIO integration.

- `openshadinglanguage-lib`: Shared OSL runtime libraries for CPU rendering. Depends on OpenImageIO, Imath, Partio, pugixml, libxml2, zlib, zstd, and LLVM/Clang runtime libraries.
- `openshadinglanguage-dev`: C++ headers, CMake package files, pkg-config metadata, and Windows import libraries. Depends on the matching `openshadinglanguage-lib` and `openshadinglanguage-tools` because upstream exports `oslc` and `oslinfo` in its CMake target set.
- `openshadinglanguage-tools`: Headless command-line tools, currently `oslc` and `oslinfo`, plus installed standard shader headers.
- `openshadinglanguage-guitools`: Qt-dependent GUI tools, currently `osltoy`. Depends on the matching `openshadinglanguage-lib` and Qt 6.
- `openshadinglanguage-python`: Python `oslquery` bindings, built for Python 3.10 through 3.14. Depends on the matching `openshadinglanguage-lib` and `openimageio-python`.
- `openimageio-format-osl`: OpenImageIO input plugin for procedural OSL images (`.osl`, `.oso`, `.oslgroup`, and `.oslbody`). Depends on the matching OSL runtime and OpenImageIO runtime.
- `openshadinglanguage`: Default metapackage for C++ and headless tool consumers. Depends on the matching `openshadinglanguage-lib`, `openshadinglanguage-dev`, and `openshadinglanguage-tools`; Python bindings, GUI tools, and OIIO plugin are opt-in.
- `openshadinglanguage-cuda-*` and `openimageio-format-osl-cuda`: Linux-only CUDA-enabled flavor built with `osl_gpu=cuda`. These packages install the same upstream CMake target names as the CPU flavor and are mutually exclusive with the CPU packages. They are intended for explicit local/private builds rather than the default publish path.
