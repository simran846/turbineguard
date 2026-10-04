import sys
import os

# Add src to sys.path for direct script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from turbineguard.analytics.analyzer import TelemetryAnalyzer
from turbineguard.config import SimulationConfig
from turbineguard.reporting.report_generator import ReportGenerator
from turbineguard.simulator.environment import WindScenarioType
from turbineguard.validation.validator import ValidationEngine


def main():
    print("\n" + "=" * 78)
    print("  TurbineGuard: Wind Turbine Controller Automated Validation Platform")
    print("  Loads and Controls Engineering Verification Suite")
    print("=" * 78 + "\n")

    config = SimulationConfig()
    validator = ValidationEngine(config)
    reporter = ReportGenerator(config.reports_dir)

    print("[*] Executing Automated Engineering Verification Suite across 12 REQs...")
    suite_res = validator.validate_all()

    # Run closed-loop sample telemetry for embedded report graphics
    print("[*] Generating reference closed-loop telemetry time-series...")
    telemetry = validator.run_closed_loop_simulation(
        duration_s=25.0,
        wind_scenario=WindScenarioType.STEP,
        base_wind_speed_ms=10.0
    )
    df = TelemetryAnalyzer.to_dataframe(telemetry)
    metrics = TelemetryAnalyzer.compute_metrics(df)

    # Print Terminal Table
    print("\n" + "-" * 78)
    print(f"{'Req ID':<10} | {'Requirement Title':<38} | {'Status':<8} | {'Measured':<12}")
    print("-" * 78)
    for r in suite_res.results:
        status_color = "\033[92mPASS\033[0m" if r.status.value == "PASSED" else "\033[91mFAIL\033[0m"
        val_str = f"{r.measured_value:.1f} {r.unit}"
        print(f"{r.req_id:<10} | {r.title[:38]:<38} | {status_color:<17} | {val_str:<12}")
    print("-" * 78)

    print(f"\n[+] Total Requirements : {suite_res.total_requirements}")
    print(f"[+] Passed            : {suite_res.passed_count}")
    print(f"[+] Failed            : {suite_res.failed_count}")
    print(f"[+] Pass Rate         : {suite_res.pass_rate_pct}%")
    print(f"[+] Total Exec Time   : {suite_res.total_execution_time_ms:.1f} ms")

    # Generate Reports
    print("\n[*] Generating formal engineering reports...")
    html_path = reporter.generate_html_report(suite_res, telemetry_df=df, metrics=metrics)
    pdf_path = reporter.generate_pdf_report(suite_res, metrics=metrics)
    csv_path = reporter.export_csv(suite_res)
    json_path = reporter.export_json(suite_res, metrics=metrics)

    print(f"[✓] HTML Report : {html_path}")
    print(f"[✓] PDF Report  : {pdf_path}")
    print(f"[✓] CSV Results : {csv_path}")
    print(f"[✓] JSON Export : {json_path}")
    print("\n" + "=" * 78 + "\n")


if __name__ == "__main__":
    main()
