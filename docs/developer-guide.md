# TurbineGuard Developer Guide

## Architecture Structure
```
src/turbineguard/
├── config.py         # Configuration dataclasses (Turbine, Safety, Controller, Simulation)
├── models.py         # Domain models, dataclasses, and Pydantic schemas
├── db.py             # SQLite persistence using SQLAlchemy ORM
├── logger.py         # Structured JSON and console logging
├── simulator/        # Physical plant, sensors, and wind inflow models
├── controller/       # Pitch, torque, safety supervisory, and FSM controllers
├── faults/           # Fault injection engine and latency verification
├── validation/       # Requirements specification catalog and validation harness
├── analytics/        # Pandas metrics computation and Matplotlib chart generator
├── reporting/        # HTML, PDF, CSV, and JSON report generator
└── api/              # FastAPI REST endpoints and static file mounts
```

## Adding a New Engineering Requirement
1. Open `src/turbineguard/validation/requirements.py`.
2. Add a new `ValidationRequirement` entry with `req_id`, `title`, `acceptance_criteria`, and `tolerance`.
3. In `src/turbineguard/validation/validator.py`, add evaluation scenario logic inside `validate_all()`.
4. In `tests/validation/test_requirements_suite.py`, add a dedicated `@pytest.mark.validation` test function.

## Adding a New Fault Injection Type
1. Add an enum entry in `src/turbineguard/models.py` (`FaultTypeEnum`).
2. Add acceptance criteria in `src/turbineguard/faults/fault_types.py` (`FAULT_CRITERIA_MAP`).
3. Implement physical perturbation logic in `src/turbineguard/faults/fault_injection.py` (`_apply_fault_impact`).
4. Add verification unit test in `tests/unit/test_fault_engine.py`.

## Static Analysis & Quality Standards
```bash
# Linting & code style (Ruff)
python -m ruff check src tests

# Run test suite
python -m pytest -v
```
