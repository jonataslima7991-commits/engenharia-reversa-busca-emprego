@echo off
:: ============================================================
:: PIPELINE DE COLETA SEMANAL — Amostra Academica
:: %~dp0 resolve o caminho automaticamente.
:: Python e localizado dinamicamente via WHERE para garantir
:: que o Task Scheduler encontre o executavel.
:: ============================================================

setlocal
cd /d "%~dp0"

:: Log com data no formato YYYY-MM-DD
for /f "tokens=2 delims==" %%i in ('wmic os get LocalDateTime /value') do set DT=%%i
set LOGFILE=%~dp0logs\coleta_%DT:~0,4%-%DT:~4,2%-%DT:~6,2%.log
if not exist "%~dp0logs" mkdir "%~dp0logs"

echo. >> "%LOGFILE%"
echo ============================================================ >> "%LOGFILE%"
echo  INICIO: %DATE% %TIME% >> "%LOGFILE%"
echo ============================================================ >> "%LOGFILE%"

:: Localiza o Python no sistema (resolve o problema de PATH no Task Scheduler)
for /f "tokens=*" %%i in ('where python 2^>nul') do (
    set PYTHON=%%i
    goto :python_ok
)
echo [ERRO] Python nao encontrado. Instale Python e adicione ao PATH. >> "%LOGFILE%"
goto :fim

:python_ok
echo  Python: %PYTHON% >> "%LOGFILE%"

:: Passo 1 — Coleta de vagas
echo [1/2] Coletando vagas... >> "%LOGFILE%"
"%PYTHON%" main.py >> "%LOGFILE%" 2>&1

if %errorlevel% neq 0 (
    echo [ERRO] main.py falhou ^(codigo %errorlevel%^) >> "%LOGFILE%"
    goto :fim
)

:: Passo 2 — Gerar JSONs dos dashboards
echo [2/2] Gerando dashboards... >> "%LOGFILE%"
"%PYTHON%" gerar_dashboard.py >> "%LOGFILE%" 2>&1

if %errorlevel% neq 0 (
    echo [ERRO] gerar_dashboard.py falhou ^(codigo %errorlevel%^) >> "%LOGFILE%"
)

:fim
echo  FIM: %DATE% %TIME% >> "%LOGFILE%"
echo ============================================================ >> "%LOGFILE%"
endlocal