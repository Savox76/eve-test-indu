[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^[0-9A-Za-z.-]+$')]
  [string]$Version,

  [string]$BundleDirectory = "src-tauri/target/release/bundle"
)

$ErrorActionPreference = "Stop"
$resolvedBundle = (Resolve-Path -LiteralPath $BundleDirectory).Path
$nsisDirectory = Join-Path $resolvedBundle "nsis"
$installers = @(Get-ChildItem -LiteralPath $nsisDirectory -Filter "*.exe" -File)
if ($installers.Count -ne 1) {
  throw "Expected exactly one NSIS installer, found $($installers.Count)."
}

$portablePath = Join-Path `
  $resolvedBundle `
  "New.Eden.Foundry_${Version}_x64-portable.zip"
if (-not (Test-Path -LiteralPath $portablePath -PathType Leaf)) {
  throw "Missing portable package: $portablePath"
}

$installerSource = $installers[0]
$publicInstallerPath = Join-Path `
  $nsisDirectory `
  "New.Eden.Foundry_${Version}_x64-setup.exe"
if (-not ($installerSource.FullName.Equals(
      $publicInstallerPath,
      [StringComparison]::OrdinalIgnoreCase
    ))) {
  if (Test-Path -LiteralPath $publicInstallerPath) {
    throw "The public installer path already exists: $publicInstallerPath"
  }
  Move-Item -LiteralPath $installerSource.FullName -Destination $publicInstallerPath
}

$packages = @(
  (Get-Item -LiteralPath $publicInstallerPath),
  (Get-Item -LiteralPath $portablePath)
)
$releaseFiles = @()
foreach ($package in $packages) {
  $checksumPath = "$($package.FullName).sha256"
  $checksum = (Get-FileHash -Algorithm SHA256 $package.FullName).Hash.ToLowerInvariant()
  "$checksum  $($package.Name)" | Set-Content -Encoding utf8NoBOM $checksumPath
  $releaseFiles += $package.FullName
  $releaseFiles += $checksumPath
}

$releaseFiles
