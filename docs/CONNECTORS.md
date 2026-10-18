# ARGUS PRISM: Pluggable Connector Architecture & SDK Guide

ARGUS PRISM follows an open-kernel, **pluggable connector architecture** (similar to the Airbyte, Terraform, and OpenTelemetry ecosystems).

The core deterministic engine—including the GoF State Machine, exponential decay mathematics, multi-hop relational DAG, and tie-breaker self-correction—is completely decoupled from underlying search engines, language models, voice synthesis engines, and observability sinks.

---

## 🏛️ Connector Architecture Overview

```text
                                ┌──────────────────────────────────────┐
                                │       ARGUS PRISM CORE KERNEL        │
                                │  • GoF State Machine & Tie-Breaker   │
                                │  • Exponential Decay: Base * e^-λt   │
                                │  • Multi-Hop Relational DAG          │
                                │  • Cost-Guard Two-Tier Cache         │
                                └──────────────────┬───────────────────┘
                                                   │
        ┌───────────────────────────┬──────────────┴────────────┬───────────────────────────┐
        ▼                           ▼                           ▼                           ▼
[ INGESTION CONNECTORS ]    [ AI / ORACLE CONNECTORS ]   [ AUDIO CONNECTORS ]    [ OBSERVABILITY CONNECTORS ]
 • DuckDuckGo (Free/0-Key)   • TabPFN Bayesian Oracle    • ElevenLabs (Broadcast) • Sentry Distributed Tracing
 • SerpApi (Google/Scholar)  • Backboard Multi-Model     • Synthetic Chime       • Local Timing Fallback
 • Custom Enterprise         • Google Gemma 2 (Ollama)   • Custom Local TTS      • OpenTelemetry / Datadog
```

---

## 🔌 Core Connector Interfaces

### 1. Ingestion & Retrieval Connector (`ISearchProvider`)
Defined in [`backend/src/argus/providers/base.py`](../backend/src/argus/providers/base.py). All search engines, enterprise wikis, and document stores implement this interface:

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from argus.models.domain import RawDocument
from argus.providers.cache import CostGuardTelemetry

class ISearchProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for the connector."""
        ...

    @abstractmethod
    def search(
        self,
        query: str,
        engine: str = "google",
        num_results: int = 5,
    ) -> List[RawDocument]:
        """Execute search and return normalized RawDocument objects."""
        ...

    @abstractmethod
    def get_cost_guard_telemetry(self) -> Optional[CostGuardTelemetry]:
        """Return cache hit rate and cost accounting metrics."""
        ...
```

#### Out-of-the-Box Ingestion Connectors:
* **DuckDuckGo Connector** ([`duckduckgo_search.py`](../backend/src/argus/providers/duckduckgo_search.py)): 100% free, zero-API-key live search provider reading endpoints from `DUCKDUCKGO_ENDPOINT`.
* **SerpApi Connector** ([`web_search.py`](../backend/src/argus/providers/web_search.py)): Multi-engine search provider (Google, Google Scholar, Google News, GitHub) reading from `SERPAPI_ENDPOINT`.
* **Mock Connector** ([`mock_search.py`](../backend/src/argus/providers/mock_search.py)): Deterministic offline mock provider used in testing and air-gapped CI/CD environments.

---

### 2. Bayesian Oracle Connector (`TabPFNOracle`)
Defined in [`backend/src/argus/engine/tabpfn_oracle.py`](../backend/src/argus/engine/tabpfn_oracle.py). Employs in-memory Prior-Data Fitted Networks to output epistemic uncertainty bounds ($\pm\sigma\%$):

```python
from argus.engine.tabpfn_oracle import TabPFNOracle

# Calculate in-memory Bayesian credibility class probabilities
metrics = TabPFNOracle.evaluate_claim(
    tier_weight=1.0,           # Tier 1 (Official Documentation)
    age_months=1.5,            # Fresh release (1.5 months old)
    corroboration_count=3,     # Corroborated by 3 converging sources
    conflict_count=0,          # Zero opposing contradictions
    base_score=94.0,
)

print(metrics["bayesian_score"])             # 95.2
print(metrics["epistemic_uncertainty_sigma"]) # 1.8
print(metrics["class_probabilities"])         # {'verified': 0.95, 'contested': 0.03, 'refuted': 0.02}
```

---

### 3. Open-Weight Multi-Model Router Connector (`BackboardClient`)
Defined in [`backend/src/argus/llm/backboard_client.py`](../backend/src/argus/llm/backboard_client.py). Connects to Backboard to triangulate propositions across multiple open-weight models in volatile RAM with zero prompt persistence:

```python
from argus.llm.backboard_client import BackboardClient

client = BackboardClient()
result = client.compare_open_weight_models(
    text="Next.js 15 requires React 19.",
    models=["llama-3-8b-instruct", "mistral-7b-instruct", "gemma-2-9b-it"],
)
print("Consensus verdict:", result["consensus_verdict"])
print("Divergence score:", result["divergence_score"])
```

---

### 4. Ephemeral Audio Briefing Connector (`ElevenLabsBriefing`)
Defined in [`backend/src/argus/audio/elevenlabs_client.py`](../backend/src/argus/audio/elevenlabs_client.py). Streams base64 audio directly to RAM across 3 distinct personas:

* **Rachel** (`ELEVENLABS_VOICE_RACHEL`): Professional executive briefing.
* **Adam** (`ELEVENLABS_VOICE_ADAM`): Technical architect deep-dive.
* **Drew** (`ELEVENLABS_VOICE_DREW`): Skeptical fact-checker tone.

```python
from argus.audio.elevenlabs_client import ElevenLabsBriefing

audio_bytes, mime, script = ElevenLabsBriefing.generate_briefing(
    report=report,
    topic_or_client="Security Audit",
    voice_persona="adam",
)
```

---

### 5. Cost-Guard Dual-Tier Telemetry Cache Connector (`SerpApiCache`)
Defined in [`backend/src/argus/providers/cache.py`](../backend/src/argus/providers/cache.py).

> **Concept & Architecture:** Cost-Guard ensures search telemetry retrieval is economically sustainable, eliminates runaway API bills, and tracks real-time cost savings across distributed LLM evaluations.

#### Why Cost-Guard Dual-Tier Caching is Essential
Every proposition audit executes **3 specialized search vectors** (optimistic, skeptical, temporal). Auditing a 10-claim technical post triggers 30+ search queries. Live commercial search queries (e.g. SerpApi Google/Scholar) cost ~$0.01 per query with 300–800ms of latency.

The **Cost-Guard Two-Tier Cache** achieves an **85–90% hit rate**, dropping latency from 350ms to 0.5ms and slashing API bills to pennies:

```
                     Incoming Claim Search Request
                                   │
                                   ▼
               ┌───────────────────────────────────────┐
               │         Deterministic SHA-256         │
               │  Hash(query : engine : num : vector)  │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │    TIER 1: In-Memory    │
                      │        LRU Cache        │
                      └────────────┬────────────┘
                            HIT   / \   MISS
                           ┌─────┘   └─────┐
                           ▼               ▼
                     [ 0.5ms Latency ]  ┌─────────────────────────┐
                     [ $0.00 Cost    ]  │     TIER 2: Persistent   │
                                        │       SQLite Cache      │
                                        └────────────┬────────────┘
                                              HIT   / \   MISS
                                             ┌─────┘   └─────┐
                                             ▼               ▼
                                       [ 2.0ms Latency ]  ┌─────────────────────────┐
                                       [ $0.00 Cost    ]  │    LIVE SEARCH API     │
                                       (Promotes to T1)   │ (SerpApi / DuckDuckGo)  │
                                                          └────────────┬────────────┘
                                                                       │
                                                                       ▼
                                                                [ ~350ms Latency ]
                                                                [ Costs ~$0.01   ]
                                                                (Stores in T1 + T2)
```

* **Tier 1 (In-Memory RAM LRU)**: Sub-millisecond (`~0.5ms`) volatile `OrderedDict` storing up to 128 recent vector results.
* **Tier 2 (Persistent SQLite Disk)**: Fast (`~2.0ms`) local storage (`.cache/serpapi_cache.sqlite`) with automatic 24-hour TTL expiration. Cache hits in Tier 2 automatically promote entries back into Tier 1 RAM.
* **Automated Cost Accounting**:
  $$\text{Dollars Saved (USD)} = \text{Cache Hits} \times \$0.01$$

```python
from argus.providers.cache import SerpApiCache

cache = SerpApiCache()
telemetry = cache.get_telemetry()
print(f"Cache Hit Rate: {telemetry.cache_hit_rate_pct:.1f}%")
print(f"Total API Cost Saved: ${telemetry.estimated_cost_saved_usd:.2f} USD")
```

---

## 🛠️ Step-by-Step: Build a Custom Enterprise Connector in < 20 Lines

Suppose your enterprise wants to connect ARGUS PRISM to an **internal Confluence workspace**, **Notion knowledge base**, or **Elasticsearch index** so proprietary company SOPs and engineering architecture docs are audited without leaking data outside your VPC.

Here is a complete, working custom connector:

```python
import os
import requests
from typing import List, Optional
from argus.models.domain import RawDocument
from argus.providers.base import ISearchProvider
from argus.providers.cache import CostGuardTelemetry

class ConfluenceEnterpriseConnector(ISearchProvider):
    """Custom enterprise connector auditing internal Atlassian Confluence documentation."""

    def __init__(self, base_url: Optional[str] = None, api_token: Optional[str] = None):
        self.base_url = base_url or os.getenv("CONFLUENCE_URL", "https://company.atlassian.net/wiki")
        self.token = api_token or os.getenv("CONFLUENCE_API_TOKEN")

    @property
    def provider_name(self) -> str:
        return "confluence_enterprise"

    def search(self, query: str, engine: str = "cql", num_results: int = 5) -> List[RawDocument]:
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        response = requests.get(
            f"{self.base_url}/rest/api/content/search",
            params={"cql": f"text ~ \"{query}\"", "limit": num_results},
            headers=headers,
            timeout=10,
        )
        data = response.json()
        documents = []
        for item in data.get("results", []):
            documents.append(
                RawDocument(
                    title=item.get("title", "Untitled Confluence Doc"),
                    snippet=item.get("excerpt", ""),
                    link=f"{self.base_url}{item.get('_links', {}).get('webui', '')}",
                    displayed_link=self.base_url,
                    source_engine="confluence",
                )
            )
        return documents

    def get_cost_guard_telemetry(self) -> Optional[CostGuardTelemetry]:
        return None  # Enterprise self-hosted endpoints have zero marginal per-search cost
```

### Registering Your Custom Connector

Registering your custom connector takes a single line:

```python
from argus.engine.evaluator import ResearchEvaluator

# Initialize the evaluator with your custom enterprise connector
evaluator = ResearchEvaluator(provider=ConfluenceEnterpriseConnector())

# Audit internal architecture decision records (ADRs)
report = evaluator.execute_research(
    topic="Authentication JWT expiry configuration",
    domain_context="Security Policy",
)
print(f"Internal Policy Compliance Score: {report.global_confidence_score:.1f}%")
```

---

## 🧩 Extension Points for Contributors

| Extension Point | Base Class / Interface | Typical Implementations |
| :--- | :--- | :--- |
| **Search Providers** | [`ISearchProvider`](../backend/src/argus/providers/base.py) | Bing, Brave Search, Perplexity API, Elasticsearch, Notion, Confluence |
| **LLM Extractors** | `BaseLLMClient` | Anthropic Claude 3.5, OpenAI GPT-4o, DeepSeek-R1, Local vLLM |
| **Audio Synthesizers** | `BaseAudioClient` | OpenAI TTS, Coqui TTS, Piper TTS (local offline speech) |
| **Observability Sinks** | `BaseTracer` | Datadog APM, OpenTelemetry (OTel), Prometheus metrics, Langfuse |
| **Export Formats** | `BaseReportFormatter` | PDF certificates, Slack webhook alerts, GitHub PR check annotations |

---

## 📜 Architectural Standards for Connectors
1. **Zero Hardcoded URLs**: All endpoint targets, base URLs, and tokens must resolve via `os.getenv` with dummy fallbacks in `.env.example`.
2. **Zero Disk Persistence**: Connectors must execute in-memory; user drafts must never be written to disk.
3. **Graceful Fallbacks**: Ingestion connectors must handle network timeouts gracefully by falling back to mock strategies rather than raising unhandled exceptions.
