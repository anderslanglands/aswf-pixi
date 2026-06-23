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

$expectedHash = "1899c049bfe523755eade3aa24aa3dc975eb40d022160536aa32841f69ce3d08"
$unexpectedHeaders = @(
  (Join-Path $env:PREFIX "include\optix.h"),
  (Join-Path $libraryPrefix "include\optix.h")
)
foreach ($unexpectedHeader in $unexpectedHeaders) {
  if (Test-Path $unexpectedHeader -PathType Leaf) {
    throw "OptiX headers should not be installed directly in a prefix include directory: $unexpectedHeader"
  }
}

$paths = @(
  (Join-Path $expectedRoot ".optix-dev-9.1.0-$expectedHash.installed"),
  $optixHeader,
  (Join-Path $env:OptiX_INCLUDE_DIR "optix_stubs.h"),
  (Join-Path $env:OptiX_INCLUDE_DIR "optix_function_table_definition.h"),
  (Join-Path $libraryPrefix "lib\cmake\OptiX\OptiXConfig.cmake")
)
foreach ($path in $paths) {
  if (-not (Test-Path $path -PathType Leaf)) {
    throw "Missing expected OptiX wrapper file: $path"
  }
}

$marker = Join-Path $expectedRoot ".optix-dev-9.1.0-$expectedHash.installed"
if ((Get-Content -LiteralPath $marker -Raw).Trim() -ne $expectedHash) {
  throw "OptiX marker does not contain the expected archive checksum: $marker"
}

$fullHeader = [IO.Path]::GetFullPath($optixHeader)
$fullLibraryPrefix = [IO.Path]::GetFullPath($libraryPrefix).TrimEnd('\') + '\'
if (-not $fullHeader.StartsWith($fullLibraryPrefix, [StringComparison]::OrdinalIgnoreCase)) {
  throw "Downloaded OptiX header is outside the active library prefix: $optixHeader"
}

$headerText = Get-Content -LiteralPath $optixHeader -Raw
$match = [regex]::Match($headerText, "(?m)^\s*#\s*define\s+OPTIX_VERSION\s+(\d+)\b")
if (-not $match.Success) {
  throw "optix.h does not define OPTIX_VERSION"
}
$version = [int]$match.Groups[1].Value
if ($version -lt 90100 -or $version -ge 90200) {
  throw "Expected OptiX 9.1.x headers, found OPTIX_VERSION=$version"
}

$config = Join-Path $libraryPrefix "lib\cmake\OptiX\OptiXConfig.cmake"
$configText = Get-Content -LiteralPath $config -Raw
foreach ($expected in @("OptiX::OptiX", "OptiX_INCLUDE_DIR", "opt/optix-dev-9.1.0", "9.1.0")) {
  if (-not $configText.Contains($expected)) {
    throw "OptiX CMake config is missing '$expected'"
  }
}
