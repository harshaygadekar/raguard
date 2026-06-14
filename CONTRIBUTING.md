# Contributing to RAGuard

Thank you for your interest in contributing to RAGuard! As a security-focused project, we appreciate community efforts to make RAG applications safer and more robust against context exfiltration.

This guide outlines our development workflow, coding standards, and how to get started.

---

## 🚀 Quick Start Developer Setup

RAGuard requires **Python 3.10+**. Follow these steps to set up your local development environment:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-username/RAGuard.git
   cd RAGuard
   ```

2. **Create and Activate a Virtual Environment:**
   ```bash
   python -m venv .venv
   # On Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies in Editable/Dev Mode:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install Pre-commit Hooks:**
   We use `pre-commit` to run linting, formatting, and tests automatically before each commit.
   ```bash
   pre-commit install
   ```

---

## 🛠️ Development Workflow & Quality Gates

To ensure stability and security, every pull request must pass three quality checks before merge:

### 1. Linting & Formatting (`ruff`)
We use **Ruff** for fast linting and formatting. You can run checks manually:
```bash
# Run lint checks
ruff check .

# Autofix fixable issues
ruff check . --fix

# Format the code style
ruff format .
```

### 2. Static Type Checking (`mypy`)
All core code must have 100% type annotations. We enforce strict mode via `mypy`:
```bash
mypy src/
```

### 3. Testing & Coverage (`pytest`)
All new features, adapters, and bug fixes must include unit or integration tests in the `tests/` directory.
- We require a minimum of **85% code coverage** to pass CI.
- Run the test suite:
  ```bash
  # PowerShell (Windows)
  $env:PYTHONPATH=".;tests"
  pytest

  # Bash (macOS/Linux)
  PYTHONPATH=".:tests" pytest
  ```

---

## 📦 Project Structure

- `src/raguard/`: Main codebase.
  - `core.py`: Core token injection and exfiltration scanning engine.
  - `config.py`: Configuration schemas using Pydantic.
  - `exceptions.py`: Custom security and import exception models.
  - `adapters/`: Middleware/callback implementations for frameworks (LangChain, LlamaIndex, FastAPI).
- `tests/`: Test suite.
  - `test_core.py`: Core functionality tests.
  - `test_adapters.py`: Adapter-specific validation tests.
  - `test_adversarial.py`: Red-teaming test suite (simulating prompt injections).
  - `test_tokenizer_validation.py`: Verifies zero-width tokens survive various tokenizers.
- `examples/`: Code examples showcasing how to integrate RAGuard.

---

## 🤝 Pull Request Guidelines

1. **Branch Naming:** Keep it descriptive, e.g., `feat/add-haystack-adapter` or `fix/webhook-retry`.
2. **Conventional Commits:** Use the [Conventional Commits](https://www.conventionalcommits.org/) format for commit messages (e.g., `feat(adapters): add new framework callback`).
3. **Keep Changes Focused:** Ensure every changed line is directly related to the issue/feature you are implementing. Avoid mixing unrelated refactoring into functional PRs.
4. **Update Documentation:** If your PR adds a config option or changes an API, update the `README.md` and inline docstrings accordingly.

---

## 🔒 Security Vulnerability Reporting

If you find a security vulnerability, please **do not** open a public issue. Instead, report it privately according to our security guidelines in `SECURITY.md` (or contact the maintainers directly).
