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
if errorlevel 1 (
    echo.
    echo ОШИБКА при установке зависимостей — см. текст ошибки выше.
    pause
    exit /b 1
)

echo Собираю .exe (это может занять пару минут)...
pyinstaller scripts\build_exe.spec
if errorlevel 1 (
    echo.
    echo ОШИБКА СБОРКИ — см. текст ошибки выше. UKTCLetters.exe НЕ создан.
    pause
    exit /b 1
)

echo.
echo Готово! Приложение здесь: dist\UKTCLetters\UKTCLetters.exe
echo Можно скопировать всю папку dist\UKTCLetters на другой компьютер —
echo Python там не потребуется.
pause
