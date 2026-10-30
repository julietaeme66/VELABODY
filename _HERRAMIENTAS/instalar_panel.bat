@echo off
REM Instala el panel "VELABODY Builder" en Premiere Pro (una sola vez).
REM 1) Copia el panel a la carpeta de extensiones CEP del usuario.
REM 2) Habilita paneles sin firmar (PlayerDebugMode) para CEP 9 a 12.
setlocal
set DEST=%APPDATA%\Adobe\CEP\extensions\com.velabody.builder
if exist "%DEST%" rmdir /s /q "%DEST%"
xcopy /e /i /y "%~dp0premiere_panel\com.velabody.builder" "%DEST%" >nul
for %%v in (9 10 11 12) do reg add "HKCU\Software\Adobe\CSXS.%%v" /v PlayerDebugMode /t REG_SZ /d 1 /f >nul
echo.
echo Panel instalado en %DEST%
echo Reinicia Premiere y abrilo desde Ventana ^> Extensiones ^> VELABODY Builder
pause
