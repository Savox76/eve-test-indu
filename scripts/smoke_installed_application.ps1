[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$InstallerPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$resolvedInstaller = (Resolve-Path -LiteralPath $InstallerPath).Path
$installRoot = Join-Path $env:LOCALAPPDATA 'New Eden Foundry'
$legacyRoot = Join-Path $env:LOCALAPPDATA 'io.github.savox76.newedenfoundry'
$legacyData = Join-Path $legacyRoot 'data'
$applicationPath = $null
$databasePath = Join-Path $installRoot 'data/foundry.sqlite3'
$migrationMarker = Join-Path $installRoot 'data/.program-storage-v1'
$lockedExport = Join-Path $legacyData 'exports/open-during-upgrade.csv'
$application = $null
$lockedStream = $null
$existingSidecarIds = @(Get-Process -Name 'foundry-sidecar' -ErrorAction SilentlyContinue | ForEach-Object Id)

try {
  New-Item -ItemType Directory -Path (Join-Path $legacyData 'backups') -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $legacyData 'exports') -Force | Out-Null

  $previousPythonPath = $env:PYTHONPATH
  $env:PYTHONPATH = Join-Path $repositoryRoot 'backend'
  $env:FOUNDRY_SMOKE_LEGACY_DATABASE = Join-Path $legacyData 'foundry.sqlite3'
  try {
    @'
import os
from pathlib import Path

from new_eden_foundry_backend.database import initialize_database

database = Path(os.environ["FOUNDRY_SMOKE_LEGACY_DATABASE"])
initialize_database(database, backup_directory=database.parent / "backups")
'@ | python -
    if ($LASTEXITCODE -ne 0) {
      throw 'Could not seed the previous-version database.'
    }
  }
  finally {
    $env:PYTHONPATH = $previousPythonPath
    Remove-Item Env:FOUNDRY_SMOKE_LEGACY_DATABASE -ErrorAction SilentlyContinue
  }

  $lockedStream = [IO.File]::Open(
    $lockedExport,
    [IO.FileMode]::OpenOrCreate,
    [IO.FileAccess]::ReadWrite,
    [IO.FileShare]::None
  )
  $lockedBytes = [Text.Encoding]::UTF8.GetBytes("locked during upgrade`n")
  $lockedStream.Write($lockedBytes, 0, $lockedBytes.Length)
  $lockedStream.Flush()

  $installer = Start-Process -FilePath $resolvedInstaller -ArgumentList '/S' -PassThru -Wait
  if ($installer.ExitCode -ne 0) {
    throw "Silent installer exited with code $($installer.ExitCode)."
  }
  $applicationPath = Get-ChildItem -LiteralPath $installRoot -Filter '*.exe' -File |
    Where-Object { $_.Name -notin @('foundry-sidecar.exe', 'uninstall.exe') } |
    Select-Object -First 1 -ExpandProperty FullName
  if (-not $applicationPath) {
    throw "Installed application not found below: $installRoot"
  }

  $application = Start-Process -FilePath $applicationPath -WorkingDirectory $installRoot -PassThru
  $deadline = [DateTime]::UtcNow.AddSeconds(45)
  $sidecar = $null
  do {
    Start-Sleep -Milliseconds 250
    $application.Refresh()
    if ($application.HasExited) {
      throw "Installed application exited with code $($application.ExitCode)."
    }
    $sidecar = Get-Process -Name 'foundry-sidecar' -ErrorAction SilentlyContinue |
      Where-Object { $_.Id -notin $existingSidecarIds } |
      Select-Object -First 1
  } until (
    (
      $sidecar -and
      (Test-Path -LiteralPath $databasePath -PathType Leaf) -and
      (Test-Path -LiteralPath $migrationMarker -PathType Leaf)
    ) -or ([DateTime]::UtcNow -ge $deadline)
  )

  if (-not $sidecar) {
    throw 'The installed sidecar did not remain running.'
  }
  if (-not (Test-Path -LiteralPath $databasePath -PathType Leaf)) {
    throw 'The previous-version database was not migrated beside the installed executable.'
  }
  if (-not (Test-Path -LiteralPath $migrationMarker -PathType Leaf)) {
    throw 'The program-folder migration marker was not created.'
  }
  Start-Sleep -Seconds 2
  $sidecar.Refresh()
  if ($sidecar.HasExited) {
    throw 'The installed sidecar exited after startup.'
  }

  Write-Output 'Installed application and sidecar started with a locked non-critical legacy file.'
}
finally {
  if ($application -and -not $application.HasExited) {
    Stop-Process -Id $application.Id -Force -ErrorAction SilentlyContinue
  }
  Get-Process -Name 'foundry-sidecar' -ErrorAction SilentlyContinue |
    Where-Object { $_.Id -notin $existingSidecarIds } |
    Stop-Process -Force -ErrorAction SilentlyContinue
  if ($lockedStream) {
    $lockedStream.Dispose()
  }
}
