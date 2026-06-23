$ErrorActionPreference = "Stop"

function Test-PathWithin {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Parent
  )
  $fullPath = [IO.Path]::GetFullPath($Path)
  $fullParent = [IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
  if (-not $fullPath.StartsWith($fullParent, [StringComparison]::OrdinalIgnoreCase)) {
    throw "refusing to remove $Path; it is outside $Parent"
  }
}

function Remove-TreeWithRetry {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return }

  $delayMs = 250
  $lastError = $null
  for ($attempt = 0; $attempt -lt 8; $attempt++) {
    try {
      Get-ChildItem -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue |
        ForEach-Object { $_.Attributes = "Normal" }
      Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
      return
    }
    catch {
      $lastError = $_
      Start-Sleep -Milliseconds $delayMs
      $delayMs = [Math]::Min($delayMs * 2, 2000)
    }
  }

  throw "failed to remove ${Path}: $lastError"
}

$prefix = $env:PREFIX
if (-not $prefix) { throw "PREFIX is not set" }
$libraryPrefix = $env:LIBRARY_PREFIX
if (-not $libraryPrefix) { $libraryPrefix = Join-Path $prefix "Library" }
$tempRoot = [IO.Path]::GetTempPath()
$buildDir = Join-Path $tempRoot ("optix-dev-cmake-" + [Guid]::NewGuid().ToString("N"))
$optixRoot = Join-Path $libraryPrefix "opt\optix-dev-9.1.0"

New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
Test-PathWithin -Path $buildDir -Parent $tempRoot
Test-PathWithin -Path $optixRoot -Parent (Join-Path $libraryPrefix "opt")

$testError = $null
try {
  & cmake -S tests -B $buildDir -GNinja -DCMAKE_BUILD_TYPE=Release "-DCMAKE_PREFIX_PATH=$libraryPrefix"
  if ($LASTEXITCODE -ne 0) { throw "cmake configure failed with exit code $LASTEXITCODE" }
  & cmake --build $buildDir --config Release
  if ($LASTEXITCODE -ne 0) { throw "cmake build failed with exit code $LASTEXITCODE" }
  & (Join-Path $buildDir "optix_consumer.exe")
  if ($LASTEXITCODE -ne 0) { throw "optix_consumer.exe failed with exit code $LASTEXITCODE" }
}
catch {
  $testError = $_
}
finally {
  $cleanupErrors = @()
  foreach ($cleanupPath in @($buildDir, $optixRoot)) {
    try {
      Remove-TreeWithRetry -Path $cleanupPath
    }
    catch {
      $cleanupErrors += $_
    }
  }

  if ($testError) {
    if ($cleanupErrors.Count -gt 0) {
      [Console]::Error.WriteLine("cleanup failed after consumer test failure:")
      foreach ($cleanupError in $cleanupErrors) {
        [Console]::Error.WriteLine("  $cleanupError")
      }
    }
    throw $testError
  }

  if ($cleanupErrors.Count -gt 0) {
    throw ($cleanupErrors -join "`n")
  }
}
