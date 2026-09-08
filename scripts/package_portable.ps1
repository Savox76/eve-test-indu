[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^[0-9A-Za-z][0-9A-Za-z.+-]*$')]
  [string]$Version,

  [ValidateSet('x64', 'arm64')]
  [string]$Architecture = 'x64',

  [string]$TargetDirectory,

  [string]$OutputDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($TargetDirectory)) {
  $TargetDirectory = Join-Path $repositoryRoot 'src-tauri/target/release'
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
  $OutputDirectory = Join-Path $TargetDirectory 'bundle'
}

$sourceExecutable = Join-Path $TargetDirectory 'new-eden-foundry.exe'
$sourceReadme = Join-Path $repositoryRoot 'docs/portable/README-DE-EN.txt'
if (-not (Test-Path -LiteralPath $sourceExecutable -PathType Leaf)) {
  throw "Built application executable not found: $sourceExecutable"
}
if (-not (Test-Path -LiteralPath $sourceReadme -PathType Leaf)) {
  throw "Portable usage notes not found: $sourceReadme"
}

$archiveBaseName = "New.Eden.Foundry_${Version}_${Architecture}-portable"
$archivePath = Join-Path $OutputDirectory "$archiveBaseName.zip"
$packageFolderName = "New Eden Foundry $Version"
$stagingRoot = Join-Path ([IO.Path]::GetTempPath()) "$archiveBaseName-$([Guid]::NewGuid().ToString('N'))"
$packageRoot = Join-Path $stagingRoot $packageFolderName

try {
  New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
  New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
  Copy-Item -LiteralPath $sourceExecutable -Destination (Join-Path $packageRoot 'New Eden Foundry.exe')
  Copy-Item -LiteralPath $sourceReadme -Destination (Join-Path $packageRoot 'PORTABLE-README-DE-EN.txt')

  if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
  }

  Add-Type -AssemblyName System.IO.Compression.FileSystem
  [IO.Compression.ZipFile]::CreateFromDirectory(
    $stagingRoot,
    $archivePath,
    [IO.Compression.CompressionLevel]::Optimal,
    $false
  )

  $archive = [IO.Compression.ZipFile]::OpenRead($archivePath)
  try {
    $folder = "$packageFolderName/"
    $entries = @($archive.Entries | ForEach-Object { $_.FullName.Replace('\', '/') })
    foreach ($expected in @(
      "${folder}New Eden Foundry.exe",
      "${folder}PORTABLE-README-DE-EN.txt"
    )) {
      if ($expected -notin $entries) {
        throw "Portable package is missing: $expected"
      }
    }
  }
  finally {
    $archive.Dispose()
  }

  Write-Output $archivePath
}
finally {
  if (Test-Path -LiteralPath $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
  }
}
