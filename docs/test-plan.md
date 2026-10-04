# TurbineGuard Automated Test Plan & Quality Assurance Strategy

## Verification Hierarchy Overview
The TurbineGuard verification strategy ensures full traceability from mathematical physical laws to high-level system requirements:

| Test Layer | Framework | Target Scope | Execution Time |
| :--- | :--- | :--- | :--- |
| **Unit Tests** | `pytest -m unit` | Physics formulas, PID math, sensor noise, safety limits | ~0.8s |
| **Integration Tests** | `pytest -m integration` | Closed-loop dynamics, state transitions, REST endpoints | ~1.2s |
| **Safety & Fault Tests** | `pytest -m "safety or fault"` | Trip latching, sensor dropout failsafe, response latency | ~0.9s |
| **Validation Suite** | `pytest -m validation` | Formal requirements REQ-001 through REQ-012 | ~1.5s |
| **Complete Suite** | `python -m pytest` | All 65 tests | ~2.5s |

## Test Markers
- `@pytest.mark.unit`: Fast unit tests with mocked or isolated plant models.
- `@pytest.mark.integration`: Multi-component closed-loop simulations with full dynamic stepping.
- `@pytest.mark.safety`: Critical safety limits, envelope bounds, and emergency stop latching tests.
- `@pytest.mark.fault`: Injected failure scenarios verifying latency and mitigation accuracy.
- `@pytest.mark.validation`: Requirements verification suite evaluated against numerical tolerances.

## Executing the Test Suite
```bash
# Run all tests
pytest -v

# Run only safety and fault tests
pytest -m "safety or fault" -v

# Run with test coverage
pytest --cov=src/turbineguard tests/
```
