@echo off
chcp 65001 >nul
title Pruebas - La Epoca de Oro ERP
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No existe el entorno virtual. Ejecuta primero iniciar.bat
    pause
    exit /b 1
)

echo Ejecutando la suite de pruebas de integracion...
echo.
".venv\Scripts\python.exe" -m pytest -q
echo.
pause
