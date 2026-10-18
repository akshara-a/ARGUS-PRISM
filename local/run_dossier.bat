@echo off
echo ===================================================
echo   ARGUS PRISM: Enterprise HTML Dossier Generator
echo ===================================================
cd /d "%~dp0.."
uv run python -m argus.cli dossier "Pydantic v2 migration"
pause
