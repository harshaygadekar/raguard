```markdown
# raguard Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill introduces the core development patterns and conventions used in the `raguard` Python repository. It covers file naming, import/export styles, commit message conventions, and testing patterns. By following these guidelines, contributors can ensure consistency and maintainability across the codebase.

## Coding Conventions

### File Naming
- **Style:** camelCase
- **Example:**  
  ```plaintext
  userProfile.py
  dataManager.py
  ```

### Import Style
- **Style:** Relative imports
- **Example:**
  ```python
  from .utils import parseData
  from .models import User
  ```

### Export Style
- **Style:** Named exports (using `__all__`)
- **Example:**
  ```python
  __all__ = ['User', 'parseData']
  ```

### Commit Message Conventions
- **Type:** Conventional commits
- **Prefix:** `feat`
- **Example:**
  ```
  feat: add user authentication to login flow
  ```

## Workflows

### Feature Development
**Trigger:** When adding a new feature to the codebase  
**Command:** `/feature-development`

1. Create a new branch for your feature.
2. Implement the feature using camelCase file naming and relative imports.
3. Export new functions/classes using named exports (`__all__`).
4. Write or update tests in files matching `*.test.*`.
5. Commit changes using the `feat` prefix and a descriptive message.
6. Open a pull request for review.

### Testing
**Trigger:** When verifying code correctness  
**Command:** `/run-tests`

1. Identify or create test files using the `*.test.*` pattern.
2. Run the test suite using the project's preferred test runner (framework unknown; check project documentation or use `python -m unittest discover` as a fallback).
3. Ensure all tests pass before merging code.

## Testing Patterns
- **Test File Naming:** Files should match the pattern `*.test.*` (e.g., `userManager.test.py`).
- **Framework:** Not explicitly specified; check for `unittest` or other frameworks in the codebase.
- **Example Test File:**
  ```python
  # userManager.test.py
  import unittest
  from .userManager import UserManager

  class TestUserManager(unittest.TestCase):
      def test_add_user(self):
          manager = UserManager()
          self.assertTrue(manager.add_user('alice'))
  ```

## Commands
| Command               | Purpose                                    |
|-----------------------|--------------------------------------------|
| /feature-development  | Start a new feature using repo conventions |
| /run-tests            | Run all tests in the codebase              |
```