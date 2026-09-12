[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string[]]$Paths
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-DefenderCommand {
  $platformRoot = Join-Path $env:ProgramData 'Microsoft/Windows Defender/Platform'
  $platformCommands = @(
    Get-ChildItem -LiteralPath $platformRoot -Filter 'MpCmdRun.exe' -File -Recurse `
      -ErrorAction SilentlyContinue |
      Sort-Object -Property FullName -Descending
  )
  if ($platformCommands.Count -gt 0) {
    return $platformCommands[0].FullName
  }

  $installedCommand = Join-Path $env:ProgramFiles 'Windows Defender/MpCmdRun.exe'
  if (Test-Path -LiteralPath $installedCommand -PathType Leaf) {
    return $installedCommand
  }

  throw 'Microsoft Defender command-line scanner is not available.'
}

$status = Get-MpComputerStatus
if (-not $status.AMServiceEnabled -or -not $status.AntivirusEnabled) {
  throw 'Microsoft Defender antivirus service is not enabled.'
}

try {
  Update-MpSignature | Out-Null
}
catch {
  throw "Microsoft Defender signatures could not be updated: $($_.Exception.Message)"
}

$status = Get-MpComputerStatus
Write-Output (
  'Microsoft Defender engine {0}; signatures {1}; updated {2:u}' -f `
    $status.AMEngineVersion,
    $status.AntivirusSignatureVersion,
    $status.AntivirusSignatureLastUpdated
)

$defenderCommand = Resolve-DefenderCommand
$preferences = Get-MpPreference
$temporarilyRemovedExclusions = @(
  $preferences.ExclusionPath |
    Where-Object { $_ -in @('C:\', 'D:\') }
)

try {
  foreach ($exclusion in $temporarilyRemovedExclusions) {
    Write-Output "Temporarily removing hosted-runner scan exclusion: $exclusion"
    Remove-MpPreference -ExclusionPath $exclusion
  }

  foreach ($path in $Paths) {
    $resolvedPath = (Resolve-Path -LiteralPath $path).Path
    Write-Output "Scanning with Microsoft Defender: $resolvedPath"
    & $defenderCommand -Scan -ScanType 3 -File $resolvedPath -DisableRemediation
    $scanExitCode = $LASTEXITCODE
    if ($scanExitCode -eq 0) {
      continue
    }

    $detections = @(
      Get-MpThreatDetection -ErrorAction SilentlyContinue |
        Sort-Object -Property InitialDetectionTime -Descending |
        Select-Object -First 10 ThreatID, ThreatStatusID, InitialDetectionTime, Resources
    )
    if ($detections.Count -gt 0) {
      $detections | Format-List | Out-String | Write-Error
    }
    if ($scanExitCode -eq 2) {
      throw "Microsoft Defender detected malware or unwanted software in: $resolvedPath"
    }
    throw "Microsoft Defender scan failed with exit code ${scanExitCode}: $resolvedPath"
  }
}
finally {
  foreach ($exclusion in $temporarilyRemovedExclusions) {
    Add-MpPreference -ExclusionPath $exclusion
    Write-Output "Restored hosted-runner scan exclusion: $exclusion"
  }
}

Write-Output 'Microsoft Defender found no threats in the requested Windows packages.'
