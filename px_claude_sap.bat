@echo off
REM ============================================================
REM Load environment variables from .claud_sap.env.json.
REM Requires PowerShell (preinstalled on Windows 10/11). If the file is
REM missing or invalid JSON, we warn and continue without proxy settings.
REM ============================================================

for /f "usebackq delims=" %%E in (`powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$e = Get-Content -Raw '%~dp0.env.json' | ConvertFrom-Json; $e.PSObject.Properties | ForEach-Object { 'SET ' + [char]34 + $_.Name + '=' + $_.Value + [char]34 }"`) do (
    %%E
)

@cls

setlocal

REM Open the current working directory in Explorer.
REM start "" explorer "%CD%"

call claude