@echo off
echo ============================================
echo   SAMANVAYA - Stopping All Servers
echo ============================================
echo.

echo Stopping uvicorn processes...
taskkill /F /IM uvicorn.exe 2>nul

echo Stopping node processes (frontend)...
taskkill /F /IM node.exe 2>nul

echo.
echo All servers stopped.
echo.
pause
