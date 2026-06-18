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
