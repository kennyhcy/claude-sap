# Fetch SharePoint folder listing via headless Edge with dedicated profile.
# Reuses the sap-note get_sapnote.ps1 mechanism: browser sends HttpOnly cookies itself.
param(
    [Parameter(Mandatory=$true)][string]$Url,
    [string]$OutFile
)
$ErrorActionPreference = 'Stop'

$edgeCandidates = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
)
$edge = $edgeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { Write-Output "ERROR: msedge.exe not found"; exit 1 }

$ProfileDir = Join-Path $env:LOCALAPPDATA "ClaudeSharePointProfile"
if (-not $OutFile) { $OutFile = Join-Path $env:TEMP "sp_dump.html" }

if (Test-Path $OutFile) { Remove-Item $OutFile -Force }

$args = @(
    "--headless=new",
    "--user-data-dir=`"$ProfileDir`"",
    "--disable-gpu",
    "--dump-dom",
    $Url
)
$proc = Start-Process -FilePath $edge -ArgumentList $args -PassThru -Wait -WindowStyle Hidden -RedirectStandardOutput $OutFile
Write-Output "exit=$($proc.ExitCode)"
if ((Test-Path $OutFile) -and ((Get-Item $OutFile).Length -gt 0)) {
    Write-Output "size=$((Get-Item $OutFile).Length)"
    Write-Output "out=$OutFile"
} else {
    Write-Output "no output"
}
