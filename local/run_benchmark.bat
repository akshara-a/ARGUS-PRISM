@echo off
echo Running ARGUS PRISM Benchmark and Evaluation Harness...
cd /d "%~dp0.."
uv run python backend/evaluate.py
pause
