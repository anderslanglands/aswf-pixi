When a one-off task needs a Python package that is not already available, write a temporary PEP 723 script with a `# /// script` dependency block and run it with `uv run` so dependencies are installed in an ephemeral environment. Remove the temporary script after use.

# Rebasing

When Anders asks to rebase a branch on another, first check if the current branch's changes can be cleanly replayed on top of the rebase target and do that preferentially. When rebasing, if there are any conflicts, DON'T try and fix them, surface them to Anders so you can discuss with him how best to handle them.

# Writing Tests

When implementing tests, always launch an adversarial review agent when the tests are done to check whether the tests actually test anything useful or are just encoding the current code behaviour, whether there are holes in the tested coverage, and whether tests are making invalid assumptions about the intended behaviour or environment.

# Reviewing Code

When Anders asks to launch one or more reviewers, make them adversarial, and collate their findings into a single report to discuss with Anders. Don't ever start fixing things without discussing with Anders first.

# ASWF Pixi Packaging

This repository is a new version of `~/code/pixi-recipes`. It builds conda packages with `rattler-build` and provides `pixi.toml` files for easy consumption of those packages.

Core goals:

- Upload built packages to `anaconda.org`.
- The `anaconda.org` channel/user is `anderslanglands`; the consumer channel URL is `https://conda.anaconda.org/anderslanglands`.
- Support both local test uploads and build/upload from GitHub Actions.
- Store individual version recipes in this repo, for example `imath/3.1.2` and `imath/3.2.2`, so changes and fixes remain trackable over time. Start with one version per package unless Anders asks for more.
- Use a single `recipe.yaml` per package version for all build flavours.
- Represent different feature combinations as separate `outputs` from that one recipe, including shared build/staging outputs where useful.
- Confirm the actual `anaconda.org` organization/channel with Anders before hard-coding upload targets, consumer channels, or GitHub Actions upload destinations.
- Expose different subpackages as pixi features.
- Name runtime library subpackages with a `-lib` suffix and development subpackages with a `-dev` suffix, for example `imath-lib` and `imath-dev`, not `-devel`.
- Prefer keeping the upstream/default package name, for example `imath`, as a compatibility metapackage that depends on the useful default split packages.
- Do not use local dependency paths in `pixi.toml`; that approach was not worth it.

Package conversion process:

- Work through packages from `~/code/pixi-recipes` one by one.
- For each package, do not immediately implement the conversion. First inspect the old recipe and propose a package breakdown for discussion with Anders.
- Discuss which subpackages should exist, which outputs should be published, and which pixi features should expose them.
- Prefer avoiding upstream patches. If builds fail, surface the problem to Anders with options and a recommendation before patching upstream library code.
- Keep this `AGENTS.md` updated as the process evolves.
- Keep `README.md` updated whenever package recipes or published package outputs are added, removed, renamed, or materially changed.
- Include an `about.repository` URL pointing at the upstream GitHub repository in every recipe when one exists; upstream-release automation may warn and skip recipes that cannot be associated with a GitHub repository.
- Keep root build tooling solvable before packages are uploaded; put package-specific consumer pixi feature manifests next to the versioned recipe when publishing has not happened yet.
- For test-label validation, put `https://conda.anaconda.org/anderslanglands/label/test` before `https://conda.anaconda.org/anderslanglands` in consumer manifests.
- Consumer validation manifests should list only platforms whose artifacts have actually been published for that label; broaden the platform list as CI publishes more platforms.
- GitHub Actions package builds are manually triggered with `workflow_dispatch`; do not add continuous package publishing on push without discussing it with Anders.
- The package build workflow accepts recipe directories, target platforms, publish target, and an optional integer build number override. Use the build number override when testing a repeated upload for the same package version.
- GitHub Actions publishes with the `ANACONDA_TOKEN` repository secret, exposed to `rattler-build upload anaconda` as `ANACONDA_API_KEY`.
- Keep the `test-label` publish path low-friction, but use the `anaconda-production` GitHub environment for `default-label` publishes so production uploads can require review in repository settings.
- Nightly upstream-release automation should create or refresh one reviewable PR per created package/version recipe from `automation/upstream-release-prs/<package>/<version>`, then dispatch the existing package build workflow separately for each recipe selector with `publish_target = test-label` and smoke tests enabled by default. A successful smoke-tested test-label workflow_dispatch build should automatically merge only the matching automation PR when the PR head SHA still equals the tested workflow SHA; the merge should then create a promotion ref at the merge commit and dispatch the existing package build workflow from that ref with `publish_target = default-label` so production uploads still use the `anaconda-production` environment gate. If PR creation is blocked by repository settings, keep each branch/build path non-fatal and surface a manual PR URL; use `UPSTREAM_RELEASE_PR_TOKEN` when a non-`GITHUB_TOKEN` credential is needed for PR creation, and require it for build workflow dispatch and auto-merge from GitHub Actions.
- `UPSTREAM_RELEASE_PR_TOKEN` should be a fine-grained token limited to this repository with Contents read/write, Pull requests read/write, and Actions read/write permissions.
- Generated upstream-release PRs should update README package version lists as one bullet per recipe version. Keep `README.md merge=union` in `.gitattributes` and keep the updater idempotent so concurrent generated PRs adding different version bullets merge cleanly and later runs normalize duplicates or ordering.
- To recheck a fixed generated upstream release PR, commit the fix to `automation/upstream-release-prs/<package>/<version>` and manually run `build-packages.yml` on that same branch with `recipes=<package>/<version>`, `publish_target=test-label`, `build_number=""`, and `run_smoke_tests=true`; a successful matching run is what enables auto-merge.
- The manual workflow platform input accepts `default`, `all`, or an explicit comma-separated list. `default` means `linux-64,win-64,osx-arm64`; keep `osx-64` available for explicit compatibility builds but do not include it in the routine default set unless Anders asks.
- CI builds should write an artifact `manifest.json` describing the exact package filename, build string, subdir, and version for every publishable output.
- CI publish jobs should upload only packages listed in the artifact manifests, not arbitrary `.conda` files found under the artifact directory.
- CI smoke tests should consume every manifest-listed package from the selected Anaconda label in clean pixi environments, verify `pixi list --json` resolves the exact uploaded build/source, and run recipe consumer tests for dev/top-level packages when present. They should not rely on package-local lockfiles.
- Never write package tests, recipe tests, smoke tests, or consumer tests that depend on pkg-config/pkgconfig `.pc` files existing or working. Validate development packages with CMake package config/targets unless Anders explicitly asks for pkg-config coverage.
- Keep the GitHub Actions platform-to-runner mapping in `scripts/ci_matrix.py`, and re-check GitHub's current hosted runner labels before changing macOS runners.
- Keep GitHub workflow actions on Node 24-capable versions instead of relying on temporary Node runtime override environment variables.

Local package preflight:

- Before pushing recipe or workflow changes, run a local native build on any platform that is readily available, especially when adding a new target platform.
- Use a clean generated `output/` directory for local preflight builds so stale packages are not picked up by manifest or upload checks.
- Match the GitHub Actions build command locally rather than relying only on shorthand tasks. For example, on a Windows machine validating Imath before enabling `win-64` in CI, run:
  `pixi run rattler-build build --recipe imath/3.2.2/recipe.yaml --target-platform win-64 --channel https://conda.anaconda.org/anderslanglands --channel conda-forge --channel-priority strict --output-dir output --package-format conda --test native --variant c_compiler=vs2022 --variant cxx_compiler=vs2022`
- Windows builds should pass both `--variant c_compiler=vs2022` and `--variant cxx_compiler=vs2022`; otherwise `rattler-build` currently renders `compiler('c')`/`compiler('cxx')` as `vs2017_win-64`, which is not available on current GitHub-hosted Windows runners.
- If testing a repeated package version/build, pass the same explicit build number to both build and manifest collection, for example add `--build-num 1` to `rattler-build build` and `--build-number 1` to `scripts/collect_artifacts.py`.
- After a successful local build, collect and validate the exact package set with:
  `pixi run python scripts/collect_artifacts.py --recipe imath/3.2.2 --platform win-64 --output-dir output --manifest output/manifest.json`
- Dry-run the publish selection before uploading anything:
  `pixi run python scripts/publish_packages.py --target test-label --root output --dry-run`
- Local preflight should normally stop before upload. Only upload locally to the `test` label when Anders explicitly wants a local test upload; otherwise use the manual GitHub Actions workflow with `publish_target = artifact-only` first, then `test-label`, then `default-label`.

MaterialX packaging decisions:

- Package MaterialX 1.39.5 as `materialx-lib`, `materialx-dev`, `materialx-render`, `materialx-render-osl`, `materialx-render-mdl`, `materialx-render-slang`, `materialx-guitools`, `materialx-python`, and a compatibility/default `materialx` metapackage.
- The `materialx` metapackage should depend on `materialx-lib`, `materialx-dev`, and `materialx-python` so downstream consumers can depend on `materialx` for the complete default base C++ and Python surface without render, renderer SDKs, OpenGL/X11, or GUI dependencies.
- Bundle all generator targets in the base packages: GLSL, MSL, OSL, MDL, and Slang generators are dependency-free in upstream MaterialX and should be available from `materialx-lib`/`materialx-dev`/`materialx-python`.
- Keep render and renderer-specific dependencies opt-in: `materialx-render` carries core/platform render targets, `materialx-render-osl` carries OSL render plus OSO generation support and depends on OpenShadingLanguage/OpenImageIO, `materialx-render-mdl` is a convenience dependency package because upstream 1.39.5 has no installed `MaterialXRenderMdl` target, and `materialx-render-slang` carries Slang render support.
- `materialx-render-slang` depends on the separate `shader-slang-dev 2026.11` package for the Slang SDK and CMake target, while the MaterialX recipe fetches the matching `shader-slang/slang-rhi` source at the pinned Slang submodule revision and packages the public RHI headers needed by downstream consumers.
- Build `materialx-guitools` from a git checkout with submodules, not the release tarball, because MaterialX 1.39.5's release tarball omits the NanoGUI, ImGui, and ImGuiNodeEditor submodule payloads required by the viewer and graph editor.
- Build `materialx-python` for Python 3.10, 3.11, 3.12, 3.13, and 3.14.
- Keep `materialx-python` co-installable with `materialx`/`materialx-dev`; the old `materialx` vs `materialx-python` conflict only existed because pixi-recipes used two monolithic packages with overlapping files.
- Do not carry the old MaterialX `add-cstdint.patch` into 1.39.4 or newer unless a build proves it is still needed; upstream 1.39.4 release notes mention a GCC 15 missing-header fix.
- Carry the narrow MaterialX 1.39.5 `fix-render-slang-gcc15.patch` until upstream fixes the exported `MaterialXRenderSlang/SlangBlit.h` extra qualifications, missing `<cstring>` includes in the Slang renderer implementation/exported header, and the `MaterialXRenderSlang` target links on `MaterialXRenderHw`/`MaterialXGenSlang`.
- MaterialX generator headers use C++17 library features such as `std::string_view`; downstream CMake consumer tests should request `cxx_std_17` for now. This is an upstream CMake export ergonomics gap: if we later want linked MaterialX targets to propagate that requirement automatically, discuss an upstream fix or a narrow recipe patch adding interface compile features.

OpenEXR packaging decisions:

- Package OpenEXR 3.4.12 as `openexr-core-lib`, `openexr-core-dev`, `openexr-lib`, `openexr-dev`, `openexr-tools`, `openexr-python`, and a compatibility/default `openexr` metapackage.
- Keep `OpenEXRCore` consumable on its own: `openexr-core-dev` carries the C API headers plus a small `OpenEXRCoreConfig.cmake` and `OpenEXRCore.pc`, while the upstream full `OpenEXRConfig.cmake` and `OpenEXR.pc` stay in `openexr-dev`.
- The `openexr` metapackage should depend on the full C++ runtime/dev/tools surface, but not `openexr-python`; keep Python opt-in as `openexr-python`.
- Build `openexr-python` for Python 3.10, 3.11, 3.12, 3.13, and 3.14.
- Use external `imath-dev` 3.2, `libdeflate`, `openjph`, and `zlib` dependencies rather than vendored copies.

OpenColorIO packaging decisions:

- Package OpenColorIO 2.5.1 as `opencolorio-lib`, `opencolorio-dev`, `opencolorio-tools`, `opencolorio-python`, and a compatibility/default `opencolorio` metapackage.
- The `opencolorio` metapackage should depend on the C++ runtime and development surface only, not Python or tools; keep `opencolorio-python` and `opencolorio-tools` opt-in.
- Build `opencolorio-python` for Python 3.10, 3.11, 3.12, 3.13, and 3.14.
- Build `opencolorio-tools` with `OCIO_USE_OIIO_FOR_APPS=OFF`; image tools should use OpenEXR rather than OpenImageIO until this repository has its own OpenImageIO package.
- Keep Java, OpenFX, Nuke, docs, and tests disabled in package builds unless Anders explicitly asks for them.

OpenVDB packaging decisions:

- Package OpenVDB 13.0.0 as `openvdb-lib`, `openvdb-dev`, `openvdb-tools`, `openvdb-guitools`, `openvdb-python`, `nanovdb-dev`, `nanovdb-tools`, `nanovdb-openvdb-tools`, `nanovdb`, and a compatibility/default `openvdb` metapackage.
- The `openvdb` metapackage should depend on the C++ runtime, development surface, and core command-line tools only; keep Python bindings, GUI/render tools, and NanoVDB opt-in.
- Build `openvdb-python` for Python 3.11, 3.12, 3.13, and 3.14.
- Keep AX, `vdb_tool`, Houdini, Maya, docs, and upstream unit tests disabled unless Anders explicitly asks for them.
- Package `openvdb-tools` with non-GUI tools only: `vdb_print` and `vdb_lod`.
- Package `openvdb-guitools` with `vdb_view` and `vdb_render`; enable PNG and OpenEXR support for `vdb_render`.
- Package standalone NanoVDB as `nanovdb-dev`, `nanovdb-tools`, and a default `nanovdb` metapackage that does not depend on OpenVDB.
- Package OpenVDB-dependent NanoVDB conversion separately as `nanovdb-openvdb-tools`.
- Pin OpenVDB and NanoVDB builds to the TBB 2022 line for now (`>=2022.3,<2023`); OpenVDB 13.0.0 fails to compile with conda-forge `tbb-devel` 2023 because its `tbb::task::self()` fallback is selected against headers where that API is gone.


libuhdr packaging decisions:

- Package libuhdr 1.4.0 as `libuhdr-lib`, `libuhdr-dev`, and a compatibility/default `libuhdr` metapackage.
- The `libuhdr` metapackage should depend on the C++ runtime and development surface only.
- Keep examples/tools, Java, GLES, tests, benchmarks, fuzzers, and vendored dependencies disabled unless Anders explicitly asks for them.
- Use external `libjpeg-turbo` rather than the upstream vendored dependency path.
- Prefer recipe-side manual install logic for Windows before carrying upstream CMake install patches; if that becomes brittle, discuss patching options with Anders.

Ptex packaging decisions:

- Package Ptex 2.5.1 as `ptex-lib`, `ptex-dev`, `ptex-tools`, and a compatibility/default `ptex` metapackage.
- The `ptex` metapackage should depend on the C++ runtime, development surface, and `ptxinfo` tool.
- Build shared libraries only; keep static libraries, docs, and PRMan 15 compatibility disabled unless Anders explicitly asks for them.
- Set `PTEX_VER` explicitly when building from release tarballs so installed headers and tools report 2.5 rather than upstream's tarball fallback version.
- Use external `libdeflate`. Keep `zlib` as a `ptex-dev` runtime dependency because upstream 2.5.1's installed CMake config still calls `find_package(ZLIB)` even though the library links against libdeflate.
- Do not enable Ptex support in OpenImageIO, OpenSubdiv, or OpenUSD as part of the standalone Ptex package; wire those consumers separately if Anders asks.

Partio packaging decisions:

- Package Partio 1.20.0 as `partio-lib`, `partio-dev`, `partio-tools`, `partio-python`, and a compatibility/default `partio` metapackage.
- The `partio` metapackage should depend on the C++ runtime, development surface, and headless command-line tools only; keep Python bindings opt-in as `partio-python`.
- Build `partio-python` for Python 3.10, 3.11, 3.12, 3.13, and 3.14.
- Keep GUI tools disabled or omitted for now. Upstream's `partview` requires OpenGL/GLUT, while `partedit` and `partinspect` require Qt Python bindings.
- Build `partio-tools` with only headless tools: `partattr`, `partconvert`, and `partinfo`.
- Upstream 1.20.0 does not install CMake package metadata; install a small recipe-side `PartioConfig.cmake` exporting `Partio::partio`, lowercase `partio` config-mode aliases, and the `partio::partio` compatibility target, and validate consumers through CMake.
- Use external zlib support for compressed particle formats.
- Patch the upstream Python binding CMake during the recipe build so macOS extension modules use dynamic symbol lookup instead of linking directly to `libpython`; direct `libpython` linkage segfaulted during `import partio` on `osx-arm64`.

OpenQMC packaging decisions:

- Package OpenQMC 0.7.1 as `openqmc-lib`, `openqmc-dev`, `openqmc-header-only`, and a compatibility/default `openqmc` metapackage.
- The `openqmc` metapackage should match the old pixi-recipes behavior: binary table build with `OPENQMC_ENABLE_BINARY=ON`, depending on the matching `openqmc-lib` and `openqmc-dev`.
- `openqmc-header-only` should build with `OPENQMC_ENABLE_BINARY=OFF` and export the same `OpenQMC::OpenQMC` CMake target as an interface library.
- `openqmc-dev` and `openqmc-header-only` both install `include/oqmc/**` and `lib/cmake/OpenQMC/**`; keep them mutually exclusive with package constraints.
- Keep OpenQMC tools disabled unless Anders explicitly asks for them. Upstream tools use TBB/glm and install broad command names such as `benchmark`, `generate`, `plot`, and `trace`.
- Carry the narrow project-version patch for 0.7.1 so installed CMake package version metadata reports 0.7.1 instead of upstream's `project(OpenQMC VERSION 0.1.0)`.
- Carry the narrow Windows shared-library table export patch for 0.7.1 so MSVC consumers import the binary blue-noise table data from `OpenQMC.dll` correctly.

OpenSubdiv packaging decisions:

- Package OpenSubdiv 3.7.0 with three public flavor metapackages: `opensubdiv`, `opensubdiv-gpu`, and `opensubdiv-cuda`. Keep matching runtime/development split outputs underneath them, for example `opensubdiv-lib`/`opensubdiv-dev`, `opensubdiv-gpu-lib`/`opensubdiv-gpu-dev`, and `opensubdiv-cuda-lib`/`opensubdiv-cuda-dev`.
- The `opensubdiv` metapackage should depend on the CPU-only runtime and development surface.
- The `opensubdiv-gpu` metapackage should mean non-CUDA graphics-API GPU support: OpenGL/GLEW/GLFW/TBB on Linux and Windows where available, and Metal/OpenGL/GLEW/GLFW/TBB on macOS. It should not depend on CUDA packages.
- The `opensubdiv-cuda` metapackage should mean CUDA-enabled OpenSubdiv, initially for Linux and Windows. Enable CUDA plus OpenGL/GLEW/GLFW/TBB where useful for interop, keep Metal disabled, and do not build it on macOS.
- Keep the CPU, non-CUDA GPU, and CUDA flavors mutually exclusive because the builds install overlapping headers, CMake metadata, and `osdCPU`/`osdGPU` implementation libraries.
- Keep OpenSubdiv examples, tutorials, regression tests, GL tests, PTex, docs, OpenMP, OpenCL, CLEW, DirectX, and macOS frameworks disabled unless Anders explicitly asks for them.
- The CPU-only build should keep TBB, CUDA, OpenGL, Metal, GLEW, and GLFW disabled.
- Upstream 3.7.0 uses legacy `FindCUDA`; keep CUDA builds pinned to the CUDA 12.9 package line for now, pass explicit conda CUDA include/library hints, and fail the staging build if CMake does not find usable CUDA include and `nvcc` paths.
- On Windows, depend on concrete `cuda-nvcc_win-64` rather than the `cuda-nvcc` meta-package so the CUDA build does not pull an extra `vs2019_win-64` activation on top of the explicit VS2022 compiler variant.
- For Windows `opensubdiv-cuda`, accept a static-only `osdGPU.lib`/`osdCPU.lib` package if upstream 3.7.0 does not produce shared libraries cleanly; do not treat the lack of Windows DLLs as a blocker.
- Keep the GPU and CUDA CMake packages self-contained for clean consumers: `OpenSubdivConfig.cmake` should load dependency targets such as TBB, OpenGL, and Threads before upstream targets, and CUDA development outputs should depend on `cuda-cudart-dev` for the runtime/static library paths exported by upstream.

SeExpr packaging decisions:

- Package SeExpr 3.0.1 as `seexpr-lib`, `seexpr-dev`, `seexpr-tools`, and a compatibility/default `seexpr` metapackage.
- The `seexpr` metapackage should depend on the C++ runtime and development surface only; keep tools opt-in as `seexpr-tools`.
- Keep Qt editor/UI, Python bindings, LLVM backend, docs, tests, PNG/image demos, and demo editor components disabled unless Anders explicitly asks for them.
- Keep `ENABLE_SSE4=OFF` for portability, especially on non-x86 platforms.
- Upstream 3.0.1 installs legacy variable-based CMake metadata named `seexpr2-config.cmake`; validate development packages with that CMake package config and direct library discovery rather than pkg-config.
- Upstream 3.0.1 builds a static `SeExpr2.lib` on Windows rather than a DLL; keep the Windows runtime package static-only unless Anders decides carrying a shared-library patch is worth it.

Shader Slang packaging decisions:

- Package Shader Slang 2026.11 as `shader-slang-lib`, `shader-slang-dev`, `shader-slang-tools`, and a compatibility/default `shader-slang` metapackage.
- Use the `shader-slang` package name rather than `slang`, because conda-forge already uses `slang` for the unrelated S-Lang library.
- The `shader-slang` metapackage should depend on the C++ runtime, development surface, and headless tools.
- Package `shader-slang-tools` with `slang`, `slangc`, `slangd`, and `slangi`.
- `shader-slang-dev` should depend on the matching runtime and tools because upstream's installed CMake target set exports `slangc` and sets `SLANG_EXECUTABLE`.
- Build from the `v2026.11` git source with submodules so upstream CMake detects the intended version from `git describe`.
- Keep DXIL/DXC support disabled in the first package. Upstream's DXC path may download prebuilt DXC or clone/build DXC plus LLVM/Clang during configure; add DXIL support later only after deciding how to package DXC reproducibly.
- Keep slang-LLVM support disabled in the first package. This omits direct CPU-native LLVM/JIT/object-code workflows but avoids fetching the upstream `slang-llvm` binary or linking against a fragile dynamic system LLVM.
- Build the optional `slang-glslang` wrapper against conda-forge `glslang`/`spirv-tools`/`spirv-headers`; Slang uses this runtime-loaded module for SPIR-V output, so do not disable it unless the package intentionally drops SPIR-V coverage.
- Keep GFX, slang-rhi, tests, examples, replayer, CUDA, OptiX, NVAPI, Aftermath, Xlib, Dawn, Tint, and SPIRV-Tools mimalloc disabled unless Anders explicitly asks for those surfaces.
- Validate tools by compiling a tiny compute shader to GLSL and SPIR-V, and validate development packages through upstream's CMake config and `slang::slang` target rather than pkg-config.

OpenImageIO packaging decisions:

- Package OpenImageIO 2.5.19.1, 3.0.19.1, and 3.1.14.0 as `openimageio-lib`, `openimageio-dev`, `openimageio-tools`, `openimageio-python`, individual optional format plugin packages, and a compatibility/default `openimageio` metapackage.
- Build common OpenImageIO formats into `openimageio-lib` with `EMBEDPLUGINS=ON`; this avoids private-symbol leakage seen when OpenEXR/TIFF/JPEG/PNG-class core formats are shipped as external DSOs.
- Keep `openimageio-dev` CMake metadata free of tool and plugin targets by building the runtime/development surface, tools, Python bindings, and plugins from separate staging builds.
- The `openimageio` metapackage should depend on the C++ runtime, development surface, and headless tools; keep Python bindings and extra format plugins opt-in.
- `openimageio-lib` should embed common formats: OpenEXR, TIFF, JPEG, PNG/ICO, BMP, DPX, HDR, PNM, PSD, SGI, TGA, Cineon, DDS, FITS, IFF, RLA, Softimage, Zfile, null, and terminal output.
- Build the core JPEG plugin with libuhdr support for upstream versions that support it; omit libuhdr from 2.5.19.1.
- Package optional plugins as `openimageio-format-gif`, `openimageio-format-webp`, `openimageio-format-jpeg2000`, `openimageio-format-jpegxl`, `openimageio-format-heif`, `openimageio-format-raw`, `openimageio-format-dicom`, `openimageio-format-ffmpeg`, and `openimageio-format-openvdb`, but omit `openimageio-format-jpegxl` from 2.5.19.1 because upstream does not provide it there.
- `openimageio-format-openvdb` should depend on `openvdb-lib`, not `openvdb-python` or the OpenVDB compatibility metapackage.
- Build `openimageio-python` for Python 3.10, 3.11, 3.12, 3.13, and 3.14; it depends on `openimageio-lib`, which carries the common read/write formats by default.
- Keep Qt viewer (`iv`), OpenCV, Freetype text rendering support, Ptex integration, R3DSDK, Nuke, docs, tests, and fonts disabled unless Anders explicitly asks for them.


OpenUSD packaging decisions:

- Package OpenUSD 26.05 as `openusd-minimal-lib`, `openusd-minimal-dev`, `openusd-minimal-tools`, `openusd-minimal-python`, and `openusd`.
- The `openusd-minimal-*` family should stay lean and depend only on MaterialX, OpenSubdiv, TBB, and Python/Jinja where Python support is enabled. Enable MaterialX support, exec, validation, and command-line tools; keep imaging, USD imaging, GUI tools, OpenImageIO, OpenColorIO, OpenVDB, Draco, Embree, Vulkan, Ptex, Alembic, OSL, PRMan, HDF5, docs, examples, tutorials, tests, generated-code validation, and precompiled headers disabled.
- Split only the non-Python minimal build into runtime, development, and tools outputs. Keep `openusd-minimal-python` as one package containing runtime libraries, headers, CMake metadata, tools, and `pxr` Python modules because Python support changes the OpenUSD build ABI/surface and installs overlapping files.
- Use `openusd` for the full Python-enabled package. It should be one package containing runtime libraries, headers, CMake metadata, tools, `pxr` Python modules, USD imaging, `usdview`, GUI dependencies, MaterialX render support, and supported plugins. It depends on `materialx-render` because USD imaging builds `hdSt` against MaterialXRender headers. It is mutually exclusive with all `openusd-minimal-*` packages.
- Full `openusd` should enable USD tools, imaging, USD imaging, validation, exec, USDView, GL/Metal support where available, OpenImageIO, OpenColorIO, ImageIO, Draco, Embree, MaterialX, and OpenVDB support. Keep Vulkan disabled for 26.05 because the old recipe hit a Vulkan header API mismatch; keep Ptex, Alembic, OSL, Renderman/PRMan, HDF5, MayaPy tests, AnimX tests, generated-code validation, and precompiled headers disabled unless Anders asks.
- Keep the old OpenUSD build stability fixes: cap recipe build parallelism at 24 jobs and remove `-pipe`, `-ffunction-sections`, and `-fvisibility-inlines-hidden` from compiler flags. Keep `PXR_PY_UNDEFINED_DYNAMIC_LOOKUP=OFF` for non-macOS Python-enabled builds, but enable it on macOS because conda-forge macOS Python reports static sysconfig metadata and direct `libpython` linkage crashes during `import pxr.Tf`; carry the narrow `link-python-to-executables.patch` so executables that link `usd_python` still link Python explicitly and avoid unresolved `_Py_NoneStruct`.
- Constrain Python 3.14 Python-enabled OpenUSD packages to the normal `python_abi 3.14.* *_cp314` ABI so solves cannot drift to conda-forge's free-threaded `cp314t` packages, for example through PySide6. Patch OpenUSD's installed CMake config so Python-enabled packages resolve `Python3` from the installed conda prefix before falling back to ambient system discovery.

OpenUSD Typhoon packaging decisions:

- Package the NVIDIA Omniverse `OpenUSD` `typhoon-anders` branch as `openusd-typhoon` version `26.05.8.4bdd4b656`, with the recipe source pinned to full commit `4bdd4b6561529720164f7d2f1e865382a797a38b`.
- Keep `openusd-typhoon` as a full Python-enabled package derived from the latest full `openusd` recipe; do not publish separate Typhoon minimal split packages unless Anders asks.
- `openusd-typhoon` is mutually exclusive with `openusd` and all `openusd-minimal-*` packages because it installs overlapping libraries, headers, CMake metadata, tools, Python modules, and plugin resources.
- `openusd-typhoon` is test-label-only. Keep `extra.allowed_publish_targets = [test-label]` in the recipe and keep CI/build-number/publish scripts enforcing that metadata so default-label publishes fail before upload. Version Typhoon packages as `26.05.<recipe-build-serial>.<short-commit>`, where the serial starts at `1` and increments for each new Typhoon package definition; for example `26.05.8.4bdd4b656`. Use dot separators because rattler normalizes `+` and `-` version separators to `.` in rendered package metadata. Build Typhoon with channels ordered as test label, `anderslanglands`, then conda-forge, and with `--channel-priority disabled` because strict priority can exclude matching dependency builds split across test and main labels. Typhoon's upstream branch pixi manifest enables the Embree renderer path with OpenQMC 0.7.1, and hdEmbree links `OpenQMC::OpenQMC`; keep `embree 4.4.*` and `openqmc-dev ==0.7.1` in host and run requirements while Embree is enabled. Keep `openimageio-dev 2.5.*` for Typhoon even though the latest full OpenUSD recipe uses 3.1, because the branch's hdEmbree code uses the OIIO 2.5 TextureSystem/TextureOpt API. Do not add NumPy just because it appears in the upstream development pixi manifest; current package builds keep upstream tests and Boost.NumPy disabled, and the source treats NumPy as optional test/runtime buffer support.

GoldenEye packaging decisions:

- Package GoldenEye 0.1.0 as a single `goldeneye` Python package; do not split runtime or development outputs because upstream installs only Python modules, CLI entry points, pytest plugin metadata, and static viewer assets.
- Build `goldeneye` for Python 3.10, 3.11, 3.12, 3.13, and 3.14. Carry narrow recipe-side Python 3.10 compatibility patches: relax upstream `requires-python` from `>=3.11` to `>=3.10`, and fall back from stdlib `tomllib` to `tomli` on Python 3.10.
- Keep `openusd-typhoon` as an unconstrained runtime dependency so the default Typhoon renderer works out of the box. GoldenEye may publish to either `test-label` or `default-label`; until `openusd-typhoon` is promoted, default-label consumers and smoke tests should use the main Anders channel first, then the test label for Typhoon, then conda-forge, with channel priority disabled.

OpenShadingLanguage packaging decisions:

- Package OpenShadingLanguage 1.15.5.0 as `openshadinglanguage-lib`, `openshadinglanguage-dev`, `openshadinglanguage-tools`, `openshadinglanguage-guitools`, `openshadinglanguage-python`, `openimageio-format-osl`, and a compatibility/default `openshadinglanguage` metapackage.
- The `openshadinglanguage` metapackage should depend on the C++ runtime, development surface, and headless tools only; keep Python bindings, Qt GUI tools, and the OIIO OSL plugin opt-in.
- Package Qt-dependent tools separately as `openshadinglanguage-guitools`; upstream 1.15.5.0 only installs `osltoy` in this category, and the recipe uses Qt 6.
- Package the OpenImageIO OSL procedural input plugin as `openimageio-format-osl`; it depends on `openshadinglanguage-lib` and `openimageio-lib`, not the OSL compatibility metapackage.
- Build `openshadinglanguage-python` for Python 3.10, 3.11, 3.12, 3.13, and 3.14. The Python module imports `OpenImageIO`, so it must depend on `openimageio-python` as well as the matching OSL runtime.
- Keep upstream tests, `testshade`, and `testrender` disabled in package builds unless Anders explicitly asks to package or run them.
- Use `winflexbison` for Windows OSL builds because conda-forge does not publish `bison`/`flex` for `win-64`; keep LLVM link-time dependencies such as `libxml2-devel` and `zstd` explicit in OSL host requirements.
- Provide a Linux-only CUDA-enabled flavor named with `-cuda` package suffixes (`openshadinglanguage-cuda-lib`, `openshadinglanguage-cuda-dev`, `openshadinglanguage-cuda-tools`, `openshadinglanguage-cuda-guitools`, `openshadinglanguage-cuda-python`, `openimageio-format-osl-cuda`, and `openshadinglanguage-cuda`). Do not call these packages `-optix`.
- Keep `osl_gpu=cpu` as the only default recipe variant. Build CUDA packages explicitly with `--variant osl_gpu=cuda` and an optional `--variant cuda_target_arch=sm_XX`; the root task uses `sm_60` as a conservative default.
- Do not create or publish an OptiX SDK/header package. OSL 1.15.5.0 only requires OptiX headers when `OSL_USE_OPTIX=ON` and `OSL_BUILD_TESTS=ON`; package builds keep tests off, so the CUDA flavor builds the embedded CUDA/PTX path with conda CUDA packages and no redistributed OptiX payload.
- The CPU and CUDA OSL flavors install overlapping headers, libraries, tools, and CMake metadata; keep them mutually exclusive through run constraints.

MDL SDK packaging decisions:

- Package MDL SDK 2026.0.0 as `mdl-sdk-lib`, `mdl-sdk-dev`, `mdl-sdk-tools`, `mdl-sdk-plugin-dds`, `mdl-sdk-plugin-openimageio`, `mdl-sdk-plugin-distiller`, `mdl-sdk-python`, and a compatibility/default `mdl-sdk` metapackage.
- Do not split `libmdl_core` into a separate runtime package for now. Upstream installs `libmdl_core` and `libmdl_sdk` as distinct loadable modules, but they share substantial internal implementation and the useful consumer surface is simpler as one `mdl-sdk-lib` runtime.
- The `mdl-sdk` metapackage should depend on the C++ runtime, development surface, headless tools, and standard plugins only; keep Python bindings opt-in as `mdl-sdk-python`.
- `mdl-sdk-dev` should depend on the matching runtime, tools, and standard plugin outputs because upstream installs one CMake export set containing all of those targets.
- Build `mdl-sdk-python` for Python 3.10, 3.11, 3.12, 3.13, and 3.14.
- Keep SDK examples, CUDA examples, OpenGL/Vulkan/DXR/OptiX examples, Qt browser, Arnold plugin, AxF support, MaterialX example integration, Slang support, API documentation generation, and upstream unit tests disabled unless Anders explicitly asks for them.
- Treat CUDA support as part of the normal SDK code-generation API surface unless a build proves a separate runtime flavor is needed. Validate the PTX backend API without requiring a CUDA driver; package CUDA example binaries separately only if Anders asks for examples.
- Use external `openimageio-dev`/`openimageio-lib` for the `nv_openimageio` plugin. Keep the plugin separate so non-image consumers can install the SDK runtime without OpenImageIO.
- Include `openexr-dev` as a host requirement when building the OpenImageIO plugin; upstream's MDL OpenImageIO finder separately calls `find_package(OpenEXR)`.
- Ignore run exports from staging-only `openimageio-dev` and `openexr-dev` requirements so `mdl-sdk-lib` stays free of image I/O dependencies and only `mdl-sdk-plugin-openimageio` depends on `openimageio-lib`.
- Build `mdl-sdk-python` with the recipe-side standalone SWIG extension helper instead of enabling upstream `MDL_ENABLE_PYTHON_BINDINGS` in a full SDK build for every Python ABI. Keep Python staging requirements limited to Python, SWIG, CMake/Ninja, and compilers; put `numpy` on the final `mdl-sdk-python` runtime dependency because `pymdl.py` imports it.
- Use the versioned conda `clang-12` executable for MDL's `clang_PATH` bitcode-generation helper on non-macOS platforms. On macOS, do not install `clang-12` alongside the Clang 22 compiler wrappers because their `llvm-tools` requirements conflict; use conda Clang 22 from the build environment for `clang_PATH`, do not fall back to Apple `/usr/bin/clang`, and keep the package C/C++ compiler wrappers pinned to Clang 22.1.8 so embedded LLVM 12 is not compiled with Clang 12 against current Xcode libc++ headers.
- On Windows, compile the generated SWIG Python binding with MSVC `/bigobj` because the generated wrapper exceeds the default COFF section limit.
- On macOS, pass `LLVM_ENABLE_LIBCXX=ON` and pre-seed LLVM 12's atomics cache checks for the embedded LLVM build. Conda's macOS Clang toolchain uses libc++, LLVM 12's default `LLVM_ENABLE_LIBCXX=OFF` path runs stale libstdc++ version probes, and the old atomics probe can report a missing Linux-style `libatomic` even though Apple arm64 atomics are provided by the toolchain.

OptiX SDK packaging decisions:

- Package OptiX SDK 9.1.0 as a Linux and Windows `optix-dev` download stub for testing CUDA/OptiX consumers. Do not put NVIDIA header files or other `NVIDIA/optix-dev` repository contents in the conda artifact.
- The package should install only activation/download logic, minimal CMake package metadata, and local explanatory text. On activation it downloads the pinned `NVIDIA/optix-dev` GitHub archive, verifies the checksum, and installs headers into the active environment under the platform's normal prefix/library-prefix layout.
- Keep SDK samples, binaries, and broad redistribution out of the package unless Anders explicitly asks.

pbrt packaging decisions:

- Package pbrt 4.0.0 as `pbrt` and `pbrt-optix` application/tool packages.
- Use a pinned git commit from `mmp/pbrt-v4` with submodules instead of a tag archive, because upstream does not provide a `4.0.0`/`v4.0.0` tag or GitHub release.
- Install the command-line tools `pbrt`, `imgtool`, `pspec`, `plytool`, and `cyhair2pbrt` in both packages.
- Do not create `pbrt-lib` or `pbrt-dev` in the first pass because upstream installs only a static internal `pbrt_lib` and does not install headers or CMake package metadata for downstream consumers.
- Keep the default `pbrt` package CPU-only. Build `pbrt-optix` explicitly with `--variant pbrt_gpu=optix`; it depends on `optix-dev 9.1.*` and CUDA 13.2, supports `linux-64` and `win-64`, and is mutually exclusive with the CPU package because the command names overlap.
- Pass a fixed `PBRT_GPU_SHADER_MODEL=sm_75` for `pbrt-optix` so package builds do not require running pbrt's CUDA device probing executable on the build host.
- Disable `PBRT_BUILD_NATIVE_EXECUTABLE` for distributable packages so CI runner CPU flags are not baked into published binaries.
- Build Linux packages with GLFW's X11 backend only; keep Wayland disabled unless Anders asks for Wayland runtime support.
- Use external `openexr-dev`/`openexr-lib` and zlib where upstream CMake supports them; keep the rest of upstream's required `src/ext` submodules vendored for now.
