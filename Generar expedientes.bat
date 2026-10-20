@echo off
chcp 65001 >nul
cd /d "%~dp0"
".venv\Scripts\python.exe" generador\construir.py --destino "%~dp0..\Comics"
echo.
pause
