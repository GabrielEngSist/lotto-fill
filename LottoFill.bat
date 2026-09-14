@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" apostas_web.py
  exit /b 0
)
if exist ".venv\Scripts\python.exe" (
  start "" ".venv\Scripts\python.exe" apostas_web.py
  exit /b 0
)
where py >nul 2>nul && (
  start "" py -3 apostas_web.py
  exit /b 0
)
start "" python apostas_web.py
