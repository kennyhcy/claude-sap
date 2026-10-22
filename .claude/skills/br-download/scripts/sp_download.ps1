# Download SharePoint file by driving a REAL (windowed) Edge with the shared profile.
# The profile already holds the SSO session; download.aspx triggers a normal browser
# download into the default Downloads dir (prefs write is best-effort and often
# blocked while Edge updates it), then we move the newest fresh .docx to OutFile.
# NOTE: downloads land in %USERPROFILE%\Downloads, NOT profile Downloads dir.
param(
    [Parameter(Mandatory=$true)][string]$Url,
    [Parameter(Mandatory=$true)][string]$OutFile
)
$ErrorActionPreference = 'Stop'
$edge = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
$ProfileDir = Join-Path $env:LOCALAPPDATA "ClaudeSharePointProfile"
$downloads = Join-Path $ProfileDir "Downloads"
if (-not (Test-Path $downloads)) { New-Item -ItemType Directory -Path $downloads | Out-Null }

# set download dir via Preferences file
$prefsPath = Join-Path $ProfileDir "Default\Preferences"
if (Test-Path $prefsPath) {
    try {
        $prefs = Get-Content $prefsPath -Raw | ConvertFrom-Json
        if ($null -ne $prefs) {
            if (-not $prefs.PSObject.Properties['download']) { $prefs | Add-Member -NotePropertyName download -NotePropertyValue (@{}) -Force }
            $prefs.download | Add-Member -NotePropertyName default_directory -NotePropertyValue $downloads -Force
            $prefs.download | Add-Member -NotePropertyName prompt_for_download -NotePropertyValue $false -Force
            $prefs | ConvertTo-Json -Depth 30 | Set-Content $prefsPath -Encoding UTF8
        }
    } catch { Write-Output "prefs edit skipped: $($_.Exception.Message)" }
}

$proc = Start-Process -FilePath $edge -ArgumentList @(
    "--user-data-dir=`"$ProfileDir`"",
    "--no-first-run",
    $Url
) -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 3
# close the download-triggering tab's Edge process tree once download completes;
# poll below handles waiting, so nothing else to do here.

$name = ([uri]::UnescapeDataString(($Url -split 'SourceUrl=')[1])) -replace '%2F','/' -split '/' | Select-Object -Last 1
$deadline = (Get-Date).AddMinutes(3)
$found = $null
$userDownloads = Join-Path $env:USERPROFILE "Downloads"
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 2000
    foreach ($d in @($downloads, $userDownloads)) {
        if (-not (Test-Path $d)) { continue }
        $done = Get-ChildItem $d -Filter "*.docx" -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-4) -and $_.Name -notlike "~*" }
        if ($done) {
            # prefer a file matching the requested name, else newest
            $want = $done | Where-Object { $_.Name -like "*$name*" }
            $found = @($want) + @($done) | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            break
        }
    }
    if ($found) { break }
}
if ($found) {
    Copy-Item $found.FullName $OutFile -Force
    Write-Output "saved=$OutFile"
    Write-Output "size=$((Get-Item $OutFile).Length)"
    Write-Output "from=$($found.FullName)"
} else {
    Write-Output "TIMEOUT: file did not appear in $downloads or $userDownloads"
}
