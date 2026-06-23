$ErrorActionPreference = "Stop"

$prefix = $env:PREFIX
if (-not $prefix) { throw "PREFIX is not set" }
$metaDir = Join-Path $prefix "conda-meta"
$recordPath = Get-ChildItem -LiteralPath $metaDir -Filter "optix-dev-9.1.0-*.json" |
  Sort-Object Name |
  Select-Object -Last 1
if (-not $recordPath) { throw "Could not find optix-dev conda-meta record" }

$record = Get-Content -LiteralPath $recordPath.FullName -Raw | ConvertFrom-Json
$files = [System.Collections.Generic.HashSet[string]]::new()
foreach ($file in @($record.files)) {
  if ($file) { [void]$files.Add([string]$file) }
}
if ($record.paths_data -and $record.paths_data.paths) {
  foreach ($entry in @($record.paths_data.paths)) {
    $path = $entry._path
    if (-not $path) { $path = $entry.path }
    if ($path) { [void]$files.Add([string]$path) }
  }
}

$allowedPayloadNames = @("README.txt", "optix-dev-activate.ps1")
$forbiddenNames = @(
  "optix.h",
  "optix_host.h",
  "optix_stubs.h",
  "optix_types.h",
  "optix_function_table_definition.h",
  "LICENSE.txt",
  "license_info.txt",
  "README.md"
)
foreach ($packageFile in $files) {
  $normalized = $packageFile.Replace("\", "/")
  $name = ($normalized -split "/")[-1]
  if ($normalized.StartsWith("include/") -or $normalized.StartsWith("Library/include/")) {
    throw "optix-dev package redistributes include payload: $normalized"
  }
  if ($normalized.StartsWith("opt/") -or $normalized.StartsWith("Library/opt/")) {
    throw "optix-dev package redistributes opt payload: $normalized"
  }
  if (($normalized.StartsWith("share/optix-dev/") -or $normalized.StartsWith("Library/share/optix-dev/")) -and $name -notin $allowedPayloadNames) {
    throw "optix-dev package redistributes non-stub share payload: $normalized"
  }
  if ($name -in $forbiddenNames) {
    throw "optix-dev package redistributes NVIDIA optix-dev payload: $normalized"
  }
  foreach ($suffix in @(".tar", ".tar.gz", ".tgz", ".zip")) {
    if ($name.EndsWith($suffix, [StringComparison]::OrdinalIgnoreCase)) {
      throw "optix-dev package redistributes an archive payload: $normalized"
    }
  }
}

$helper = Join-Path $prefix "Library\share\optix-dev\optix-dev-activate.ps1"
$helperText = Get-Content -LiteralPath $helper -Raw
foreach ($forbidden in @("Get-FileHash", "Expand-Archive")) {
  if ($helperText.Contains($forbidden)) {
    throw "Windows activation helper depends on module-backed cmdlet: $forbidden"
  }
}
foreach ($expected in @("System.Net.WebClient", "System.Security.Cryptography.SHA256", "System.IO.Compression.ZipFile")) {
  if (-not $helperText.Contains($expected)) {
    throw "Windows activation helper is missing self-contained API use: $expected"
  }
}

$tmp = Join-Path ([IO.Path]::GetTempPath()) ("optix-dev-stub-test." + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
try {
  $fakePrefix = Join-Path $tmp "prefix"
  $fakeLibraryPrefix = Join-Path $fakePrefix "Library"
  $fakeTemp = Join-Path $tmp "temp"
  New-Item -ItemType Directory -Path $fakePrefix, $fakeLibraryPrefix, $fakeTemp -Force | Out-Null

  $badArchive = Join-Path $tmp "not-optix-dev.zip"
  Set-Content -LiteralPath $badArchive -Value "not the optix-dev archive" -Encoding UTF8
  $archiveUri = ([Uri](Resolve-Path -LiteralPath $badArchive).Path).AbsoluteUri
  $replacement = '$optixDevArchiveUrl = "' + $archiveUri + '"'
  $helperLines = $helperText -split "\r?\n"
  $replacedArchiveUrl = $false
  for ($index = 0; $index -lt $helperLines.Count; $index++) {
    if ($helperLines[$index].StartsWith('$optixDevArchiveUrl = "')) {
      $helperLines[$index] = $replacement
      $replacedArchiveUrl = $true
      break
    }
  }
  if (-not $replacedArchiveUrl) {
    throw "Could not replace optix-dev archive URL in Windows activation helper"
  }
  $testHelperText = $helperLines -join [Environment]::NewLine
  $testHelper = Join-Path $tmp "optix-dev-activate.ps1"
  Set-Content -LiteralPath $testHelper -Value $testHelperText -Encoding UTF8

  $testHelperLiteral = $testHelper.Replace("'", "''")
  $wrapper = Join-Path $tmp "run-helper.ps1"
  Set-Content -LiteralPath $wrapper -Encoding UTF8 -Value @"
`$ErrorActionPreference = "Stop"
function Get-FileHash { throw "unexpected Get-FileHash invocation" }
function Expand-Archive { throw "unexpected Expand-Archive invocation" }
. '$testHelperLiteral'
"@

  $oldCondaPrefix = $env:CONDA_PREFIX
  $oldPrefix = $env:PREFIX
  $oldLibraryPrefix = $env:LIBRARY_PREFIX
  $oldTemp = $env:TEMP
  $oldTmp = $env:TMP
  $stdoutPath = Join-Path $tmp "run-helper.stdout.txt"
  $stderrPath = Join-Path $tmp "run-helper.stderr.txt"
  try {
    $env:CONDA_PREFIX = $fakePrefix
    $env:PREFIX = $fakePrefix
    $env:LIBRARY_PREFIX = $fakeLibraryPrefix
    $env:TEMP = $fakeTemp
    $env:TMP = $fakeTemp
    $process = Start-Process -FilePath "powershell" `
      -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $wrapper) `
      -NoNewWindow `
      -Wait `
      -PassThru `
      -RedirectStandardOutput $stdoutPath `
      -RedirectStandardError $stderrPath
    $exitCode = $process.ExitCode
  }
  finally {
    $env:CONDA_PREFIX = $oldCondaPrefix
    $env:PREFIX = $oldPrefix
    $env:LIBRARY_PREFIX = $oldLibraryPrefix
    $env:TEMP = $oldTemp
    $env:TMP = $oldTmp
  }

  $outputText = ""
  if (Test-Path $stdoutPath) { $outputText += Get-Content -LiteralPath $stdoutPath -Raw }
  if (Test-Path $stderrPath) { $outputText += Get-Content -LiteralPath $stderrPath -Raw }
  if ($exitCode -eq 0) {
    throw "Windows activation succeeded with a fake archive payload"
  }
  if (-not $outputText.Contains("checksum mismatch")) {
    throw "Windows activation did not fail at checksum verification:`n$outputText"
  }
  $installRoot = Join-Path $fakeLibraryPrefix "opt\optix-dev-9.1.0"
  if (Test-Path $installRoot) {
    throw "Windows activation left a partial install after checksum failure: $installRoot"
  }
  $leftovers = Get-ChildItem -LiteralPath $fakeTemp -Filter "optix-dev.*" -ErrorAction SilentlyContinue
  if ($leftovers) {
    throw "Windows activation left temporary directories after checksum failure: $($leftovers.FullName -join ', ')"
  }
}
finally {
  if (Test-Path $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
}
