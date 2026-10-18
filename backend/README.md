# ARGUS PRISM Backend

Deterministic Evidence Intelligence & Verification Engine.

## 📁 Architecture

```text
backend/
├── src/
│   └── argus/
│       ├── api/             # FastAPI REST Server (/api/validate, /api/chat, /api/compare)
│       ├── audio/           # ElevenLabs spoken audio debriefs
│       ├── dashboard/       # Streamlit interactive graph dashboard
│       ├── engine/          # Verification pipeline, GoF state machine, scoring, DAG
│       ├── llm/             # Google Gemma 2 local model client (Ollama)
│       ├── mcp/             # Model Context Protocol (MCP 2.x) stdio server
│       ├── models/          # Pydantic V2 domain models
│       ├── observability/   # Sentry distributed agent tracing & spans
│       └── providers/       # Search strategies (DuckDuckGo, SerpApi, Mock, SQLite cache)
├── demo.py                  # 6-act end-to-end judge showcase script
├── evaluate.py              # 7-point CI/CD deterministic benchmark suite
├── pyproject.toml           # Python package specifications
└── requirements.txt         # Pinned pip requirements
```

## 🚀 Running Backend Services Directly

From the project root:
```bash
# Start FastAPI REST server
uv run uvicorn argus.api.server:app --port 8000 --reload

# Start Streamlit Evidence Inspector Dashboard
uv run streamlit run backend/src/argus/dashboard/app.py

# Launch MCP Server
uv run python -m argus.mcp.server

# Run 7-Point Benchmark Suite
uv run python backend/evaluate.py

# Run Showcase Demo
uv run python backend/demo.py
```
Or use the 1-click Windows batch scripts located in [`local/`](../local).
