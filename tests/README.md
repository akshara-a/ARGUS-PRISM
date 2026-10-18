# ARGUS PRISM Test Suite

This directory contains the automated test suite (53 unit and integration tests) verifying the mathematical correctness, deterministic scoring, tie-breaker self-correction, and caching behavior of ARGUS PRISM.

## 🧪 Test Inventory

| Test File | Focus Area |
| :--- | :--- |
| `test_audit_report.py` | ROI calculator, HTML certificate, and Markdown briefing generation |
| `test_cache.py` | Two-tier LRU memory + SQLite persistent cache hit rates & cost savings |
| `test_cli.py` | Terminal interface (validate, research, compare, dossier, telemetry, mcp) |
| `test_comparator.py` | TechnologyComparator 4-dimension head-to-head empirical trade-off matrix |
| `test_contradiction.py` | Polarity clash detection and semantic contradiction mapping |
| `test_dossier.py` | Standalone enterprise HTML evidence dossier structure |
| `test_elevenlabs.py` | Spoken audio briefings & synthetic chime fallback |
| `test_gemma.py` | Google Gemma 2 local open-weight model client & heuristic fallbacks |
| `test_graph_engine.py` | Multi-hop entailment DAG and transitive invalidation |
| `test_mcp.py` | Model Context Protocol tools, resources, and prompt templates |
| `test_providers.py` | SerpApi adapter, DuckDuckGo free search, and mock provider |
| `test_scoring.py` | Credibility tiering, temporal exponential decay ($e^{-\lambda t}$), and Bayesian updates |
| `test_sentry.py` | Sentry distributed agent tracing, spans, breadcrumbs, and Cost-Guard telemetry |
| `test_state_machine.py` | GoF state transitions and recursive tie-breaker elevation |
| `test_validator.py` | Multi-stream proposition audit and hallucination trap detection |

## 🚀 Running the Tests

From the project root:
```bash
pytest tests/
# or with verbose traceback:
pytest -v --tb=short
```
Or via the benchmark launcher in [`local/run_benchmark.bat`](../local/run_benchmark.bat).
