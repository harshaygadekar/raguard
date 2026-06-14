## Phase 1: Deep Analysis & Threat Modeling

- Competitor Deep-Dive: Analyze canari-llm, LLM-Canary, and academic papers to identify their exact gaps (e.g., lack of framework integrations, poor DX).
- Threat Modeling: Define the exact attack vectors we are mitigating (e.g., indirect prompt injection, context exfiltration) and what is explicitly out of scope (e.g., preventing the LLM from hallucinating).

## Phase 2: Product Requirements Document (PRD)

- Problem & Solution: Formalize the "honeypot" concept we discussed.
- Objectives: Zero-latency overhead, 100% deterministic detection, framework-agnostic design.
- Scope:
  - V1: Python package with core engine + LangChain/LlamaIndex adapters.
  - V2: Node.js/TypeScript (NPM) package + FastAPI/Express middleware.
- Delivery: Open-source GitHub repository, PyPI package, comprehensive documentation.

## Phase 3: Tech Stack Selection

- Language: Python 3.10+ (primary), TypeScript (future V2).
- Core Dependencies: Minimal. cryptography or secrets for token generation. pydantic for robust configuration validation.
- Tooling: uv or Poetry for dependency management, Ruff for linting/formatting, pytest for testing.
- CI/CD: GitHub Actions for automated testing, type checking, and PyPI publishing on release.

## Phase 4: System Design & Architecture

- Core Engine: Stateless, async-compatible module for token generation, injection, and scanning.
- Adapter Pattern: Clean interfaces for integrations (e.g., LangChainCallbackHandler, LlamaIndexNodePostprocessor) so the core logic remains decoupled from third-party frameworks.
- Stealth Mechanism: Design the token format (e.g., random alphanumeric vs. zero-width Unicode characters) to minimize context window pollution.

## Phase 5: Testing Strategy

- Unit Tests: 100% coverage on the core engine (token generation, regex scanning).
- Integration Tests: Mocked tests against LangChain and LlamaIndex to ensure the adapters hook into the lifecycle correctly.
- Adversarial Testing (Red Teaming): A dedicated test suite that intentionally tries to bypass the canary using known prompt injection techniques to prove the middleware catches them.

## Phase 6: Dev Environment Setup

- Initialize the Git repository with a standard open-source structure (src/, tests/, examples/, docs/).
- Configure pre-commit hooks to enforce code quality before any commit.
- Set up a local, free LLM (like Ollama with Llama 3) for running integration tests without incurring API costs.

## Phase 7: Development & Iterative Testing

- Sprint 1: Build and test the Core Engine.
- Sprint 2: Build and test the LangChain adapter.
- Sprint 3: Build and test the LlamaIndex adapter.
- Sprint 4: Write comprehensive examples and documentation.

## Phase 8: Release, Packaging & Open Source Launch

- Finalize pyproject.toml with proper metadata, classifiers, and dependencies.
- Draft a high-quality README.md (the most important file for open-source adoption) with a clear "Why", "How it works", and "Quick Start" guide.
- Add an open-source license (e.g., MIT or Apache 2.0).
- Publish to PyPI and create the v1.0.0 GitHub Release.

## Phase 9: Post-Launch & Future Roadmap (The "Even More")

- Monitor initial GitHub issues and PyPI downloads.
- Begin architectural planning for the TypeScript/NPM port (Phase 2 scope).
- Create a simple Streamlit or Gradio demo app hosted on Hugging Face Spaces so users can try it instantly without installing anything.
