@echo off
echo ============================================
echo   SAMANVAYA - Starting All Servers
echo ============================================
echo.

echo [1/3] Starting Backend on port 8000...
start "Samanvaya Backend" cmd /k "cd backend && python seed.py && python -m uvicorn main:app --reload --port 8000"

echo [2/3] Starting Mock Bank on port 8001...
start "Mock Bank" cmd /k "cd mock-bank && python -m uvicorn main:app --reload --port 8001"

echo [3/3] Starting Frontend on port 3000...
start "Samanvaya Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================
echo   All servers launched!
echo.
echo   Backend:     http://localhost:8000
echo   API Docs:    http://localhost:8000/docs
echo   Mock Bank:   http://localhost:8001/ui
echo   Frontend:    http://localhost:3000
echo ============================================
echo.
pause
