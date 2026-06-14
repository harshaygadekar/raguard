# Phase 3 Execution Plan: Tech Stack, Architecture & Repository Setup

**Date:** 2026-06-03  
**Status:** Pending User Review & Approval  

---

## 1. Phase 3 Objectives
- Finalize the exact technical stack and dependencies.
- Define the system architecture and adapter patterns.
- Generate the complete local repository structure, configuration files, and initial documentation.
- Set up automated CI/CD workflows for quality assurance.

---

## 2. Task Breakdown: What I Will Do (AI)
Once you approve this plan, I will independently generate the following files in your local project directory:

1. **Project Configuration**:
   - `pyproject.toml`: Complete Python project configuration (dependencies, build system, metadata).
   - `.gitignore`: Standard Python/GitHub ignore rules.
   - `LICENSE`: MIT License text.
2. **Directory Structure**:
   - Create `src/raguard/` (Core engine, token generator, scanner).
   - Create `src/raguard/adapters/` (LangChain, LlamaIndex, FastAPI stubs).
   - Create `tests/` (Unit tests, adversarial red-teaming stubs).
   - Create `examples/` (Usage examples for each adapter).
3. **System Architecture Document**:
   - `docs/architecture.md`: Detailed breakdown of the Core Engine and Adapter pattern, including Mermaid.js diagrams.
4. **CI/CD Pipeline**:
   - `.github/workflows/ci.yml`: GitHub Actions workflow to run `ruff` (linting/formatting), `mypy` (type checking), and `pytest` (testing) on every push and PR.
5. **Initial README**:
   - `README.md`: A professional, draft README with project description, installation instructions, and a basic usage example.

---

## 3. Task Breakdown: What You Need to Do (User)
To ensure you maintain full ownership and control, please handle the following:

1. **Review this Plan**: Confirm the proposed tech stack and directory structure below are acceptable.
2. **Create GitHub Repository**: Go to GitHub and create a new, empty public repository named `raguard` (or your preferred name). Do not initialize it with a README or .gitignore.
3. **Local Git Initialization**: After I generate the files, you will run:
   ```bash
   git init
   git add .
   git commit -m "chore: initial project setup and phase 3 artifacts"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```
4. **PyPI Account (Future)**: Ensure you have a PyPI account and an API token ready for when we reach the publishing stage (not needed for Phase 3).

---

## 4. Proposed Tech Stack & Dependencies (For Review)
- **Language**: Python 3.10+ (ensures modern type hinting and async support).
- **Core Dependencies**: 
  - None required for the absolute core (uses built-in `secrets` and `re`).
  - `pydantic` (v2): For robust, type-safe configuration validation.
- **Development Dependencies**:
  - `pytest` + `pytest-asyncio`: For unit and integration testing.
  - `ruff`: For blazing-fast linting and code formatting (replaces black/flake8).
  - `mypy`: For strict static type checking.
  - `langchain` & `llama-index` (as optional/dev dependencies): To write and run adapter integration tests.
- **Packaging**: `build` and `twine` (or modern `hatch`/`poetry` - I recommend standard `pyproject.toml` with `build` for simplicity).

---

## 5. Proposed Directory Structure (For Review)
```text
raguard/
├── .github/
│   └── workflows/
│       └── ci.yml                 # Automated testing and linting
├── docs/
│   └── architecture.md            # System design and Mermaid diagrams
├── examples/
│   ├── core_usage.py              # Basic core engine example
│   ├── langchain_example.py       # LangChain adapter example
│   ├── llamaindex_example.py      # LlamaIndex adapter example
│   └── fastapi_example.py         # FastAPI middleware example
├── src/
│   └── raguard/
│       ├── __init__.py
│       ├── core.py                # Token generation, injection, scanning logic
│       ├── config.py              # Pydantic configuration models
│       └── adapters/
│           ├── __init__.py
│           ├── langchain.py       # LangChain CallbackHandler
│           ├── llamaindex.py      # LlamaIndex NodePostprocessor
│           └── fastapi.py         # FastAPI HTTP Middleware
├── tests/
│   ├── __init__.py
│   ├── test_core.py               # Unit tests for core logic
│   ├── test_stealth_mode.py       # Tokenizer validation tests
│   └── test_adversarial.py        # Red-teaming simulation tests
├── .gitignore
├── LICENSE                        # MIT License
├── pyproject.toml                 # Project metadata and dependencies
└── README.md                      # Initial project documentation
```

---

## 6. Next Steps
1. **You review** this document, the tech stack, and the directory structure.
2. **You reply** with "Approved" or request any modifications.
3. **I will execute** all AI tasks listed in Section 2, generating the files locally in your project directory.
4. **You perform** the Git initialization and push to your new GitHub repository.
