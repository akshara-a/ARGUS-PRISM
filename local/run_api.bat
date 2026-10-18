@echo off
echo ===================================================
echo   ARGUS PRISM: Starting FastAPI Backend Server
echo ===================================================
cd /d "%~dp0.."
uv run uvicorn argus.api.server:app --port 8000 --reload
