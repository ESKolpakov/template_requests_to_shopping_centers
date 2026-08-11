@echo off
REM Быстрый запуск приложения из исходников на Windows (без сборки .exe).
REM Требуется установленный Python 3.10+ (https://www.python.org/downloads/,
REM при установке отметить галочку "Add python.exe to PATH").

cd /d "%~dp0.."

if not exist ".venv" (
    echo Создаю виртуальное окружение...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Устанавливаю зависимости...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ОШИБКА при установке зависимостей — см. текст ошибки выше.
    pause
    exit /b 1
)

set PYTHONPATH=%cd%\src
python -m uktc_letters.main
if errorlevel 1 (
    echo.
    echo Приложение завершилось с ошибкой — см. текст выше.
    pause
    exit /b 1
)

pause
