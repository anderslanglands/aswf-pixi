if(NOT DEFINED OPTIX_STUB_PREFIX)
  message(FATAL_ERROR "OPTIX_STUB_PREFIX is required")
endif()
if(NOT DEFINED OPTIX_STUB_LIBRARY_PREFIX)
  set(OPTIX_STUB_LIBRARY_PREFIX "${OPTIX_STUB_PREFIX}")
endif()

set(_optix_activation_dir "${OPTIX_STUB_PREFIX}/etc/conda/activate.d")
set(_optix_cmake_dir "${OPTIX_STUB_LIBRARY_PREFIX}/lib/cmake/OptiX")
set(_optix_share_dir "${OPTIX_STUB_LIBRARY_PREFIX}/share/optix-dev")
file(MAKE_DIRECTORY "${_optix_activation_dir}" "${_optix_cmake_dir}" "${_optix_share_dir}")

if(WIN32)
  file(WRITE "${_optix_share_dir}/optix-dev-activate.ps1" [=[
$ErrorActionPreference = "Stop"
$optixDevVersion = "9.1.0"
$optixDevTag = "v9.1.0"
$optixDevArchiveSha256 = "1899c049bfe523755eade3aa24aa3dc975eb40d022160536aa32841f69ce3d08"
$optixDevArchiveUrl = "https://github.com/NVIDIA/optix-dev/archive/refs/tags/$optixDevTag.zip"
$optixDevPrefix = $env:CONDA_PREFIX
if (-not $optixDevPrefix) { $optixDevPrefix = $env:PREFIX }
if (-not $optixDevPrefix) { throw "CONDA_PREFIX is not set" }
$optixDevLibraryPrefix = $env:LIBRARY_PREFIX
if (-not $optixDevLibraryPrefix) {
  $candidate = Join-Path $optixDevPrefix "Library"
  if (Test-Path $candidate) { $optixDevLibraryPrefix = $candidate } else { $optixDevLibraryPrefix = $optixDevPrefix }
}
$optixDevRoot = Join-Path $optixDevLibraryPrefix "opt\optix-dev-$optixDevVersion"
$optixDevIncludeDir = Join-Path $optixDevRoot "include"
$optixDevMarker = Join-Path $optixDevRoot ".optix-dev-$optixDevVersion-$optixDevArchiveSha256.installed"

if ((-not (Test-Path $optixDevMarker -PathType Leaf)) -or (-not (Test-Path (Join-Path $optixDevIncludeDir "optix.h") -PathType Leaf))) {
  $optixDevTmpRoot = Join-Path ([IO.Path]::GetTempPath()) ("optix-dev." + [Guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Path $optixDevTmpRoot -Force | Out-Null
  try {
    $optixDevArchive = Join-Path $optixDevTmpRoot "optix-dev-$optixDevVersion.zip"
    $optixDevExtract = Join-Path $optixDevTmpRoot "extract"
    $optixDevStage = Join-Path $optixDevTmpRoot "optix-dev-$optixDevVersion"
    New-Item -ItemType Directory -Path $optixDevExtract, $optixDevStage -Force | Out-Null

    Write-Host "optix-dev activation: downloading $optixDevArchiveUrl"
    try {
      [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    }
    catch {}
    $optixDevWebClient = [System.Net.WebClient]::new()
    $optixDevWebClient.Headers.Add("User-Agent", "aswf-pixi-optix-dev-activation")
    try {
      $optixDevWebClient.DownloadFile($optixDevArchiveUrl, $optixDevArchive)
    }
    finally {
      $optixDevWebClient.Dispose()
    }

    $optixDevSha256 = [System.Security.Cryptography.SHA256]::Create()
    $optixDevStream = [System.IO.File]::OpenRead($optixDevArchive)
    try {
      $optixDevActualSha256 = [System.BitConverter]::ToString($optixDevSha256.ComputeHash($optixDevStream)).Replace("-", "").ToLowerInvariant()
    }
    finally {
      $optixDevStream.Dispose()
      $optixDevSha256.Dispose()
    }
    if ($optixDevActualSha256 -ne $optixDevArchiveSha256) {
      throw "checksum mismatch for ${optixDevArchiveUrl}: expected ${optixDevArchiveSha256}, got ${optixDevActualSha256}"
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($optixDevArchive, $optixDevExtract)

    $optixDevSourceRoot = Join-Path $optixDevExtract "optix-dev-$optixDevVersion"
    if (-not (Test-Path (Join-Path $optixDevSourceRoot "include\optix.h") -PathType Leaf)) {
      throw "downloaded archive does not contain include/optix.h"
    }

    Copy-Item -Recurse -Path (Join-Path $optixDevSourceRoot "include") -Destination (Join-Path $optixDevStage "include")
    foreach ($optixDevDoc in @("LICENSE.txt", "license_info.txt", "README.md")) {
      $sourceDoc = Join-Path $optixDevSourceRoot $optixDevDoc
      if (Test-Path $sourceDoc -PathType Leaf) { Copy-Item -Path $sourceDoc -Destination (Join-Path $optixDevStage $optixDevDoc) }
    }
    Set-Content -Path (Join-Path $optixDevStage ".optix-dev-$optixDevVersion-$optixDevArchiveSha256.installed") -Value $optixDevArchiveSha256 -NoNewline

    New-Item -ItemType Directory -Path (Split-Path -Parent $optixDevRoot) -Force | Out-Null
    if (Test-Path $optixDevRoot) { Remove-Item -Recurse -Force $optixDevRoot }
    Move-Item -Path $optixDevStage -Destination $optixDevRoot
  }
  finally {
    if (Test-Path $optixDevTmpRoot) { Remove-Item -Recurse -Force $optixDevTmpRoot }
  }
}
]=])

  file(WRITE "${_optix_activation_dir}/optix-dev.bat" [=[@echo off
set "optix_dev_prefix=%CONDA_PREFIX%"
if "%optix_dev_prefix%"=="" set "optix_dev_prefix=%PREFIX%"
if "%optix_dev_prefix%"=="" (
  echo optix-dev activation: CONDA_PREFIX is not set 1>&2
  exit /b 1
)
set "optix_dev_library_prefix=%LIBRARY_PREFIX%"
if "%optix_dev_library_prefix%"=="" set "optix_dev_library_prefix=%optix_dev_prefix%\Library"
if not exist "%optix_dev_library_prefix%" set "optix_dev_library_prefix=%optix_dev_prefix%"
set "optix_dev_helper=%optix_dev_library_prefix%\share\optix-dev\optix-dev-activate.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%optix_dev_helper%"
if errorlevel 1 exit /b 1
set "OptiX_ROOT=%optix_dev_library_prefix%\opt\optix-dev-9.1.0"
set "OPTIX_ROOT_DIR=%OptiX_ROOT%"
set "OptiX_INCLUDE_DIR=%OptiX_ROOT%\include"
set "OPTIX_INCLUDE_DIR=%OptiX_INCLUDE_DIR%"
set "OPTIX_INCLUDES=%OptiX_INCLUDE_DIR%"
]=])

  file(WRITE "${_optix_activation_dir}/optix-dev.ps1" [=[$optixDevPrefix = $env:CONDA_PREFIX
if (-not $optixDevPrefix) { $optixDevPrefix = $env:PREFIX }
if (-not $optixDevPrefix) { throw "optix-dev activation: CONDA_PREFIX is not set" }
$optixDevLibraryPrefix = $env:LIBRARY_PREFIX
if (-not $optixDevLibraryPrefix) {
  $candidate = Join-Path $optixDevPrefix "Library"
  if (Test-Path $candidate) { $optixDevLibraryPrefix = $candidate } else { $optixDevLibraryPrefix = $optixDevPrefix }
}
$optixDevHelper = Join-Path $optixDevLibraryPrefix "share\optix-dev\optix-dev-activate.ps1"
& $optixDevHelper
if (-not $?) { throw "optix-dev activation failed" }
$env:OptiX_ROOT = Join-Path $optixDevLibraryPrefix "opt\optix-dev-9.1.0"
$env:OPTIX_ROOT_DIR = $env:OptiX_ROOT
$env:OptiX_INCLUDE_DIR = Join-Path $env:OptiX_ROOT "include"
$env:OPTIX_INCLUDE_DIR = $env:OptiX_INCLUDE_DIR
$env:OPTIX_INCLUDES = $env:OptiX_INCLUDE_DIR
]=])
else()
  file(WRITE "${_optix_activation_dir}/optix-dev.sh" [=[#!/usr/bin/env sh
# Download NVIDIA OptiX headers on activation. The conda package itself is
# intentionally a stub and does not redistribute the optix-dev repository.

optix_dev_version="9.1.0"
optix_dev_tag="v9.1.0"
optix_dev_archive_sha256="3a29b2254107fdfbb5e6bbad3ec154dd682149121f61e9c406607ac7b52a6ba6"
optix_dev_archive_url="https://github.com/NVIDIA/optix-dev/archive/refs/tags/${optix_dev_tag}.tar.gz"
optix_dev_prefix="${CONDA_PREFIX:-${PREFIX:-}}"
optix_dev_tmp_root=""

optix_dev_error() {
  echo "optix-dev activation: $*" >&2
  if [ -n "${optix_dev_tmp_root:-}" ] && [ -d "${optix_dev_tmp_root}" ]; then
    rm -rf "${optix_dev_tmp_root}"
  fi
}

if [ -z "${optix_dev_prefix}" ]; then
  optix_dev_error "CONDA_PREFIX is not set"
  return 1 2>/dev/null || exit 1
fi

optix_dev_root="${optix_dev_prefix}/opt/optix-dev-${optix_dev_version}"
optix_dev_include_dir="${optix_dev_root}/include"
optix_dev_marker="${optix_dev_root}/.optix-dev-${optix_dev_version}-${optix_dev_archive_sha256}.installed"

if [ ! -f "${optix_dev_marker}" ] || [ ! -f "${optix_dev_include_dir}/optix.h" ]; then
  if ! command -v curl >/dev/null 2>&1; then
    optix_dev_error "curl is required to download ${optix_dev_archive_url}"
    return 1 2>/dev/null || exit 1
  fi
  if ! command -v sha256sum >/dev/null 2>&1; then
    optix_dev_error "sha256sum is required to verify ${optix_dev_archive_url}"
    return 1 2>/dev/null || exit 1
  fi
  if ! command -v tar >/dev/null 2>&1; then
    optix_dev_error "tar is required to unpack ${optix_dev_archive_url}"
    return 1 2>/dev/null || exit 1
  fi
  if ! command -v mktemp >/dev/null 2>&1; then
    optix_dev_error "mktemp is required to unpack ${optix_dev_archive_url}"
    return 1 2>/dev/null || exit 1
  fi

  if ! optix_dev_tmp_root="$(mktemp -d "${TMPDIR:-/tmp}/optix-dev.XXXXXX")"; then
    optix_dev_error "failed to create a temporary directory"
    return 1 2>/dev/null || exit 1
  fi
  optix_dev_archive="${optix_dev_tmp_root}/optix-dev-${optix_dev_version}.tar.gz"
  optix_dev_extract="${optix_dev_tmp_root}/extract"
  optix_dev_stage="${optix_dev_tmp_root}/optix-dev-${optix_dev_version}"
  if ! mkdir -p "${optix_dev_extract}" "${optix_dev_stage}"; then
    optix_dev_error "failed to create temporary extraction directories"
    return 1 2>/dev/null || exit 1
  fi

  echo "optix-dev activation: downloading ${optix_dev_archive_url}" >&2
  if ! curl --location --fail --show-error --retry 3 --output "${optix_dev_archive}" "${optix_dev_archive_url}"; then
    optix_dev_error "failed to download ${optix_dev_archive_url}"
    return 1 2>/dev/null || exit 1
  fi

  optix_dev_actual_sha256="$(sha256sum "${optix_dev_archive}")"
  optix_dev_actual_sha256="${optix_dev_actual_sha256%% *}"
  if [ "${optix_dev_actual_sha256}" != "${optix_dev_archive_sha256}" ]; then
    optix_dev_error "checksum mismatch for ${optix_dev_archive_url}: expected ${optix_dev_archive_sha256}, got ${optix_dev_actual_sha256}"
    return 1 2>/dev/null || exit 1
  fi

  if ! tar -xzf "${optix_dev_archive}" -C "${optix_dev_extract}"; then
    optix_dev_error "failed to unpack ${optix_dev_archive_url}"
    return 1 2>/dev/null || exit 1
  fi

  optix_dev_source_root="${optix_dev_extract}/optix-dev-${optix_dev_version}"
  if [ ! -f "${optix_dev_source_root}/include/optix.h" ]; then
    optix_dev_error "downloaded archive does not contain include/optix.h"
    return 1 2>/dev/null || exit 1
  fi

  if ! cp -R "${optix_dev_source_root}/include" "${optix_dev_stage}/include"; then
    optix_dev_error "failed to stage OptiX headers"
    return 1 2>/dev/null || exit 1
  fi
  for optix_dev_doc in LICENSE.txt license_info.txt README.md; do
    if [ -f "${optix_dev_source_root}/${optix_dev_doc}" ]; then
      if ! cp "${optix_dev_source_root}/${optix_dev_doc}" "${optix_dev_stage}/${optix_dev_doc}"; then
        optix_dev_error "failed to stage ${optix_dev_doc}"
        return 1 2>/dev/null || exit 1
      fi
    fi
  done
  if ! printf '%s\n' "${optix_dev_archive_sha256}" > "${optix_dev_stage}/.optix-dev-${optix_dev_version}-${optix_dev_archive_sha256}.installed"; then
    optix_dev_error "failed to write installation marker"
    return 1 2>/dev/null || exit 1
  fi

  if ! mkdir -p "$(dirname "${optix_dev_root}")"; then
    optix_dev_error "failed to create ${optix_dev_root%/*}"
    return 1 2>/dev/null || exit 1
  fi
  if ! rm -rf "${optix_dev_root}"; then
    optix_dev_error "failed to remove previous ${optix_dev_root}"
    return 1 2>/dev/null || exit 1
  fi
  if ! mv "${optix_dev_stage}" "${optix_dev_root}"; then
    optix_dev_error "failed to install headers into ${optix_dev_root}"
    return 1 2>/dev/null || exit 1
  fi
  if ! rm -rf "${optix_dev_tmp_root}"; then
    optix_dev_error "failed to clean ${optix_dev_tmp_root}"
    return 1 2>/dev/null || exit 1
  fi
  optix_dev_tmp_root=""
fi

export OptiX_ROOT="${optix_dev_root}"
export OPTIX_ROOT_DIR="${optix_dev_root}"
export OptiX_INCLUDE_DIR="${optix_dev_include_dir}"
export OPTIX_INCLUDE_DIR="${optix_dev_include_dir}"
export OPTIX_INCLUDES="${optix_dev_include_dir}"

unset optix_dev_version optix_dev_tag optix_dev_archive_sha256 optix_dev_archive_url
unset optix_dev_prefix optix_dev_root optix_dev_include_dir optix_dev_marker
unset optix_dev_tmp_root optix_dev_archive optix_dev_extract optix_dev_stage
unset optix_dev_actual_sha256 optix_dev_source_root optix_dev_doc
unset -f optix_dev_error 2>/dev/null || true
]=])
endif()

file(WRITE "${_optix_cmake_dir}/OptiXConfig.cmake" [=[include_guard()

get_filename_component(_optix_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
set(OptiX_ROOT "${_optix_prefix}/opt/optix-dev-9.1.0")
set(OPTIX_ROOT_DIR "${OptiX_ROOT}")
set(OptiX_INCLUDE_DIR "${OptiX_ROOT}/include")
set(OPTIX_INCLUDE_DIR "${OptiX_INCLUDE_DIR}")
set(OPTIX_INCLUDES "${OptiX_INCLUDE_DIR}")
set(OptiX_VERSION "9.1.0")

if(NOT EXISTS "${OptiX_INCLUDE_DIR}/optix.h")
  message(FATAL_ERROR "OptiX headers are not installed in ${OptiX_INCLUDE_DIR}. Activate the conda environment to download them from https://github.com/NVIDIA/optix-dev.")
endif()

set(_optix_interface_include_dirs "${OptiX_INCLUDE_DIR}")
if(EXISTS "${_optix_prefix}/targets/x86_64-linux/include/cuda.h")
  list(APPEND _optix_interface_include_dirs "${_optix_prefix}/targets/x86_64-linux/include")
elseif(EXISTS "${_optix_prefix}/include/cuda.h")
  list(APPEND _optix_interface_include_dirs "${_optix_prefix}/include")
endif()

set(OptiX_FOUND TRUE)
if(NOT TARGET OptiX::OptiX)
  add_library(OptiX::OptiX INTERFACE IMPORTED)
  set_target_properties(OptiX::OptiX PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${_optix_interface_include_dirs}"
  )
endif()
]=])

file(WRITE "${_optix_cmake_dir}/OptiXConfigVersion.cmake" [=[set(PACKAGE_VERSION "9.1.0")
if(PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)
  set(PACKAGE_VERSION_EXACT TRUE)
  set(PACKAGE_VERSION_COMPATIBLE TRUE)
elseif(PACKAGE_FIND_VERSION VERSION_LESS PACKAGE_VERSION)
  set(PACKAGE_VERSION_COMPATIBLE TRUE)
else()
  set(PACKAGE_VERSION_COMPATIBLE FALSE)
endif()
]=])

file(WRITE "${_optix_share_dir}/README.txt" [=[optix-dev is a download stub package. It does not redistribute NVIDIA's
optix-dev repository contents. On environment activation, it downloads the
requested version from https://github.com/NVIDIA/optix-dev, verifies the
archive checksum, and installs the headers into the active environment.
]=])
