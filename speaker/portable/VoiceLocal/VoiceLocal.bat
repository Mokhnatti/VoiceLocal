@echo off
cd /d "%~dp0"

REM Portable Python (в папке python/) — приоритет
if exist "%~dp0python\python.exe" (
    "%~dp0python\python.exe" main.py
    goto :eof
)

REM Системный Python
python main.py
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Python не найден. Установите Python 3.11+ с python.org
    echo          или используйте портативную версию (с папкой python/)
    pause
)
