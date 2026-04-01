@echo off
:: Добавляет VoiceLocal в автозагрузку с правами админа через Планировщик задач

set TASK_NAME=VoiceLocal
set BAT_PATH=C:\claud\1c\speaker\portable\VoiceLocal\VoiceLocal.bat

:: Удалить старую задачу если есть
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Создать задачу: запуск при входе, с правами SYSTEM (максимальные)
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%BAT_PATH%\"" ^
  /sc onlogon ^
  /rl highest ^
  /f

if %errorlevel%==0 (
    echo [OK] Задача "%TASK_NAME%" добавлена в автозагрузку с правами админа.
) else (
    echo [ОШИБКА] Не удалось создать задачу. Запусти этот bat от имени администратора.
)
pause
