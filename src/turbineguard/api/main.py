"""FastAPI REST service for TurbineGuard simulation, fault injection, and verification."""

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from turbineguard.analytics.analyzer import TelemetryAnalyzer
from turbineguard.config import SimulationConfig
from turbineguard.db import DatabaseManager
from turbineguard.faults.fault_injection import FaultInjector
from turbineguard.faults.fault_types import FAULT_CRITERIA_MAP, FaultTypeEnum
from turbineguard.models import (
    FaultInjectRequest,
    FaultSeverity,
    SimulationStartRequest,
)
from turbineguard.reporting.report_generator import ReportGenerator
from turbineguard.simulator.environment import WindScenarioType
from turbineguard.validation.validator import ValidationEngine, ValidationSuiteResult

app = FastAPI(
    title="TurbineGuard API",
    description="Wind Turbine Controller Validation, Simulation, and Automated Testing Platform REST API",
    version="1.0.0"
)

# Enable CORS for dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State Container
class ServiceState:
    def __init__(self):
        self.config = SimulationConfig()
        self.db = DatabaseManager(self.config.db_path)
        self.validator = ValidationEngine(self.config)
        self.reporter = ReportGenerator(self.config.reports_dir)
        self.fault_injector = FaultInjector()
        
        # Latest test run cache
        self.latest_telemetry: list[Any] = []
        self.latest_validation: ValidationSuiteResult | None = None
        self.latest_run_id: str = "INIT"
        self.is_running: bool = False
        self.sim_status: str = "IDLE"

state = ServiceState()

# Mount dashboard static files if directory exists
dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "dashboard")
if os.path.exists(dashboard_dir):
    app.mount("/dashboard", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")


@app.get("/", response_class=HTMLResponse)
def root():
    """Redirect to dashboard or return health greeting."""
    index_file = os.path.join(dashboard_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>TurbineGuard API is Running</h1><p>Visit <a href='/docs'>/docs</a> for Swagger UI.</p>")


@app.get("/health")
def get_health():
    """Service health and system status check."""
    return {
        "status": "HEALTHY",
        "service": "TurbineGuard Platform",
        "version": "1.0.0",
        "db_connected": True
    }


@app.get("/simulation/status")
def get_simulation_status():
    """Retrieves current simulation status, telemetry sample, and active state."""
    latest_tel = state.latest_telemetry[-1] if state.latest_telemetry else None
    return {
        "sim_status": state.sim_status,
        "is_running": state.is_running,
        "latest_run_id": state.latest_run_id,
        "total_data_points": len(state.latest_telemetry),
        "latest_point": latest_tel.__dict__ if latest_tel else None
    }


@app.post("/simulation/start")
def start_simulation(req: SimulationStartRequest):
    """Executes a closed-loop wind turbine simulation run."""
    state.is_running = True
    state.sim_status = "RUNNING"
    run_id = f"RUN-{int(os.times().system * 1000)}"
    state.latest_run_id = run_id

    # Configure wind scenario
    scenario_type = WindScenarioType.CONSTANT
    for st in WindScenarioType:
        if st.value.lower() == req.wind_scenario.lower():
            scenario_type = st
            break

    # Add any requested faults
    for f in req.injected_faults:
        try:
            ftype = FaultTypeEnum(f.get("type"))
            state.fault_injector.add_fault(
                fault_id=f.get("fault_id", f"F-{len(state.fault_injector.scheduled_faults)+1}"),
                fault_type=ftype,
                start_time_s=float(f.get("start_time_s", 5.0)),
                duration_s=float(f.get("duration_s", 5.0)),
                severity=FaultSeverity(f.get("severity", "HIGH")),
                magnitude=float(f.get("magnitude", 1.0))
            )
        except (ValueError, KeyError, TypeError):
            continue

    telemetry = state.validator.run_closed_loop_simulation(
        duration_s=req.duration_s,
        wind_scenario=scenario_type,
        base_wind_speed_ms=req.base_wind_speed_ms,
        fault_injector=state.fault_injector
    )
    state.latest_telemetry = telemetry
    state.is_running = False
    state.sim_status = "COMPLETED"

    # Save to SQLite
    df = TelemetryAnalyzer.to_dataframe(telemetry)
    metrics = TelemetryAnalyzer.compute_metrics(df)
    
    state.db.save_run(
        run_id=run_id,
        scenario_name=req.wind_scenario,
        duration_s=req.duration_s,
        dt=state.config.dt,
        total_steps=len(telemetry),
        final_state=telemetry[-1].operating_state.value if telemetry else "UNKNOWN",
        telemetry=[t.__dict__ for t in telemetry]
    )

    return {
        "run_id": run_id,
        "status": "COMPLETED",
        "duration_s": req.duration_s,
        "data_points": len(telemetry),
        "final_state": telemetry[-1].operating_state.value if telemetry else "UNKNOWN",
        "metrics": metrics.__dict__
    }


@app.post("/simulation/reset")
def reset_simulation():
    """Resets simulator buffers and fault injectors."""
    state.fault_injector.clear()
    state.latest_telemetry.clear()
    state.sim_status = "IDLE"
    state.is_running = False
    return {"status": "RESET_OK"}


@app.post("/faults/inject")
def inject_fault(req: FaultInjectRequest):
    """Schedules a fault in the fault injection engine."""
    f = state.fault_injector.add_fault(
        fault_id=f"F-{len(state.fault_injector.scheduled_faults)+1:03d}",
        fault_type=req.fault_type,
        start_time_s=req.start_time_s,
        duration_s=req.duration_s,
        severity=req.severity,
        magnitude=req.magnitude,
        description=req.description or f"Injected {req.fault_type.value}"
    )
    return {
        "status": "SCHEDULED",
        "fault": f.__dict__
    }


@app.get("/faults")
def list_faults():
    """Lists all supported fault types and scheduled/executed faults."""
    supported = [
        {"type": ft.value, "description": FAULT_CRITERIA_MAP[ft].description if ft in FAULT_CRITERIA_MAP else ""}
        for ft in FaultTypeEnum
    ]
    return {
        "supported_faults": supported,
        "scheduled_faults": [f.__dict__ for f in state.fault_injector.scheduled_faults],
        "results": [r.__dict__ for r in state.fault_injector.results]
    }


@app.post("/validation/run")
def run_validation():
    """Triggers the full automated engineering validation suite."""
    suite_res = state.validator.validate_all()
    state.latest_validation = suite_res
    
    # Generate reports
    html_path = state.reporter.generate_html_report(suite_res)
    pdf_path = state.reporter.generate_pdf_report(suite_res)
    csv_path = state.reporter.export_csv(suite_res)
    json_path = state.reporter.export_json(suite_res)

    return {
        "suite_name": suite_res.suite_name,
        "total_requirements": suite_res.total_requirements,
        "passed": suite_res.passed_count,
        "failed": suite_res.failed_count,
        "pass_rate_pct": suite_res.pass_rate_pct,
        "execution_time_ms": suite_res.total_execution_time_ms,
        "failed_ids": suite_res.failed_req_ids,
        "reports": {
            "html": html_path,
            "pdf": pdf_path,
            "csv": csv_path,
            "json": json_path
        }
    }


@app.get("/validation/results")
def get_validation_results():
    """Returns latest requirement verification scorecard."""
    if not state.latest_validation:
        raise HTTPException(status_code=404, detail="No validation run executed yet. Call POST /validation/run")
    return state.latest_validation.__dict__


@app.get("/reports/latest")
def get_latest_report():
    """Serves the latest generated HTML validation report."""
    report_file = os.path.join(state.config.reports_dir, "validation_report.html")
    if not os.path.exists(report_file):
        raise HTTPException(status_code=404, detail="No report generated yet.")
    return FileResponse(report_file, media_type="text/html")


@app.get("/metrics")
def get_metrics():
    """Returns current telemetry metrics summary."""
    if not state.latest_telemetry:
        return {"status": "NO_DATA"}
    df = TelemetryAnalyzer.to_dataframe(state.latest_telemetry)
    metrics = TelemetryAnalyzer.compute_metrics(df)
    return metrics.__dict__
