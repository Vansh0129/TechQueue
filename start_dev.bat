@echo off
REM ============================================================
REM  TechQueue Interview Coach — Dev Mode Launcher
REM  Requires Ollama running locally: https://ollama.com
REM  Open http://localhost:8181 in your browser once started.
REM ============================================================

set PYTHONPATH=%~dp0..

REM ── Locate Python ────────────────────────────────────────────
REM Prefer the project venv, then fall back to anything on PATH.
set PY=%~dp0..\venv\Scripts\python.exe
if not exist "%PY%" (
    where python >nul 2>&1
    if %errorlevel%==0 (
        set PY=python
    ) else (
        echo ERROR: Python not found.
        echo   Either activate your virtual environment or install Python.
        pause
        exit /b 1
    )
)

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set OLLAMA_MODEL=granite3-moe:3b

REM ── Optional overrides (uncomment and edit to override defaults) ──
REM set OLLAMA_URL=http://localhost:11434/api/chat
REM set PORT=8181

echo ================================================
echo  TechQueue Interview Coach  [DEV MODE]
echo ================================================
echo  LLM : %OLLAMA_MODEL% via Ollama
echo  UI  : http://localhost:8181
echo  Stop: Ctrl+C
echo ================================================

"%PY%" "%~dp0dev_server.py"
pause
