@echo off
echo Stopping Samanvaya servers on ports 8000, 8001, and 5173...
for %%P in (8000 8001 5173) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr /R /C:":%%P .*LISTENING"') do (
    echo Stopping PID %%A on port %%P...
    taskkill /T /F /PID %%A >nul 2>nul
  )
)
echo Done.
pause
