$ErrorActionPreference = "Stop"
. "$env:PREFIX\etc\conda\activate.d\optix-dev.ps1"
if (-not $env:OptiX_INCLUDE_DIR) { throw "OptiX_INCLUDE_DIR was not set by PowerShell activation" }
$optixHeader = Join-Path $env:OptiX_INCLUDE_DIR "optix.h"
if (-not (Test-Path $optixHeader -PathType Leaf)) { throw "PowerShell activation did not expose $optixHeader" }
if (-not $env:OptiX_ROOT) { throw "OptiX_ROOT was not set by PowerShell activation" }
$libraryPrefix = $env:LIBRARY_PREFIX
if (-not $libraryPrefix) { $libraryPrefix = Join-Path $env:PREFIX "Library" }
$expectedRoot = Join-Path $libraryPrefix "opt\optix-dev-9.1.0"
if ([IO.Path]::GetFullPath($env:OptiX_ROOT) -ne [IO.Path]::GetFullPath($expectedRoot)) {
  throw "PowerShell activation set OptiX_ROOT to '$env:OptiX_ROOT', expected '$expectedRoot'"
}
