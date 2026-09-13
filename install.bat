@echo off
REM Windows: dê dois cliques ou rode install.bat no Prompt de Comando
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 install.py %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python install.py %*
  exit /b %ERRORLEVEL%
)

echo Erro: Python 3.10+ nao encontrado. Instale em https://www.python.org/downloads/ e rode de novo.
exit /b 1
