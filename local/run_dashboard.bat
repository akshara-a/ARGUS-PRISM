@echo off
echo Starting ARGUS PRISM Evidence Inspector Dashboard...
cd /d "%~dp0.."
uv run streamlit run backend/src/argus/dashboard/app.py
