# RAGuard v1.0.0 — Initial Release

**Deterministic security middleware for RAG applications.**

RAGuard protects Retrieval-Augmented Generation (RAG) systems from context exfiltration via indirect prompt injection. It acts as a deterministic "tripwire" by injecting unique, session-specific canary tokens into retrieved context and scanning LLM outputs for their presence.

## Highlights

- **Core Engine** — `CanaryMiddleware` with token generation, injection, scanning, and async support
- **Zero-Width Stealth Mode** — Invisible Unicode canary tokens that hide from attackers
- **Framework Adapters** — Drop-in integrations for LangChain, LlamaIndex, and FastAPI
- **Encoding Bypass Detection** — Catches Base64, ROT13, hex, reversed, and character-split evasions
- **Production Hardening** — Thread-safe token stores (in-memory + Redis), circuit-breaker webhooks, SSRF filtering, body size caps, structured JSON logging
- **FastAPI Streaming Support** — Sliding-window chunk scanner for `text/event-stream` responses
- **Observability** — Built-in thread-safe metrics counters

## Installation

```bash
pip install raguard-security

# With framework support:
pip install "raguard-security[langchain]"
pip install "raguard-security[llamaindex]"
pip install "raguard-security[fastapi]"
pip install "raguard-security[redis]"
```

## Quick Start

```python
from raguard import CanaryMiddleware

middleware = CanaryMiddleware()

# Inject a canary token into retrieved context
context = middleware.inject("session_123", "Retrieved document text...")

# After LLM generates a response, check for leakage
if not middleware.is_safe("session_123", llm_response):
    raise Exception("Context exfiltration detected!")
```

## Test Coverage

180 tests across 14 files including unit, integration, adversarial, property-based (Hypothesis), concurrency, and benchmark tests. 85%+ code coverage.

## Known Limitations

- `decode_response` defaults to `False` for performance — enable it to catch encoded bypass attempts
- `InMemoryTokenStore` is single-process only — use `RedisTokenStore` for multi-worker deployments
- Stealth mode (zero-width tokens) may be stripped by some LLM APIs during tokenization
- Semantic paraphrasing attacks are out of scope by design — see the [threat model](https://github.com/harshaygadekar/raguard#-threat-model--known-limitations)

## Links

- [Documentation](https://github.com/harshaygadekar/raguard#readme)
- [PyPI](https://pypi.org/project/raguard-security/)
- [Changelog](https://github.com/harshaygadekar/raguard/blob/main/CHANGELOG.md)
- [Contributing](https://github.com/harshaygadekar/raguard/blob/main/CONTRIBUTING.md)
- [Security Policy](https://github.com/harshaygadekar/raguard/blob/main/SECURITY.md)
