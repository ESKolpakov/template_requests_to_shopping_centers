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

set PYTHONPATH=%cd%\src
python -m uktc_letters.main

pause
