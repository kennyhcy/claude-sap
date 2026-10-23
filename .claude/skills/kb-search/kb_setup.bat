@echo off
rem ============================================================
rem  kb_setup.bat — one-command initialization of the kb data folder (~/.kb)
rem  (Prompts for the vault directory, then runs kb_setup.py:
rem   config -> model -> venv -> download -> index)
rem  Double-click or run from cmd; no arguments needed.
rem ============================================================
setlocal
chcp 65001 >nul

echo ============================================
echo  kb setup (local knowledge-base search)
echo  知识库检索工具初始化 (数据目录: %USERPROFILE%\.kb)
echo ============================================
echo.

set "VAULT="
set /p VAULT=Knowledge-base root directory (md files) / 笔记库根目录 (其中 md 文件将被向量化):
if "%VAULT%"=="" (
    echo [setup] ERROR: no vault path entered / 未输入笔记库路径
    pause
    exit /b 2
)

echo.
echo [setup] vault = %VAULT%
echo.

python "%~dp0kb_setup.py" --vault "%VAULT%"

if errorlevel 1 (
    echo.
    echo [setup] FAILED / 初始化失败 — see messages above; fix and rerun this bat.
    pause
    exit /b 1
)

echo.
echo [setup] Done / 初始化完成.
echo AI-tool integration: nothing to configure — the kb data folder defaults to %USERPROFILE%\.kb
pause
