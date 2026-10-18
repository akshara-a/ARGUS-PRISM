@echo off
echo ======================================================================
echo Launching ARGUS PRISM 1-Click End-to-End Judge Showcase Demo...
echo ======================================================================
cd /d "%~dp0.."
uv run python backend/demo.py
pause
