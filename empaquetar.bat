@echo off
chcp 65001 >nul
title Empaquetar - La Epoca de Oro ERP
cd /d "%~dp0"

set "ZIP=%~dp0..\LaEpocaDeOroERP.zip"
if exist "%ZIP%" del "%ZIP%"

echo Generando paquete limpio para enviar (sin .venv, sin base de datos, sin cache)...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$origen='%CD%'; $zip='%ZIP%'; $stage=Join-Path $env:TEMP 'epoca_zip_stage'; if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }; New-Item -ItemType Directory -Path $stage | Out-Null; $excl=@('.venv','instance','.pytest_cache','__pycache__','.git'); Get-ChildItem -LiteralPath $origen -Force | Where-Object { $excl -notcontains $_.Name } | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $stage -Recurse -Force }; Get-ChildItem -Path $stage -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue; Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::CreateFromDirectory($stage, $zip, [System.IO.Compression.CompressionLevel]::Optimal, $false); Remove-Item -Recurse -Force $stage"
if errorlevel 1 goto :error

for %%A in ("%ZIP%") do echo Paquete creado: %%A
for %%A in ("%ZIP%") do echo Tamano: %%~zA bytes
echo.
echo Envia ese ZIP a tu amigo. El debe:
echo   1. Descargarlo y descomprimirlo (clic derecho, Extraer todo).
echo   2. Tener Python 3.10 o superior instalado (python.org, marcar "Add to PATH").
echo   3. Ejecutar instalar.bat (solo la primera vez) y luego iniciar.bat.
echo      Si algo falta o falla, que use si_no_funciona_ejecuta_esto.bat.
echo.
pause
exit /b 0

:error
echo ERROR al crear el paquete.
pause
exit /b 1
