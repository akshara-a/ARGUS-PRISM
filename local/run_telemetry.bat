@echo off
echo ===================================================
echo   ARGUS PRISM: Cost-Guard & Cache Telemetry Inspector
echo ===================================================
cd /d "%~dp0.."
uv run python -m argus.cli telemetry
pause
