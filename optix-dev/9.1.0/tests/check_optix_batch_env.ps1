$ErrorActionPreference = "Stop"

$prefix = $env:PREFIX
if (-not $prefix) { throw "PREFIX is not set" }
$libraryPrefix = $env:LIBRARY_PREFIX
if (-not $libraryPrefix) { $libraryPrefix = Join-Path $prefix "Library" }
$expectedRoot = Join-Path $libraryPrefix "opt\optix-dev-9.1.0"
$expectedInclude = Join-Path $expectedRoot "include"

$expectedEnv = @(
  @("OptiX_ROOT", $expectedRoot),
  @("OPTIX_ROOT_DIR", $expectedRoot),
  @("OptiX_INCLUDE_DIR", $expectedInclude),
  @("OPTIX_INCLUDE_DIR", $expectedInclude),
  @("OPTIX_INCLUDES", $expectedInclude)
)

foreach ($entry in $expectedEnv) {
  $name = $entry[0]
  $expected = $entry[1]
  $actual = [Environment]::GetEnvironmentVariable($name)
  if (-not $actual) {
    throw "$name was not set by batch activation"
  }
  if ([IO.Path]::GetFullPath($actual) -ne [IO.Path]::GetFullPath($expected)) {
    throw "Batch activation set $name to '$actual', expected '$expected'"
  }
}

$optixHeader = Join-Path $env:OptiX_INCLUDE_DIR "optix.h"
if (-not (Test-Path $optixHeader -PathType Leaf)) {
  throw "Batch activation did not expose $optixHeader"
}
