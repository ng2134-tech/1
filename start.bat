@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem На машине бывает несколько Python, и нужный не всегда первый в PATH.
rem Двойной клик по .py вообще берёт интерпретатор из ассоциации файлов.
rem Поэтому ищем тот, в котором действительно есть yfinance.

set "PY="
call :try py -3
if not defined PY call :try python
if not defined PY call :try "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not defined PY call :try "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY call :try "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY call :try "%LOCALAPPDATA%\Python\bin\python.exe"

if not defined PY (
    echo.
    echo   Не найден Python с установленным yfinance.
    echo.
    echo   Проверьте вручную, подставив свой путь:
    echo     "путь\к\python.exe" -c "import yfinance"
    echo.
    echo   Если модуля нет нигде — установите:
    echo     "путь\к\python.exe" -m pip install yfinance requests pandas
    echo.
    pause
    exit /b 1
)

echo Запускаю через: %PY%
echo.
%PY% web.py
pause
exit /b

:try
%* -c "import yfinance" >nul 2>&1
if not errorlevel 1 set "PY=%*"
goto :eof
