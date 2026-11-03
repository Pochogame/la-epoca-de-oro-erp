@echo off
chcp 65001 >nul
title Instalar - La Epoca de Oro ERP
cd /d "%~dp0"

echo ==================================================
echo   La Epoca de Oro ERP
echo   Preparacion del entorno
echo ==================================================
echo.

set "SIN_PAUSA="
if /i "%~1"=="--auto" set "SIN_PAUSA=1"

set "PY_EXE="
set "PY_ARGS="

call :detectar_python
call :verificar_python
if not errorlevel 1 goto :python_listo

:instalar_python
echo No se encontro Python 3.10 o superior en este equipo.
echo.

where winget >nul 2>nul
if errorlevel 1 goto :sin_winget

echo Se instalara Python automaticamente con winget.
echo Esto puede tardar unos minutos; si Windows pide permisos, aceptalos.
echo.
winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo.
    echo El primer intento fallo. Reintentando la instalacion...
    winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
)

set "PY_EXE="
set "PY_ARGS="
call :detectar_python
call :verificar_python
if errorlevel 1 goto :sin_winget
goto :python_listo

:sin_winget
echo.
echo No fue posible preparar Python automaticamente.
echo Se abrira la pagina oficial de descarga en tu navegador.
echo.
echo Instala Python 3.10 o superior y marca la casilla
echo "Add python.exe to PATH". Despues ejecuta de nuevo este archivo.
start "" "https://www.python.org/downloads/"
pause
exit /b 1

:python_listo
echo Python detectado:
"%PY_EXE%" %PY_ARGS% --version
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import flask, flask_sqlalchemy" >nul 2>nul
    if errorlevel 1 (
        echo El entorno virtual existente esta incompleto o danado.
        echo Se eliminara y se creara de nuevo...
        rmdir /s /q .venv
        if exist ".venv\Scripts\python.exe" (
            echo ERROR: No se pudo eliminar la carpeta .venv.
            echo Cierra otras ventanas del sistema y vuelve a intentarlo.
            pause
            exit /b 1
        )
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual...
    "%PY_EXE%" %PY_ARGS% -m venv .venv
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
".venv\Scripts\python.exe" -c "from importlib.metadata import version; print('  Flask', version('flask'), '| SQLAlchemy', version('sqlalchemy'), '| pytest', version('pytest'))"
if errorlevel 1 goto :error

echo.
echo ==================================================
echo   Todo listo y verificado correctamente.
if not defined SIN_PAUSA echo   Ahora ejecuta iniciar.bat para abrir el sistema.
echo ==================================================
if not defined SIN_PAUSA pause
exit /b 0

:error
echo.
echo ERROR: Algo fallo durante la instalacion.
echo Revisa tu conexion a internet e intentalo de nuevo.
pause
exit /b 1

:detectar_python
if not defined PY_EXE (
    for %%P in (Python313 Python312 Python311 Python310) do (
        if not defined PY_EXE if exist "%LocalAppData%\Programs\Python\%%P\python.exe" set "PY_EXE=%LocalAppData%\Programs\Python\%%P\python.exe"
    )
)
if not defined PY_EXE (
    for %%P in (Python313 Python312 Python311 Python310) do (
        if not defined PY_EXE if exist "%ProgramFiles%\Python%%P\python.exe" set "PY_EXE=%ProgramFiles%\Python%%P\python.exe"
    )
)
if not defined PY_EXE (
    for %%P in (Python313 Python312 Python311 Python310) do (
        if not defined PY_EXE if exist "C:\%%P\python.exe" set "PY_EXE=C:\%%P\python.exe"
    )
)
if not defined PY_EXE (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PY_EXE=py"
        set "PY_ARGS=-3"
    )
)
if not defined PY_EXE (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        echo %%i | findstr /i "WindowsApps" >nul
        if errorlevel 1 set "PY_EXE=%%i"
    )
)
exit /b 0

:verificar_python
if not defined PY_EXE exit /b 1
"%PY_EXE%" %PY_ARGS% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
exit /b %errorlevel%
