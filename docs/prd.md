# Product Requirements Document (PRD): RAGuard

**Project Name:** RAGuard  
**Version:** 1.3 (Revised with LlamaIndex in V1)  
**Status:** Draft  
**Date:** 2026-06-03  
**License Target:** MIT / Apache 2.0 (Free and Open Source)  

---

## 1. Executive Summary
RAGuard is a free, open-source, deterministic security middleware designed to protect Retrieval-Augmented Generation (RAG) applications from context exfiltration via indirect prompt injection. By dynamically injecting unique, session-specific "canary tokens" into retrieved data and scanning LLM outputs for their presence, RAGuard provides a deterministic tripwire for token-level data leakage. It features a unique, opt-in "Zero-Width Stealth Mode" to differentiate it from existing solutions, ensuring minimal context window disruption while maintaining robust detection.

---

## 2. Problem Statement
RAG systems are inherently vulnerable to **Indirect Prompt Injection**. An attacker can craft a malicious query (or upload a poisoned document) that tricks the LLM into ignoring its system prompts and outputting the retrieved private context. 

**Why current defenses fail:**
- **Prompt Engineering:** Instructions like "do not leak data" are trivially bypassed by advanced jailbreaks.
- **Heuristic/LLM Scanners:** Using a secondary LLM to check outputs for PII is slow, expensive, and prone to false negatives.
- **Traditional WAFs:** Cannot distinguish between a legitimate summary and a malicious leak, as the exfiltrated data looks like a normal API response.
- **Existing Canary Tools:** Current open-source solutions rely on visible random strings, which waste context tokens and can be explicitly filtered out by sophisticated attackers.

---

## 3. Proposed Solution
RAGuard acts as a "tripwire" inside the LLM's context window. The solution operates in three deterministic steps:

1. **Dynamic Injection:** When the RAG retriever fetches documents, RAGuard intercepts the chunks. Based on user configuration, it injects a unique, session-specific token:
   - *Default Mode:* A highly random, obscure alphanumeric string (e.g., `x9Qm2_7z`). Guaranteed to survive all tokenizers.
   - *Stealth Mode (Opt-in):* A randomized sequence of zero-width Unicode characters (e.g., specific patterns of `U+200B` Zero Width Space and `U+200C` Zero Width Non-Joiner). This remains invisible to the user and minimizes visual context disruption.
2. **Augmented Generation:** The augmented context is passed to the LLM alongside the user's query.
3. **Output Interception:** Before the LLM's response is returned to the user, RAGuard scans the output string for the session's specific token.
   - **If detected:** The response is immediately blocked, a generic "Security Violation" error is returned, and a security alert is triggered.
   - **If not detected:** The response is deemed safe and passed through normally.

---

## 4. Objectives & Success Metrics
- **Performance:** Add <5ms of latency overhead per request for token generation and regex scanning.
- **Reliability:** Achieve 100% deterministic detection of the injected token *when the token is present in the output*.
- **Adoption (6 Months):** 
  - 500+ GitHub stars.
  - 5,000+ monthly PyPI downloads.
  - At least 3 external community contributors.
- **Developer Experience (DX):** Achieve a "drop-in" integration time of under 5 minutes for supported frameworks.

---

## 5. Project Scope

### Phase 1: V1 (Comprehensive Core & Major Frameworks)
- **Core Engine:** Framework-agnostic Python module for token generation, injection, and scanning.
- **Stealth Mode (Opt-in):** Implementation and tokenizer-validation of zero-width Unicode sequence injection alongside the default alphanumeric mode.
- **LangChain Integration:** Custom `BaseCallbackHandler` adapter (targeting the largest RAG developer surface).
- **LlamaIndex Integration:** Custom `NodePostprocessor` adapter (ensuring broad coverage of modern RAG stacks).
- **FastAPI Integration:** Standard HTTP middleware for custom, framework-less builds.
- **Documentation:** Comprehensive README, quick-start guides, adversarial test examples, and clear documentation on Stealth Mode limitations.

### Phase 1.1: V1 Expansion (Post-Traction)
- **Haystack Integration:** Custom `Component` adapter for deepset's enterprise-grade framework.

### Phase 2: V2 (Enterprise & Advanced Features)
- **Dify & RAGFlow:** Custom node/plugin integrations for visual RAG platforms.
- **Semantic Kernel:** Adapter for Microsoft's enterprise-grade Python SDK.
- **Native Webhooks:** Built-in, configurable alerting to Slack, Discord, or enterprise SIEMs.

### Out of Scope (For Now)
- Managed SaaS dashboard or centralized logging UI.
- Modifying the LLM's weights or requiring fine-tuning.

---

## 6. Target Audience
- **Primary:** AI/ML Engineers and Backend Developers building production RAG applications who need a reliable, low-overhead security layer.
- **Secondary:** Enterprise Security Teams requiring deterministic proof of basic data protection controls.
- **Tertiary:** Open-source contributors and security researchers.

---

## 7. Technical Requirements
- **Language:** Python 3.10+ (with full async/await support).
- **Dependencies:** Strictly minimal. Rely on standard library (`secrets`, `re`) and lightweight, trusted packages like `pydantic` for configuration validation.
- **Code Quality:** 
  - 100% type hinting (validated via `mypy` or `pyright`).
  - 95%+ unit and integration test coverage (via `pytest`).
  - Strict linting and formatting (via `Ruff`).
- **Testing Strategy:** 
  - Unit tests for core logic.
  - Mocked integration tests for framework adapters (LangChain, LlamaIndex, FastAPI).
  - **Tokenizer Validation Suite:** Dedicated tests to verify that zero-width sequences survive preprocessing in major LLM APIs (OpenAI, Anthropic, and local Ollama models).
  - **Adversarial Red-Teaming Suite:** A dedicated test module that intentionally attempts prompt injection to prove the middleware catches it.

---

## 8. Known Limitations (Crucial for Credibility)
To maintain trust with enterprise security teams, the documentation will explicitly state what RAGuard does **not** catch:
1. **Semantic Summarization:** If an attacker prompts the LLM to "summarize the retrieved text without using any special characters," the LLM may leak the *meaning* of the data without outputting the exact canary token.
2. **Encoded Leaks:** An attacker could prompt the LLM to output the context in Base64, bypassing a simple string match.
3. **Token Discovery:** A sophisticated attacker who reverse-engineers the application might guess the token format and explicitly instruct the LLM to omit it.
4. **Aggressive Normalization:** In rare cases, specific LLM endpoints may aggressively strip all zero-width characters during preprocessing, causing Stealth Mode to fail silently (which is why the default alphanumeric mode remains the recommended safe choice).

**Positioning:** RAGuard is a deterministic tripwire for naive, token-level exfiltration, not a comprehensive Data Loss Prevention (DLP) system. It significantly raises the attacker's effort and catches the vast majority of automated injection attacks.

---

## 9. Open Source Strategy
- **Licensing:** MIT or Apache 2.0. Permissive licenses encourage both personal use and enterprise adoption without legal friction.
- **Community Files:** Include standard `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md` (for responsible vulnerability disclosure).
- **Onboarding:** Tag initial issues as `good first issue` and `help wanted`.
- **CI/CD:** GitHub Actions pipeline enforcing tests, linting, type checking, and automated PyPI publishing on tagged releases.

---

## 10. Approval & Next Steps
- [x] Phase 1: Deep Analysis & Threat Modeling (`analysis.md` complete and revised)
- [x] Phase 2: Product Requirements Document (`prd.md` complete and revised with Stealth Mode + LlamaIndex in V1)
- [ ] Phase 3: Tech Stack Finalization & Repository Initialization
- [ ] Phase 4: System Design & Architecture Diagrams
- [ ] Phase 5: Development Sprint 1 (Core Engine + Stealth Mode + LangChain/LlamaIndex Adapters)