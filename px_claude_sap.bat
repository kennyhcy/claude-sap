@echo off
REM ============================================================
REM  File:        claude-resume.bat
REM  Generated:   Claude Code
REM  Date:        2026-08-13
REM  Purpose:     Resume last session, else start fresh
REM ============================================================
REM  Resume the last Claude Code session if possible; otherwise
REM  start a fresh one. Also opens the current working directory
REM  in Explorer before launching claude.
REM
REM  Logic:
REM    1. Open %CD% in Explorer.
REM    2. Run `claude -c` and capture its exit code.
REM    3. If it fails to read the previous session (non-zero exit),
REM       fall back to a plain `claude` with no session history.
REM    4. Hand the exit code back to the caller.
REM
REM  Usage:
REM    claude-resume.bat
REM ============================================================

SET https_proxy=http://127.0.0.1:3128
SET http_proxy=http://127.0.0.1:3128
SET HTTP
SET NO_PROXY

@cls

setlocal

REM Open the current working directory in Explorer.
REM start "" explorer "%CD%"

REM First try: resume the last session.
call claude -c
set "RC=%errorlevel%"

REM If resume succeeded (exit code 0), we're done.
if "%RC%"=="0" goto :done

REM Resume failed (couldn't read previous session) -> start fresh.
echo.
echo [claude-resume] Could not resume previous session (exit %RC%). Starting a new one...
echo.
call claude
set "RC=%errorlevel%"

:done
endlocal & exit /b %RC%
@pause
