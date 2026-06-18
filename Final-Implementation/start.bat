@echo off
echo ============================================
echo   SAMANVAYA - Starting All Servers
echo ============================================
echo.

echo [1/3] Resetting demo data and starting Backend on port 8000...
start "Samanvaya Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe seed.py --reset && venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo [2/3] Starting Mock Bank on port 8001...
start "Mock Bank" cmd /k "cd /d %~dp0mock-bank && ..\backend\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001"

echo [3/3] Starting Frontend on port 5173...
start "Samanvaya Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================
echo   All servers launched!
echo.
echo   Backend:     http://localhost:8000
echo   API Docs:    http://localhost:8000/docs
echo   Mock Bank:   http://localhost:8001/ui
echo   Frontend:    http://localhost:5173
echo ============================================
echo.
pause
