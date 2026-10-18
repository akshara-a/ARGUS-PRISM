@echo off
echo Starting ARGUS PRISM MCP Server (stdio transport)...
cd /d "%~dp0.."
uv run python -m argus.mcp.server
