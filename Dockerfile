# ==============================================================================
# ARGUS PRISM - Production Containerfile (Render, Cloud & Local Deployment)
# ==============================================================================

FROM python:3.12-slim

# Set environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency configuration and source
COPY pyproject.toml pytest.ini ./
COPY backend/ ./backend/
COPY tests/ ./tests/
COPY README.md .env.example ./

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -e .

# Expose Streamlit dashboard and MCP ports
EXPOSE 8501 8000

# Healthcheck to ensure container stability
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default command: launch the interactive Streamlit dashboard
CMD ["streamlit", "run", "backend/src/argus/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
