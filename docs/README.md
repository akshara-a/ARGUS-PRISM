# ARGUS PRISM: Technical Documentation Index

Welcome to the **ARGUS PRISM** deep-dive technical documentation library. This directory contains comprehensive references, architectural guides, walkthroughs, and deployment blueprints for engineers, agent developers, and enterprise architects.

---

## 📚 Documentation Catalog

| Document | Primary Focus | Target Audience |
| :--- | :--- | :--- |
| 🌐 [**API_REFERENCE.md**](API_REFERENCE.md) | Full specification of all **12 FastAPI REST endpoints** and all **15 Model Context Protocol (MCP 2.x) tools**, JSON schemas, resources, and prompt templates. | Backend Engineers, Agent Developers, Integrators |
| 🎭 [**AGENT_WALKTHROUGH.md**](AGENT_WALKTHROUGH.md) | End-to-end trace comparing a naive LLM vs. an ARGUS-empowered agent: multi-hop DAG reasoning, TabPFN uncertainty bounds ($\pm\sigma\%$), Backboard multi-model consensus, and autonomous factual auto-repair. | AI/LLM Engineers, Solutions Architects |
| 🔌 [**CONNECTORS.md**](CONNECTORS.md) | Open-kernel pluggable connector architecture: build custom enterprise retrieval providers (Confluence, Notion, Elasticsearch), TabPFN oracles, Backboard LLM routers, ElevenLabs audio synthesizers, and **Cost-Guard dual-tier caching** (real-time cost tracking). | Enterprise Developers, DevOps, Contributors |
| 🚀 [**DEPLOYMENT.md**](DEPLOYMENT.md) | Production cloud runtime guide: 1-click Render Blueprints (`render.yaml`), multi-stage Docker containerization (`Dockerfile`), local developer environment, and Cost-Guard telemetry. | DevOps Engineers, Cloud Architects, System Admins |

---

## 🏛️ System High-Level Topology

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 ARGUS PRISM CORE                       │
                  │  (TabPFN Bayesian Oracle · DAG · Multi-Model Consensus)│
                  └──────────────────────────┬─────────────────────────────┘
                                             │
      ┌──────────────┬──────────────┬────────┴─────┬──────────────┬──────────────┐
      ▼              ▼              ▼              ▼              ▼              ▼
[Next.js 16 UI]  [Streamlit]   [MCP Server]   [FastAPI REST]  [Python SDK]   [CLI Evaluator]
(Web Studio)     (Graphviz)    (Cursor/Claude) (Webhooks/CI)  (In-process)   (7 Benchmarks)
                                                   │
                                                   ├─► [Dynamic SVG Badges]
                                                   ├─► [Academic IEEE/APA Exports]
                                                   └─► [ElevenLabs Voice Debriefs]
```

---

## ⚡ Quick Navigation

* Looking for HTTP endpoints? $\rightarrow$ [**API Reference (REST)**](API_REFERENCE.md#1-fastapi-rest-endpoints)
* Connecting Cursor or Claude Desktop? $\rightarrow$ [**MCP 2.x Tools Specification**](API_REFERENCE.md#2-model-context-protocol-mcp-2x-tools)
* Integrating a custom enterprise search or wiki? $\rightarrow$ [**Custom Connectors SDK**](CONNECTORS.md#step-by-step-build-a-custom-enterprise-connector-in--20-lines)
* Understanding Cost-Guard caching & cost economics? $\rightarrow$ [**Cost-Guard Dual-Tier Cache**](CONNECTORS.md#5-cost-guard-dual-tier-telemetry-cache-connector-serpapicache)
* Deploying to Render with 1-click? $\rightarrow$ [**Render Cloud Blueprint**](DEPLOYMENT.md#1-render-cloud-deployment-blueprint)
