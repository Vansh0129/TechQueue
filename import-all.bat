@echo off
REM ==============================================================================
REM TechQueue Interview Coach — Windows Import Script (cmd.exe)
REM Imports tools, flows, knowledge bases, and agents into watsonx Orchestrate.
REM ==============================================================================

setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
set "ORCH=%SCRIPT_DIR%..\venv\Scripts\orchestrate.exe"

if not exist "%ORCH%" (
    where orchestrate >nul 2>&1
    if %errorlevel%==0 (
        set "ORCH=orchestrate"
    ) else (
        echo ERROR: orchestrate CLI not found in venv or PATH.
        exit /b 1
    )
)

echo ======================================================
echo  TechQueue Interview Coach - Importing to Orchestrate
echo ======================================================

echo.
echo [1/4] Importing Knowledge Base ...
"%ORCH%" knowledge-bases import -f "%SCRIPT_DIR%knowledge_base\interview_knowledge_base.yaml"

echo.
echo [2/4] Importing Python Tools ...
"%ORCH%" tools import -k python -f "%SCRIPT_DIR%tools\profile_tools.py"
"%ORCH%" tools import -k python -f "%SCRIPT_DIR%tools\evaluation_tools.py"

echo.
echo [3/4] Importing Flow Tool ...
"%ORCH%" tools import -k flow -f "%SCRIPT_DIR%tools\interview_prep_flow.py"

echo.
echo [4/4] Importing Agent ...
"%ORCH%" agents import -f "%SCRIPT_DIR%agents\techqueue_interview_coach.yaml"

echo.
echo ======================================================
echo  Import complete!
echo ======================================================
pause
