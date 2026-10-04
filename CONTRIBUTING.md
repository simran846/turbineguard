# Contributing to TurbineGuard

Thank you for your interest in contributing to **TurbineGuard**!

## Code Quality Standards
1. **Formatting & Linting:** All code must pass `ruff check src tests` with zero warnings.
2. **Type Hints:** Use explicit Python type hints throughout the codebase.
3. **Automated Testing:** Every new controller feature, safety threshold, or physics model must be accompanied by comprehensive `pytest` tests.
4. **Deterministic Verification:** Ensure tests do not rely on non-deterministic random seeds.

## Pull Request Process
1. Fork the repository and create a feature branch (`git checkout -b feat/your-feature-name`).
2. Implement your changes following clean OOP and SOLID principles.
3. Run the full validation suite:
   ```bash
   python -m pytest -v
   python -m ruff check src tests
   python scripts/run_validation_suite.py
   ```
4. Commit using conventional commit format (`feat: ...`, `test: ...`, `fix: ...`, `docs: ...`).
5. Open a Pull Request against `main` or `develop`.
