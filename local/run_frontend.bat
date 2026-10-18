@echo off
echo ===================================================
echo   ARGUS PRISM: Starting Next.js Studio Frontend
echo ===================================================
cd /d "%~dp0..\frontend"
where bun >nul 2>nul
if %errorlevel% equ 0 (
    bun dev
) else (
    npm run dev
)
