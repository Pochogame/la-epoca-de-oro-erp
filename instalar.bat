@echo off
chcp 65001 >nul
title Instalar dependencias - La Epoca de Oro ERP
cd /d "%~dp0"

echo ==================================================
echo   Instalacion de dependencias
echo   La Epoca de Oro ERP
echo ==================================================
echo.

set "PY=python"
where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo ERROR: No se encontro Python en esta computadora.
        echo.
        echo Descargalo de https://www.python.org/downloads/
        echo IMPORTANTE: durante la instalacion marca la casilla
        echo "Add python.exe to PATH" y luego vuelve a ejecutar este archivo.
        pause
        exit /b 1
    )
    set "PY=py -3"
)

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo ERROR: Se requiere Python 3.10 o superior.
    echo Descarga la version mas reciente en https://www.python.org/downloads/
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import flask, flask_sqlalchemy" >nul 2>nul
    if errorlevel 1 (
        echo El entorno virtual existente esta incompleto o danado.
        echo Se eliminara y se creara de nuevo...
        rmdir /s /q .venv
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo ERROR al crear el entorno virtual.
        pause
        exit /b 1
    )
) else (
    echo [1/3] El entorno virtual ya existe y funciona.
)

echo [2/3] Instalando dependencias desde requirements.txt...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto :error

echo [3/3] Verificando que todo quedo instalado...
".venv\Scripts\python.exe" -c "from importlib.metadata import version; print('  Flask', version('flask'), '| SQLAlchemy', version('sqlalchemy'), '| Werkzeug', version('werkzeug'), '| pytest', version('pytest'))"
if errorlevel 1 goto :error

echo.
echo ==================================================
echo   Todo listo y verificado correctamente.
echo   Ahora puedes ejecutar iniciar.bat
echo ==================================================
pause
exit /b 0

:error
echo.
echo ERROR: Algo fallo durante la instalacion.
echo Revisa tu conexion a internet e intentalo de nuevo.
pause
exit /b 1
