@echo off
cd /d "%~dp0"
set "BUNDLED_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED_PY%" (
 "%BUNDLED_PY%" start.py
 goto end
)
where py >nul 2>nul
if not errorlevel 1 (
 py -3 start.py
 if not errorlevel 1 goto end
)
where python >nul 2>nul
if not errorlevel 1 (
 python start.py
 if not errorlevel 1 goto end
)
echo Install Python 3.11 or newer from https://www.python.org/downloads/windows/
echo Enable Add Python to PATH, then reopen this file.
:end
pause
