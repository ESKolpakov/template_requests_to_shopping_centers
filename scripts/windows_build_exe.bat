@echo off
REM Собрать автономный UKTCLetters.exe (без необходимости ставить Python
REM на компьютер, где приложение будет использоваться).
REM Python нужен только НА ЭТОМ компьютере, чтобы собрать .exe.

cd /d "%~dp0.."

if not exist ".venv" (
    echo Создаю виртуальное окружение...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Устанавливаю зависимости для сборки...
pip install -r requirements-dev.txt

echo Собираю .exe (это может занять пару минут)...
pyinstaller scripts\build_exe.spec

echo.
echo Готово! Приложение здесь: dist\UKTCLetters\UKTCLetters.exe
echo Можно скопировать всю папку dist\UKTCLetters на другой компьютер —
echo Python там не потребуется.
pause
