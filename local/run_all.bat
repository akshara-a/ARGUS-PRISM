@echo off
echo ========================================================
echo   ARGUS PRISM: Launching Full Stack (Backend + Frontend)
echo ========================================================
start "ARGUS FastAPI Backend" cmd /k "%~dp0run_api.bat"
start "ARGUS Next.js Studio" cmd /k "%~dp0run_frontend.bat"
echo Services launched in separate terminal windows!
echo - FastAPI Backend: http://localhost:8000
echo - Next.js Studio:  http://localhost:3000
