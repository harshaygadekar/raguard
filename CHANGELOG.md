# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-06-19

### Added

- Core `CanaryMiddleware` engine with token generation, injection, and scanning.
- `InMemoryTokenStore` with TTL eviction, FIFO pruning, session limits, and background sweep.
- `RedisTokenStore` for horizontally scaled deployments using Redis sorted sets.
- `RAGuardConfig` with Pydantic Settings, environment variable support (`RAGUARD_` prefix).
- Framework adapters:
  - `RAGuardLangChainCallback` — LangChain `BaseCallbackHandler` integration.
  - `RAGuardLlamaIndexPostprocessor` — LlamaIndex `BaseNodePostprocessor` integration.
  - `RAGuardFastAPIMiddleware` — FastAPI/Starlette middleware with streaming support.
- Zero-width stealth mode for invisible canary tokens.
- Encoding bypass detection (`decode_response`): Base64, ROT13, hex, reversed, character-split.
- Webhook alerting with SSRF validation and circuit-breaker protection.
- Fail-open / fail-closed operational modes.
- Thread-safe in-process metrics (`RAGuardMetrics`).
- `max_scan_body_bytes` guardrail in the FastAPI adapter (default 1 MB) to prevent OOM on oversized generation responses.
- CI pipeline: Ruff, MyPy strict, Pytest with 85% coverage gate across Python 3.10/3.11/3.12.
- 178 tests across 14 files including property-based (Hypothesis), adversarial, concurrency, and benchmark tests.

### Known Limitations

- `decode_response` defaults to `False` for performance. Enable it to catch encoded bypass attempts.
- `InMemoryTokenStore` is single-process only. Use `RedisTokenStore` for multi-worker deployments.
- Stealth mode (zero-width tokens) may be stripped by some LLM APIs during tokenization.
- Semantic paraphrasing attacks are out of scope by design. See README threat model.
