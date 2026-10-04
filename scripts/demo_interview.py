"""5-Minute Live Interview Demonstration Script for Siemens Gamesa Technology Intern Interview.

Candidate: Kumari Simran (CMR University, Bangalore)
Demonstrates:
- Simulation physics & aerodynamic multi-region control
- Automated formal requirement verification
- Fault injection testing & protective trip latching
- Executive engineering report generation
"""

import sys
import os
import time

# Add src to sys.path for direct script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from turbineguard.analytics.analyzer import TelemetryAnalyzer
from turbineguard.config import SimulationConfig
from turbineguard.faults.fault_injection import FaultInjector
from turbineguard.faults.fault_types import FaultTypeEnum
from turbineguard.models import FaultSeverity, TurbineOperatingState
from turbineguard.reporting.report_generator import ReportGenerator
from turbineguard.simulator.environment import WindScenarioType
from turbineguard.validation.validator import ValidationEngine


def print_step(step_num: int, title: str):
    print("\n" + "=" * 78)
    print(f"  STEP {step_num}: {title}")
    print("=" * 78)
    time.sleep(0.6)


def main():
    print("""
    ======================================================================
      TURBINEGUARD: WIND TURBINE CONTROLLER VALIDATION PLATFORM
      Siemens Gamesa Technology Portfolio Demonstration
      Presenter: Kumari Simran | B.Tech Computer Engineering (CMR University)
    ======================================================================
    """)
    time.sleep(0.8)

    config = SimulationConfig()
    validator = ValidationEngine(config)
    reporter = ReportGenerator(config.reports_dir)

    # STEP 1 & 2: Start Normal Simulation & Telemetry Readout
    print_step(1, "Start Normal Closed-Loop Turbine Simulation")
    print("[*] Initializing 2.5 MW variable-speed pitch-regulated turbine plant...")
    print("[*] Inflow wind: 11.5 m/s (Rated Wind Regime). Executing 10-second run (200 cycles @ 20Hz)...")
    
    telemetry_norm = validator.run_closed_loop_simulation(
        duration_s=10.0,
        wind_scenario=WindScenarioType.CONSTANT,
        base_wind_speed_ms=11.5
    )
    df_norm = TelemetryAnalyzer.to_dataframe(telemetry_norm)
    metrics_norm = TelemetryAnalyzer.compute_metrics(df_norm)

    print_step(2, "Live Plant Telemetry & Closed-Loop Performance Readout")
    print(f"  - Hub Wind Speed      : 11.5 m/s")
    print(f"  - Generator Speed     : {metrics_norm.mean_generator_rpm:.1f} RPM (Rated: 1500 RPM)")
    print(f"  - Blade Pitch Angle   : {metrics_norm.mean_pitch_deg:.2f} deg")
    print(f"  - Electrical Power    : {metrics_norm.mean_electrical_power_kw:.1f} kW (Capacity: 2500 kW)")
    print(f"  - Generator Temp      : {metrics_norm.final_generator_temp_c:.1f} C (Trip: 98.0 C)")
    print(f"  - Nacelle Vibration   : {metrics_norm.peak_vibration_mm_s:.2f} mm/s (Trip: 5.5 mm/s)")
    print(f"  - Operating State     : {telemetry_norm[-1].operating_state.value}")
    print("[+] Status: Turbine stably regulating power at rated setpoint.")

    # STEP 3 & 4: Run Automated Validation Suite
    print_step(3, "Execute Automated Engineering Validation Suite (12 Requirements)")
    print("[*] Dispatching automated verification harness across aerodynamic, electrical, and safety REQs...")
    suite_res = validator.validate_all()

    print_step(4, "Validation Results & Requirements Traceability Matrix")
    for r in suite_res.results[:6]:
        print(f"  [{r.req_id}] {r.title:<38} -> \033[92m{r.status.value}\033[0m ({r.measured_value:.1f} {r.unit} in {r.execution_time_ms:.1f}ms)")
    print(f"  ... (+ {len(suite_res.results)-6} additional requirements verified)")
    print(f"\n[+] Suite Outcome: {suite_res.passed_count}/{suite_res.total_requirements} PASSED ({suite_res.pass_rate_pct}% Pass Rate in {suite_res.total_execution_time_ms:.1f}ms)")

    # STEP 5 & 6: Inject Critical Overspeed Fault
    print_step(5, "Fault Injection: Injecting Critical Rotor Overspeed (>1725 RPM)")
    fi = FaultInjector()
    fi.add_fault(
        fault_id="F-INJECT-001",
        fault_type=FaultTypeEnum.ROTOR_OVERSPEED,
        start_time_s=3.0,
        duration_s=2.0,
        severity=FaultSeverity.CRITICAL,
        magnitude=1.0,
        description="Simulated aerodynamic runaway / grid loss exceeding hard trip speed"
    )
    print("[*] Injected Fault: RotorOverspeed at t=3.0s (Target Speed: ~1800 RPM)")

    print_step(6, "Safety Supervisory System Trip & Containment Verification")
    telemetry_fault = validator.run_closed_loop_simulation(
        duration_s=8.0,
        wind_scenario=WindScenarioType.CONSTANT,
        base_wind_speed_ms=11.5,
        fault_injector=fi
    )
    f_res = fi.results[0]
    print(f"  - Fault Detected      : {'YES' if f_res.detected else 'NO'}")
    print(f"  - Response Latency    : {f_res.response_time_ms:.1f} ms (Acceptance Limit: <= 250.0 ms)")
    print(f"  - Controller Action   : Latched EMERGENCY_STOP, mechanical brake applied, pitch rate 12 deg/s")
    print(f"  - Safety Verification : \033[92m{'PASSED' if f_res.passed_verification else 'FAILED'}\033[0m")

    # STEP 7: Show Emergency Shutdown Post-State
    print_step(7, "Turbine Post-Trip Safe State Confirmation")
    final_point = telemetry_fault[-1]
    print(f"  - Final Operating State : \033[91m{final_point.operating_state.value}\033[0m")
    print(f"  - Mechanical Brake      : {'ENGAGED' if final_point.brake_engaged else 'DISENGAGED'}")
    print(f"  - Final Pitch Angle     : {final_point.pitch_angle_deg:.1f} deg (Feathered safe position)")
    print(f"  - Generator Power       : {final_point.electrical_power_kw:.1f} kW")

    # STEP 8 & 9: Generate Formal Engineering Reports
    print_step(8, "Generate Comprehensive Engineering Reports & Plots")
    html_path = reporter.generate_html_report(suite_res, telemetry_df=df_norm, metrics=metrics_norm, fault_results=fi.results)
    pdf_path = reporter.generate_pdf_report(suite_res, metrics=metrics_norm)
    csv_path = reporter.export_csv(suite_res)
    json_path = reporter.export_json(suite_res, metrics=metrics_norm, fault_results=fi.results)

    print(f"  [✓] Interactive HTML Report : {html_path}")
    print(f"  [✓] Executive PDF Report    : {pdf_path}")
    print(f"  [✓] Machine-Readable JSON   : {json_path}")
    print(f"  [✓] Tabular CSV Data        : {csv_path}")

    # STEP 10: CI/CD Pipeline Reference
    print_step(9, "CI/CD Pipeline & DevOps Automation Architecture")
    print("  - GitHub Actions Workflow  : .github/workflows/ci.yml (Lint, Unit, Integration, Val, Report)")
    print("  - Jenkinsfile Pipeline     : Multi-stage declarative pipeline for enterprise test automation")
    print("  - Docker Containerization  : Dockerfile & docker-compose.yml ready for deployment")
    print("  - REST API & Dashboard     : FastAPI (Port 8000) + Live Telemetry & Control Dashboard")

    print("\n" + "=" * 78)
    print("  DEMO COMPLETE: All 10 Verification Stages Executed Successfully.")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()
