@echo off
cd /d %~dp0

echo Проверяю auth state...
pytest tests/test_auth_state.py -q
if errorlevel 1 (
    echo.
    echo state.json невалиден. Сначала обнови сессию:
    echo python auth/save_auth.py
    exit /b 1
)

echo.
echo Auth state валиден. Запускаю авторизованные тесты...
pytest tests/test_messages.py -v
