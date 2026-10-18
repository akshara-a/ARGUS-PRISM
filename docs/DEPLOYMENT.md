# ARGUS PRISM: Deployment, Cloud Runtime & Testing Guide

This guide provides end-to-end instructions for deploying ARGUS PRISM across **Render Cloud**, **Docker Containers**, and **Local Developer Environments**, along with verification and test suite execution.

---

## 🚀 1. Render Cloud Deployment Blueprint

ARGUS PRISM includes a turnkey Infrastructure-as-Code specification in [`render.yaml`](../render.yaml) that automatically provisions the multi-tier microservice architecture on Render.

### Services Provisioned by `render.yaml`:
1. **`argus-prism-api`** (FastAPI REST Backend & MCP Core)
   * **Runtime**: Python 3.12
   * **Build Command**: `pip install --upgrade pip && pip install -e .`
   * **Start Command**: `uvicorn --app-dir backend/src argus.api.server:app --host 0.0.0.0 --port $PORT`
   * **Health Check**: `/api/health`
2. **`argus-prism-studio`** (Next.js 16 Web Studio)
   * **Runtime**: Node 20
   * **Root Directory**: `frontend`
   * **Build Command**: `npm install && npm run build`
   * **Start Command**: `npm start`
   * **Environment**: `NEXT_PUBLIC_API_URL=https://argus-prism-api.onrender.com`
3. **`argus-prism-dashboard`** (Streamlit Telemetry & DAG Explorer)
   * **Runtime**: Python 3.12
   * **Start Command**: `streamlit run backend/src/argus/dashboard/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`

---

### Step-by-Step Render Deployment:
1. **Push your code to GitHub / GitLab**:
   ```bash
   git remote add origin https://github.com/<your-username>/argus-prism.git
   git push -u origin main
   ```
2. **Open Render Dashboard**:
   * Navigate to [dashboard.render.com](https://dashboard.render.com).
   * Click **New +** (top right) $\rightarrow$ Select **Blueprint**.
3. **Connect Repository**:
   * Select your `argus-prism` repository.
   * Render detects `render.yaml` and lists the 3 services.
4. **Configure Secrets**:
   * Under `argus-prism-api`, set your optional API keys (`SERPAPI_API_KEY`, `ELEVENLABS_API_KEY`, `BACKBOARD_API_KEY`, `SENTRY_DSN`).
5. **Click Apply**:
   * Render builds and deploys the backend, frontend, and dashboard.

> [!NOTE]
> On Render's Free tier, web services spin down after 15 minutes of inactivity. The first request after an idle period takes ~30–50 seconds for cold start; subsequent requests respond instantly.

---

## 🐳 2. Docker Container Deployment

ARGUS PRISM provides a multi-stage production [`Dockerfile`](../Dockerfile) based on `python:3.12-slim`.

### Build the Docker Image:
```bash
docker build -t argus-prism:latest .
```

### Run the Container:
```bash
docker run -d \
  -p 8000:8000 \
  -p 8501:8501 \
  -e SEARCH_PROVIDER=duckduckgo \
  -e SENTRY_ENVIRONMENT=production \
  --name argus-prism-container \
  argus-prism:latest
```

### Verify Container Health:
```bash
curl -f http://localhost:8501/_stcore/health
```

---

## 💻 3. Local Developer Setup

### Prerequisites:
* Python 3.12+ (or `uv`)
* Node.js 20+ (or Bun)
* Git

### Step 1: Clone and Configure Environment:
```bash
git clone https://github.com/<your-username>/argus-prism.git
cd "ARGUS PRISM"

# Copy environment templates
cp .env.example .env
cp frontend/.env.example frontend/.env.local
```

### Step 2: Install Python Backend Dependencies:
```bash
# Using standard pip
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -e .

# Or using uv (ultrafast)
uv sync
```

### Step 3: Install Frontend Dependencies:
```bash
cd frontend
npm install  # or: bun install
cd ..
```

### Step 4: Run Services Concurrently:
* **Terminal 1 (FastAPI Backend)**:
  ```bash
  uvicorn --app-dir backend/src argus.api.server:app --host 0.0.0.0 --port 8000 --reload
  ```
* **Terminal 2 (Next.js 16 Web Studio)**:
  ```bash
  cd frontend
  npm run dev
  # Accessible at http://localhost:3000
  ```
* **Terminal 3 (Optional Streamlit DAG Explorer)**:
  ```bash
  streamlit run backend/src/argus/dashboard/app.py --server.port 8501
  ```

---

## 🧪 4. Automated Testing & Verification

### Run the Pytest Test Suite (82 Tests):
```bash
python -m pytest tests -v
```
Verifies unit logic, scoring math, exponential decay velocity, DAG cycles, SSRF defenses, Backboard router, TabPFN oracle, and ElevenLabs persona lookups.

### Run the Ground-Truth Benchmark Evaluation:
```bash
python backend/evaluate.py
```
Executes 7 deterministic benchmarks measuring precision, recall, contradiction detection, and freshness handling against curated ground-truth datasets.

### Run Next.js 16 Production Build:
```bash
cd frontend
npm run build  # or: bun run build
```
Ensures zero TypeScript lint or bundle compilation errors with Turbopack.

---

## 🛡️ 5. Key Environment Variables

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `DEFAULT_SEARCH_PROVIDER` | Active search provider (`duckduckgo`, `serpapi`, `mock`) | `duckduckgo` |
| `SERPAPI_API_KEY` | SerpApi secret key for live Google/Scholar telemetry | *Optional* |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for streaming audio briefings | *Optional* |
| `ELEVENLABS_VOICE_RACHEL` | Voice ID for Executive persona | `21m00Tcm4TlvDq8ikWAM` |
| `ELEVENLABS_VOICE_ADAM` | Voice ID for Technical persona | `pNInz6obpgDQGcFmaJgB` |
| `ELEVENLABS_VOICE_DREW` | Voice ID for Skeptical persona | `29vD33N1CtxCmqQRPOHJ` |
| `BACKBOARD_API_KEY` | Backboard key for open-weight multi-model arena | *Optional* |
| `CORS_ALLOWED_ORIGINS` | Allowed origins for web clients (`*` or comma-separated) | `*` |
| `CORS_ORIGIN_REGEX` | Regular expression for cloud subdomains | `https://.*\.onrender\.com` |
| `SENTRY_DSN` | Sentry Data Source Name for distributed tracing | *Optional* |
