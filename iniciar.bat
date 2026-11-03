@echo off
chcp 65001 >nul
title La Epoca de Oro ERP
cd /d "%~dp0"

echo ==================================================
echo   La Epoca de Oro ERP - Cafe, Guisados y Nostalgia
echo ==================================================
echo.

set "NECESITA_PREPARAR=0"
if not exist ".venv\Scripts\python.exe" set "NECESITA_PREPARAR=1"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import flask, flask_sqlalchemy" >nul 2>nul
    if errorlevel 1 set "NECESITA_PREPARAR=1"
)

if "%NECESITA_PREPARAR%"=="1" (
    echo [1/3] Preparando el entorno. Puede tardar la primera vez...
    call "%~dp0instalar.bat" --auto
    if errorlevel 1 (
        echo.
        echo No se pudo preparar el entorno. Revisa los mensajes anteriores.
        pause
        exit /b 1
    )
) else (
    echo [1/3] El entorno ya esta listo.
)

if not exist "instance\la_epoca_de_oro.db" (
    echo [2/3] Creando base de datos con datos de demostracion...
    ".venv\Scripts\python.exe" seed.py
) else (
    echo [2/3] Base de datos encontrada.
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
