# TurbineGuard User Guide & Operational Manual

## Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13
- Pip package manager
- Optional: Docker / Docker Compose

## Quick Start Installation
```bash
# 1. Clone repository
git clone https://github.com/simran846/turbineguard.git
cd turbineguard

# 2. Install dependencies & package in editable mode
pip install -r requirements.txt
pip install -e .
```

## Running the 5-Minute Interview Demonstration
Execute the interactive demonstration showcasing 10 guided verification steps:
```bash
python scripts/demo_interview.py
```

## Running the CLI Automated Validation Suite
Execute the formal requirements validation suite and automatically generate HTML, PDF, CSV, and JSON reports:
```bash
python scripts/run_validation_suite.py
```
Generated reports are stored in:
- HTML Report: `reports/validation_report.html`
- PDF Report: `reports/validation_report.pdf`
- CSV Results: `reports/validation_results.csv`
- Machine-Readable JSON: `reports/validation_report.json`

## Launching the REST API and Interactive Dashboard
Start the FastAPI server:
```bash
uvicorn turbineguard.api.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser to:
- **Interactive Control Dashboard:** `http://localhost:8000/dashboard` or `http://localhost:8000/`
- **Interactive OpenAPI (Swagger) Documentation:** `http://localhost:8000/docs`
- **Alternative ReDoc API Documentation:** `http://localhost:8000/redoc`

## Running via Docker Compose
```bash
docker compose up --build
```
Access the dashboard at `http://localhost:8000`.
