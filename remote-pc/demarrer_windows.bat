@echo off
rem Lance le serveur de contrôle à distance sur Windows.
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python n'est pas installe. Telechargez-le sur https://www.python.org/downloads/
  echo et cochez "Add Python to PATH" pendant l'installation.
  pause
  exit /b 1
)
python -m pip install -r requirements.txt
python server.py %*
pause
