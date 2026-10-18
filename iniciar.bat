@echo off
chcp 65001 >nul
title La Epoca de Oro ERP
cd /d "%~dp0"

echo ==================================================
echo   La Epoca de Oro ERP - Cafe, Guisados y Nostalgia
echo ==================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERROR: No se encontro Python. Instala Python 3.10+ desde
        echo https://www.python.org/downloads/ y vuelve a ejecutar este archivo.
        pause
        exit /b 1
    )
    echo [2/3] Instalando dependencias...
    ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
    if errorlevel 1 (
        echo ERROR al instalar dependencias.
        pause
        exit /b 1
    )
)

if not exist "instance\la_epoca_de_oro.db" (
    echo [3/3] Creando base de datos con datos de demostracion...
    ".venv\Scripts\python.exe" seed.py
)

echo.
echo Servidor:  http://127.0.0.1:5000
echo Cuentas:   admin/admin123  ^|  chef1/chef123  ^|  mesero1/mesero123
echo.
echo Se abrira el navegador automaticamente.
echo Para detener el sistema: cierra esta ventana o pulsa Ctrl+C.
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000"
".venv\Scripts\python.exe" run.py

pause
