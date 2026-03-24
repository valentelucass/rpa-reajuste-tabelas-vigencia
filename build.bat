@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 (
    echo   Nao foi possivel acessar a pasta do projeto: %~dp0
    endlocal & exit /b 1
)
set "APP_NAME=RPA-Reajuste-Tabelas-Vigencia"
set "DIST_DIR=dist\%APP_NAME%"
set "EXE_NAME=%APP_NAME%.exe"
set "INSTALLER_SCRIPT=installer\%APP_NAME%.iss"
set "INSTALLER_DIR=dist\instalador"
set "INSTALLER_NAME=%APP_NAME%-Setup.exe"
set "OVERALL_EXIT_CODE=0"
set "INSTALLER_OK=0"

echo ============================================
echo   Build - Painel de Automacao RPA
echo   Reajuste Tabelas Vigencia
echo ============================================
echo.

taskkill /IM %EXE_NAME% /F /T >nul 2>&1
ping 127.0.0.1 -n 2 >nul

if exist build (
    rmdir /S /Q build
    echo   build\ removido para rebuild limpo
)

if exist "%DIST_DIR%" (
    rmdir /S /Q "%DIST_DIR%"
    echo   %DIST_DIR%\ removido para rebuild limpo
)

if exist "%INSTALLER_DIR%" (
    rmdir /S /Q "%INSTALLER_DIR%"
    echo   %INSTALLER_DIR%\ removido para rebuild limpo
)

echo.
call :resolver_python
if not defined PYTHON_CMD (
    echo   Python nao encontrado. Instale o launcher py -3.12 ou deixe o comando python disponivel no PATH.
    endlocal & exit /b 1
)

echo   Atualizando icones em public\ a partir de rpa_icon_4.png...
%PYTHON_CMD% update_icon.py
if errorlevel 1 (
    echo   Falha ao atualizar os icones.
    endlocal & exit /b 1
)

%PYTHON_CMD% -m PyInstaller build.spec --clean --noconfirm

if %ERRORLEVEL% EQU 0 (
    if exist .env (
        copy /Y .env "%DIST_DIR%\.env" >nul
        echo   .env copiado para %DIST_DIR%\
    )

    call :resolver_iscc
    if not defined ISCC_EXE (
        call :instalar_inno_setup
        call :resolver_iscc
    )

    if defined ISCC_EXE (
        echo   Gerando instalador com Inno Setup...
        call :gerar_instalador
        if errorlevel 1 (
            echo   Falha ao gerar o instalador.
            set "OVERALL_EXIT_CODE=1"
        ) else (
            set "INSTALLER_OK=1"
            echo   Instalador em: %INSTALLER_DIR%\%INSTALLER_NAME%
        )
    ) else (
        echo   Inno Setup nao encontrado. Instalador nao gerado.
    )

    echo.
    if "!INSTALLER_OK!"=="1" (
        echo ============================================
        echo   Build concluido com sucesso!
        echo   Executavel em: %DIST_DIR%\%EXE_NAME%
        echo   Instalador em: %INSTALLER_DIR%\%INSTALLER_NAME%
        echo ============================================
    ) else (
        echo ============================================
        echo   Executavel gerado com sucesso.
        echo   Executavel em: %DIST_DIR%\%EXE_NAME%
        echo   Instalador nao foi gerado.
        echo ============================================
    )
) else (
    echo.
    echo ============================================
    echo   ERRO no build. Verifique os logs acima.
    echo ============================================
    set "OVERALL_EXIT_CODE=1"
)

endlocal & set "EXIT_CODE=%OVERALL_EXIT_CODE%"
if /I "%~1"=="--no-pause" exit /b %EXIT_CODE%
pause
exit /b %EXIT_CODE%

:resolver_iscc
set "ISCC_EXE="
for %%I in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe") do (
    if exist %%~I set "ISCC_EXE=%%~I"
)
if not defined ISCC_EXE (
    for /f "delims=" %%I in ('where ISCC 2^>nul') do (
        if not defined ISCC_EXE set "ISCC_EXE=%%I"
    )
)
exit /b 0

:resolver_python
set "PYTHON_CMD="
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.12"
    exit /b 0
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
)
exit /b 0

:instalar_inno_setup
where winget >nul 2>&1
if errorlevel 1 exit /b 0
echo   Inno Setup nao encontrado. Instalando via winget...
winget install --id JRSoftware.InnoSetup --exact --silent --accept-package-agreements --accept-source-agreements
exit /b 0

:gerar_instalador
set "INSTALLER_TEMP_DIR=%TEMP%\%APP_NAME%-installer-%RANDOM%%RANDOM%"

if exist "%INSTALLER_TEMP_DIR%" (
    rmdir /S /Q "%INSTALLER_TEMP_DIR%" >nul 2>&1
)

mkdir "%INSTALLER_TEMP_DIR%" >nul 2>&1
if errorlevel 1 (
    echo   Nao foi possivel criar a pasta temporaria do instalador.
    exit /b 1
)

echo   Compilando instalador fora do OneDrive em: %INSTALLER_TEMP_DIR%
"!ISCC_EXE!" /O"%INSTALLER_TEMP_DIR%" /F"%APP_NAME%-Setup" "%INSTALLER_SCRIPT%"
if errorlevel 1 exit /b 1

if not exist "%INSTALLER_TEMP_DIR%\%INSTALLER_NAME%" (
    echo   Instalador temporario nao encontrado em %INSTALLER_TEMP_DIR%\%INSTALLER_NAME%
    exit /b 1
)

if not exist "%INSTALLER_DIR%" mkdir "%INSTALLER_DIR%" >nul 2>&1
call :copiar_arquivo_com_retry "%INSTALLER_TEMP_DIR%\%INSTALLER_NAME%" "%INSTALLER_DIR%\%INSTALLER_NAME%"
if errorlevel 1 exit /b 1

rmdir /S /Q "%INSTALLER_TEMP_DIR%" >nul 2>&1
exit /b 0

:copiar_arquivo_com_retry
set "COPY_SOURCE=%~1"
set "COPY_DEST=%~2"
set /a COPY_TRY=0

:copiar_arquivo_com_retry_loop
set /a COPY_TRY+=1
copy /Y "%COPY_SOURCE%" "%COPY_DEST%" >nul
if not errorlevel 1 exit /b 0
if !COPY_TRY! GEQ 5 (
    echo   Nao foi possivel copiar o instalador para %COPY_DEST%
    exit /b 1
)

echo   Copia do instalador falhou na tentativa !COPY_TRY!. Tentando novamente...
ping 127.0.0.1 -n 3 >nul
goto :copiar_arquivo_com_retry_loop
