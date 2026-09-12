[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$InstallerPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Wait-InstalledApplicationReady {
  param(
    [Parameter(Mandatory = $true)]
    [System.Diagnostics.Process]$Application,
    [Parameter(Mandatory = $true)]
    [AllowEmptyCollection()]
    [int[]]$IgnoredSidecarIds,
    [Parameter(Mandatory = $true)]
    [string]$DatabasePath,
    [Parameter(Mandatory = $true)]
    [string]$MigrationMarker
  )

  $deadline = [DateTime]::UtcNow.AddSeconds(45)
  $sidecar = $null
  do {
    Start-Sleep -Milliseconds 250
    $Application.Refresh()
    if ($Application.HasExited) {
      throw "Installed application exited with code $($Application.ExitCode)."
    }
    $sidecar = Get-Process -Name 'foundry-sidecar' -ErrorAction SilentlyContinue |
      Where-Object { $_.Id -notin $IgnoredSidecarIds } |
      Select-Object -First 1
  } until (
    (
      $sidecar -and
      (Test-Path -LiteralPath $DatabasePath -PathType Leaf) -and
      (Test-Path -LiteralPath $MigrationMarker -PathType Leaf)
    ) -or ([DateTime]::UtcNow -ge $deadline)
  )

  if (-not $sidecar) {
    throw 'The installed sidecar did not remain running.'
  }
  Start-Sleep -Seconds 2
  $sidecar.Refresh()
  if ($sidecar.HasExited) {
    throw 'The installed sidecar exited after startup.'
  }
  return $sidecar
}

function Close-InstalledApplicationCleanly {
  param(
    [Parameter(Mandatory = $true)]
    [System.Diagnostics.Process]$Application,
    [Parameter(Mandatory = $true)]
    [AllowEmptyCollection()]
    [int[]]$IgnoredSidecarIds
  )

  $windowDeadline = [DateTime]::UtcNow.AddSeconds(15)
  do {
    $Application.Refresh()
    if ($Application.HasExited) {
      throw 'Installed application exited before its window could be closed cleanly.'
    }
    if ($Application.MainWindowHandle -ne 0) {
      break
    }
    Start-Sleep -Milliseconds 200
  } until ([DateTime]::UtcNow -ge $windowDeadline)

  if ($Application.MainWindowHandle -eq 0 -or -not $Application.CloseMainWindow()) {
    throw 'The installed application did not expose a closable main window.'
  }
  if (-not $Application.WaitForExit(20000)) {
    throw 'The installed application did not exit after its main window was closed.'
  }

  $sidecarDeadline = [DateTime]::UtcNow.AddSeconds(15)
  do {
    $remainingSidecars = @(
      Get-Process -Name 'foundry-sidecar' -ErrorAction SilentlyContinue |
        Where-Object { $_.Id -notin $IgnoredSidecarIds }
    )
    if ($remainingSidecars.Count -eq 0) {
      return
    }
    Start-Sleep -Milliseconds 200
  } until ([DateTime]::UtcNow -ge $sidecarDeadline)
  throw 'The installed sidecar remained after the application was closed.'
}

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
$secondApplication = $null
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

from contextlib import closing
from new_eden_foundry_backend.database import connect_database, initialize_database

database = Path(os.environ["FOUNDRY_SMOKE_LEGACY_DATABASE"])
initialize_database(database, backup_directory=database.parent / "backups")
with closing(connect_database(database)) as connection:
    connection.execute(
        "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
        ("installed-restart-smoke", "preserved"),
    )
    connection.commit()
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
  $sidecarSupport = Join-Path $installRoot 'foundry-sidecar-lib'
  if (-not (Test-Path -LiteralPath $sidecarSupport -PathType Container)) {
    throw "Installed sidecar support directory not found: $sidecarSupport"
  }
  if (-not (Get-ChildItem -LiteralPath $sidecarSupport -File -Recurse | Select-Object -First 1)) {
    throw "Installed sidecar support directory is empty: $sidecarSupport"
  }

  $application = Start-Process -FilePath $applicationPath -WorkingDirectory $installRoot -PassThru
  $firstSidecar = Wait-InstalledApplicationReady `
    -Application $application `
    -IgnoredSidecarIds $existingSidecarIds `
    -DatabasePath $databasePath `
    -MigrationMarker $migrationMarker
  if (-not (Test-Path -LiteralPath $databasePath -PathType Leaf)) {
    throw 'The previous-version database was not migrated beside the installed executable.'
  }
  if (-not (Test-Path -LiteralPath $migrationMarker -PathType Leaf)) {
    throw 'The program-folder migration marker was not created.'
  }

  Close-InstalledApplicationCleanly `
    -Application $application `
    -IgnoredSidecarIds $existingSidecarIds
  $application = $null

  $secondApplication = Start-Process -FilePath $applicationPath -WorkingDirectory $installRoot -PassThru
  $secondSidecar = Wait-InstalledApplicationReady `
    -Application $secondApplication `
    -IgnoredSidecarIds $existingSidecarIds `
    -DatabasePath $databasePath `
    -MigrationMarker $migrationMarker
  if ($secondSidecar.Id -eq $firstSidecar.Id) {
    throw 'The second application start reused a stale sidecar process.'
  }

  $env:FOUNDRY_SMOKE_INSTALLED_DATABASE = $databasePath
  try {
    @'
import os
import sqlite3

with sqlite3.connect(os.environ["FOUNDRY_SMOKE_INSTALLED_DATABASE"]) as connection:
    marker = connection.execute(
        "SELECT value FROM app_metadata WHERE key = ?",
        ("installed-restart-smoke",),
    ).fetchone()
if marker != ("preserved",):
    raise RuntimeError("The migrated database marker was not preserved across the restart.")
'@ | python -
    if ($LASTEXITCODE -ne 0) {
      throw 'Could not verify the database after the second application start.'
    }
  }
  finally {
    Remove-Item Env:FOUNDRY_SMOKE_INSTALLED_DATABASE -ErrorAction SilentlyContinue
  }

  Close-InstalledApplicationCleanly `
    -Application $secondApplication `
    -IgnoredSidecarIds $existingSidecarIds
  $secondApplication = $null

  Write-Output 'Installed application migrated data, closed cleanly and restarted with a fresh sidecar.'
}
finally {
  if ($application -and -not $application.HasExited) {
    Stop-Process -Id $application.Id -Force -ErrorAction SilentlyContinue
  }
  if ($secondApplication -and -not $secondApplication.HasExited) {
    Stop-Process -Id $secondApplication.Id -Force -ErrorAction SilentlyContinue
  }
  Get-Process -Name 'foundry-sidecar' -ErrorAction SilentlyContinue |
    Where-Object { $_.Id -notin $existingSidecarIds } |
    Stop-Process -Force -ErrorAction SilentlyContinue
  if ($lockedStream) {
    $lockedStream.Dispose()
  }
}
