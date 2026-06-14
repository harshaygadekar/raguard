# Phase 6 Plan: Dev Environment Setup

## Goal
Set up developer infrastructure that enforces quality before commits, validates zero-width stealth tokens against real tokenizers, and enables free local LLM integration testing.

---

## Architecture Decision: What Ollama Testing Adds

Current tests mock LLM responses (fast, deterministic, no API keys). Ollama adds:
- **Real tokenizer validation**: Does Llama 3's tokenizer preserve zero-width characters? (Claude/OpenAI may strip them)
- **End-to-end proof**: A full pipeline with a real LLM that proves the tripwire catches real exfiltration
- **Free**: No API costs, fully local

The Ollama tests are **supplementary** — they don't replace the mock tests. They live in a separate script (`tests/test_ollama_integration.py`) and require `ollama` to be installed and running.

---

## Implementation Plan

### Step 1: Pre-commit Hooks

**File**: `.pre-commit-config.yaml`

Hooks:
| Hook | What it does | Failure mode |
|------|-------------|--------------|
| `ruff check` | Lint all Python files | Block commit |
| `ruff format --check` | Verify formatting | Block commit |
| `mypy src/` | Type check production code | Block commit |
| `pytest tests/ -x` | Run all tests (exit fast) | Block commit |
| `check-yaml` | Validate YAML files | Block commit |
| `check-toml` | Validate TOML files | Block commit |
| `trailing-whitespace` | Remove trailing whitespace | Auto-fix |
| `end-of-file-fixer` | Ensure newline at EOF | Auto-fix |

**Update**: `pyproject.toml` — add `[tool.pytest.ini_options]` with `addopts = "--cov=src/raguard --cov-report=term-missing --cov-fail-under=85"` so coverage threshold blocks commits.

### Step 2: Tokenizer Validation Suite

**File**: `tests/test_tokenizer_validation.py`

This is critical per PRD §7: "tokenizer validation suite" was named as a V1 requirement.

Tests validate that stealth tokens survive tokenization:

| Test | What it checks | Why |
|------|---------------|-----|
| `test_zero_width_survives_unicode_normalization` | NFC/NFD/NFKC normalization doesn't destroy tokens | Tokenizers often normalize Unicode |
| `test_zero_width_not_stripped_by_whitespace_cleaning` | `.strip()` doesn't remove zero-width | Some APIs strip "whitespace" from context |
| `test_zero_width_survives_string_operations` | Common Python string ops preserve tokens | Confidence baseline before real tokenizer tests |
| `test_alphanumeric_survives_all_transforms` | Alphanumeric tokens are resilient | Guaranteed reliability mode |
| `test_zero_width_is_detectable_after_injection` | Full inject→extract→detect pipeline with stealth | End-to-end stealth confidence |

These tests use Python's `unicodedata` module (stdlib) — no external deps. They test against Unicode normalization forms that real tokenizers apply.

### Step 3: Ollama Integration

**File**: `tests/test_ollama_integration.py` (separate from regular test suite)

**Prerequisites**: 
- Ollama installed locally
- `ollama pull llama3.2:1b` (smallest model, fast download)
- `pip install ollama`

**Test scenarios** (each requires Ollama running, skipped otherwise):

| Test | Scenario | Expected |
|------|----------|----------|
| `test_safe_summary_with_ollama` | Inject token → ask Llama to summarize → check output | SAFE (summary doesn't contain token) |
| `test_exfiltration_with_ollama` | Inject token → ask Llama to output context verbatim → check output | DETECTED |
| `test_stealth_token_survives_ollama` | Inject zero-width token → ask Llama to repeat context → token in output | DETECTED (proves Llama 3 doesn't strip ZW chars) |
| `test_ollama_availability` | Connect to Ollama, list models | Skip test if unavailable |

**Runner**: `python tests/test_ollama_integration.py` (standalone script, not part of `pytest tests/` by default — avoids CI failures on non-Ollama machines)

### Step 4: CI/CD Update

**Update**: `.github/workflows/ci.yml` — add coverage threshold reporting. The pre-commit YAML check and TOML check should pass.

### Step 5: Developer Documentation

**Create**: `CONTRIBUTING.md` 

Contents:
- Prerequisites (Python 3.10+, Ollama optional)
- Setup: clone, venv, `pip install -e ".[dev]"`, `pre-commit install`
- Running tests: `pytest tests/`, `python tests/test_ollama_integration.py`
- Running linting: `ruff check . && ruff format --check .`
- Running type checks: `mypy src/`
- PR checklist

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `.pre-commit-config.yaml` | **Create** | Pre-commit hook definitions |
| `tests/test_tokenizer_validation.py` | **Create** | ~5 tests for Unicode/tokenizer edge cases |
| `tests/test_ollama_integration.py` | **Create** | ~4 real-LLM tests (skipped when Ollama unavailable) |
| `.github/workflows/ci.yml` | **Modify** | Add coverage threshold to CI |
| `pyproject.toml` | **Modify** | Add coverage threshold + pre-commit to dev deps |
| `CONTRIBUTING.md` | **Create** | Developer onboarding guide |

---

## Verification
```bash
# Pre-commit
pre-commit install
pre-commit run --all-files

# Tokenizer validation
pytest tests/test_tokenizer_validation.py -v

# Ollama (requires Ollama running)
pip install ollama
ollama pull llama3.2:1b
python tests/test_ollama_integration.py

# Full suite
pytest tests/ -v

# CI validation (simulate)
ruff check . && ruff format --check . && mypy src/ && pytest tests/ --cov=src/raguard --cov-fail-under=85
```

---

## Expected Outcomes
- Pre-commit blocks unformatted/lint-error/type-error/failing-test commits
- Tokenizer validation proves zero-width tokens survive Unicode normalization
- Ollama integration provides real-LLM smoke tests (free, local)
- CONTRIBUTING.md gives new developers a clear path from clone to first PR
- CI enforces 85% coverage threshold
