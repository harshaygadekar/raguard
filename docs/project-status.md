# Project Status: RAGuard

**Last Updated:** 2026-06-04  
**Current Phase:** Phase 4 Complete (Framework Adapters, Async Support & Webhook Alerts)  

---

## 🎯 Project Overview
**RAGuard** is a free, open-source, deterministic security middleware designed to protect Retrieval-Augmented Generation (RAG) applications from context exfiltration via indirect prompt injection. It acts as a "tripwire" by injecting unique, session-specific canary tokens into retrieved context and scanning LLM outputs for their presence.

---

## ✅ Completed Work

### Phase 1: Deep Analysis & Threat Modeling (`analysis.md`)
- [x] Defined the core problem: Indirect Prompt Injection and RAG context exfiltration.
- [x] Conducted competitor analysis: Acknowledged `canari-llm` and `vigil-llm`, positioning RAGuard as a lightweight, RAG-specific middleware.
- [x] Corrected initial hallucinations: Removed fabricated academic citations and replaced them with verified OWASP LLM Top 10 mitigation strategies.
- [x] Defined explicit limitations: Documented that the tool catches token-level exfiltration, but not semantic summarization, encoded leaks, or aggressive tokenizer normalization.

### Phase 2: Product Requirements Document (`prd.md`)
- [x] Defined the 3-step solution: Dynamic Injection, Augmented Generation, Output Interception.
- [x] **Key Differentiator Locked:** Added "Zero-Width Stealth Mode" as an opt-in V1 feature to differentiate from competitors, with a fallback to safe alphanumeric strings.
- [x] **V1 Scope Finalized:** Core Engine + Stealth Mode + LangChain Adapter + LlamaIndex Adapter + FastAPI Middleware.
- [x] Defined technical requirements: Python 3.10+, minimal dependencies, 95%+ test coverage, tokenizer validation suite, and adversarial red-teaming.
- [x] Established Open Source Strategy: MIT licensing, and automated CI/CD for PyPI publishing.

### Phase 3: Tech Stack, Architecture & Repository Setup
- [x] **Tech Stack Finalized:** Python 3.10+, `pydantic` (core), `pytest`, `ruff`, `mypy` (dev).
- [x] **Repository Structure Created:** `src/raguard/`, `tests/`, `examples/`, `docs/`.
- [x] **Configuration Files Generated:** `pyproject.toml`, `.gitignore`, `LICENSE` (MIT).
- [x] **System Architecture Documented:** `docs/architecture.md` with Mermaid sequence diagrams.
- [x] **CI/CD Pipeline Configured:** `.github/workflows/ci.yml` for automated linting, type checking, and testing.
- [x] **Core Engine & Tests Stubbed:** Functional `CanaryMiddleware` class with token generation, injection, scanning, and initial `pytest` coverage.
- [x] **Initial Documentation:** Professional `README.md` with installation and quick-start examples.

### Phase 4: System Design, Framework Adapters & Core Enhancements
- [x] **Custom Exceptions:** `CanaryTokenDetected` and `RAGuardImportError` in `src/raguard/exceptions.py`.
- [x] **Core Engine Enhancements:**
  - Webhook alerting via `urllib.request` (stdlib, fire-and-forget, 5s timeout, JSON payload with session_id/timestamp/response_snippet).
  - Async methods: `is_safe_async()` and `inject_async()` with non-blocking webhook via `asyncio.to_thread`.
  - Token accumulation: `_active_tokens` stores `list[str]` per session (supports multi-retrieval scenarios).
  - `clear_session()` method for memory management in long-running processes.
- [x] **LangChain Adapter** (`src/raguard/adapters/langchain.py`):
  - `RAGuardLangChainCallback` extending `BaseCallbackHandler`.
  - Hooks: `on_retriever_end` (inject), `on_llm_end` (scan generations), `on_chain_end` (scan chain outputs).
  - Compatible with both `langchain_core` (v1.3+) and legacy `langchain` import paths.
  - Raises `CanaryTokenDetected` on exfiltration.
- [x] **LlamaIndex Adapter** (`src/raguard/adapters/llamaindex.py`):
  - `RAGuardLlamaIndexPostprocessor` extending `BaseNodePostprocessor`.
  - `_postprocess_nodes()` injects canary tokens into node text.
  - `scan_response()` for manual output validation (LlamaIndex lacks output interception hook).
  - Uses Pydantic v2 `ConfigDict` (no deprecation warnings).
- [x] **FastAPI Adapter** (`src/raguard/adapters/fastapi.py`):
  - `RAGuardFastAPIMiddleware` extending `BaseHTTPMiddleware`.
  - Configurable regex path patterns for inject/scan endpoints.
  - Session ID extraction from headers (configurable header name).
  - Automatic JSON body modification for retrieval paths (recursive into dicts and lists).
  - 403 response blocking for generation paths with leaked tokens.
  - `clear_session()` called after scan to prevent memory leaks.
- [x] **Package Exports:**
  - Lazy `__getattr__` in `adapters/__init__.py` (PEP 562) — prevents import errors when optional deps missing.
  - `CanaryTokenDetected` exported from top-level `raguard.__init__`.
- [x] **Test Suite:** 45 tests across 6 files — **all passing, 0 failures, 0 skips, 0 warnings**.
  - `test_core.py` (3): Token generation, injection, scanning.
  - `test_exceptions.py` (5): Exception messages, attributes, inheritance.
  - `test_webhook.py` (8): Webhook delivery, payload, failure handling, async.
  - `test_adapters.py` (19): 6 LangChain + 5 LlamaIndex + 8 FastAPI.
  - `test_integration.py` (10): Full pipelines, multi-session, token accumulation, async, adapter integration.
- [x] **Example Files:** `langchain_example.py`, `llamaindex_example.py`, `fastapi_example.py`.
- [x] **Linting:** All ruff checks pass, zero errors.

---

## 🚧 Upcoming Work

### Phase 5: Adversarial Red Teaming Test Suite
- [ ] **Direct Exfiltration Attacks:** Tests simulating attackers forcing LLMs to output retrieved context verbatim.
- [ ] **Encoded Leak Attempts:** Tests for Base64, URL encoding, and other encoding bypass techniques.
- [ ] **Semantic Summarization Attacks:** Tests where LLMs are prompted to summarize without special characters.
- [ ] **Token Filtering Attacks:** Tests simulating attackers who guess and strip the token format.
- [ ] **Multi-Step Jailbreaking:** Complex attack scenarios combining multiple techniques.

### Phase 6: Dev Environment Setup
- [ ] **Pre-commit Hooks:** Configure pre-commit with ruff, mypy, and pytest to enforce quality before commits.
- [ ] **Local Ollama Integration:** Set up local LLM (Llama 3 via Ollama) for free integration testing without API costs.
- [ ] **Tokenizer Validation Suite:** Verify zero-width tokens survive preprocessing in OpenAI, Anthropic, and Ollama.

### Phase 7: Documentation & Polish
- [ ] **README Update:** Comprehensive examples, use cases, and performance benchmarks.
- [ ] **CONTRIBUTING.md:** Guidelines for community contributors.
- [ ] **CODE_OF_CONDUCT.md:** Community standards.
- [ ] **SECURITY.md:** Responsible vulnerability disclosure process.
- [ ] **API Documentation:** Auto-generated docs from docstrings.

### Phase 8: Release Preparation
- [ ] **Finalize pyproject.toml:** Add proper metadata, classifiers, and dependency specifications.
- [ ] **Publish to PyPI:** Initial release as `raguard` package.
- [ ] **GitHub Release:** Create v1.0.0 tag and release notes.
- [ ] **Launch Announcement:** Blog post or social media announcement.

---

## 📁 Key Artifacts
- `analysis.md`: Comprehensive threat modeling and competitor landscape.
- `prd.md`: Detailed product requirements, scope, and technical specifications.
- `phase-3-plan.md`: Execution plan and division of labor for Phase 3.
- `pyproject.toml`: Python project configuration and dependencies.
- `docs/architecture.md`: System design and Mermaid diagrams.
- `src/raguard/core.py`: Core engine with token generation, injection, scanning, webhooks, and async support.
- `src/raguard/config.py`: Configuration models (stealth_mode, token_length, alert_webhook_url).
- `src/raguard/exceptions.py`: Custom exceptions (CanaryTokenDetected, RAGuardImportError).
- `src/raguard/adapters/langchain.py`: LangChain BaseCallbackHandler adapter.
- `src/raguard/adapters/llamaindex.py`: LlamaIndex BaseNodePostprocessor adapter.
- `src/raguard/adapters/fastapi.py`: FastAPI BaseHTTPMiddleware adapter.
- `tests/`: 45 tests across 6 files (core, exceptions, webhook, adapters, integration).
- `examples/`: Usage examples for core, LangChain, LlamaIndex, and FastAPI.
- `project-status.md`: (This file) High-level progress tracker.

---

## 📝 Notes & Decisions
- **LlamaIndex in V1:** Kept in V1 scope alongside LangChain to ensure comprehensive coverage of major RAG frameworks from day one.
- **Zero-Width Characters:** Implemented as an *opt-in* feature (`stealth_mode=True`) due to the risk of certain LLM APIs stripping them during preprocessing. Default mode uses obscure alphanumeric strings for guaranteed reliability.
- **Marketing Positioning:** Framed as a "deterministic tripwire for token-level exfiltration," explicitly avoiding claims of "100% proof" or comprehensive DLP to maintain enterprise credibility.
- **Token Accumulation (Phase 4):** Changed `_active_tokens` from `dict[str, str]` to `dict[str, list[str]]` to support multi-retrieval scenarios where `inject()` is called multiple times per session. `is_safe()` checks all accumulated tokens.
- **LangChain Compatibility (Phase 4):** Adapter supports both `langchain_core.callbacks.base.BaseCallbackHandler` (v1.3+) and legacy `langchain.callbacks.base.BaseCallbackHandler` via fallback import pattern.
- **Pydantic v2 Migration (Phase 4):** LlamaIndex adapter uses `model_config = ConfigDict(arbitrary_types_allowed=True)` instead of deprecated `class Config` to avoid PydanticDeprecatedSince20 warnings.
- **Lazy Adapter Imports (Phase 4):** `adapters/__init__.py` uses PEP 562 `__getattr__` to defer framework imports until adapter classes are accessed, preventing ImportError when optional dependencies aren't installed.
- **FastAPI JSON Injection (Phase 4):** Middleware recursively injects tokens into string values within JSON response bodies (dicts and nested lists), not just top-level strings.
- **Webhook Design (Phase 4):** Uses stdlib `urllib.request` to avoid adding httpx/aiohttp as core dependencies. Fire-and-forget pattern with 5s timeout and exception logging.
