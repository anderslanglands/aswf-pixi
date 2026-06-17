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

## MaterialX

Recipe versions: `1.39.4`

MaterialX is an open standard for transferring rich material and look-development content.

- `materialx-lib`: Shared MaterialX runtime libraries plus installed MaterialX libraries and resources. Render modules are currently disabled.
- `materialx-dev`: C++ headers, CMake package files, and Windows import libraries. Depends on the matching `materialx-lib`.
- `materialx-python`: Python bindings for MaterialX, built for Python 3.10 through 3.14. Depends on the matching `materialx-lib`. Render Python modules and upstream helper scripts that require disabled render modules are not included.
- `materialx`: Default metapackage for complete consumers. Depends on the matching `materialx-lib`, `materialx-dev`, and compatible `materialx-python`.
