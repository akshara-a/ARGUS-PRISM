@echo off
echo ===================================================
echo   ARGUS PRISM: Technology Head-to-Head Comparison
echo ===================================================
cd /d "%~dp0.."
uv run python -m argus.cli compare "FastAPI" "Django"
pause
