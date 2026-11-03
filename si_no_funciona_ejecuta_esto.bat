@echo off
chcp 65001 >nul
title Reparar - La Epoca de Oro ERP
cd /d "%~dp0"

echo ==================================================
echo   Reparacion de la instalacion
echo   La Epoca de Oro ERP
echo ==================================================
echo.
echo Este proceso elimina el entorno virtual y lo instala de nuevo.
echo Cierra cualquier ventana del sistema que este abierta antes de continuar.
echo.
pause

if exist ".venv" (
    echo Eliminando entorno anterior...
    rmdir /s /q ".venv"
)
if exist ".venv\Scripts\python.exe" (
    echo.
    echo ERROR: No se pudo eliminar la carpeta .venv.
    echo Cierra todas las ventanas del sistema y vuelve a intentarlo.
    pause
    exit /b 1
)

call "%~dp0instalar.bat" --auto
if errorlevel 1 (
    echo.
    echo No se pudo reparar automaticamente. Revisa los mensajes anteriores.
    pause
    exit /b 1
)

echo.
echo Entorno reparado. Iniciando el sistema...
call "%~dp0iniciar.bat"
