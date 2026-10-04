"""Automated Engineering Report Generator for TurbineGuard validation suites."""

import base64
import json
import os
from datetime import datetime, timezone

import pandas as pd

from turbineguard.analytics.analyzer import SimulationMetrics
from turbineguard.analytics.visualization import TelemetryVisualizer
from turbineguard.faults.fault_injection import InjectedFaultResult
from turbineguard.validation.validator import ValidationSuiteResult


class ReportGenerator:
    """Generates professional HTML, PDF, CSV, and JSON engineering validation reports."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "figures"), exist_ok=True)

    def export_csv(self, suite_res: ValidationSuiteResult, filename: str = "validation_results.csv") -> str:
        """Exports validation results as a tabular CSV file."""
        records = [
            {
                "Requirement_ID": r.req_id,
                "Title": r.title,
                "Status": r.status.value,
                "Measured_Value": r.measured_value,
                "Expected_Value": r.expected_value,
                "Tolerance": r.tolerance,
                "Unit": r.unit,
                "Execution_Time_ms": r.execution_time_ms,
                "Diagnostic_Message": r.message
            }
            for r in suite_res.results
        ]
        df = pd.DataFrame(records)
        path = os.path.join(self.output_dir, filename)
        df.to_csv(path, index=False)
        return path

    def export_json(
        self,
        suite_res: ValidationSuiteResult,
        metrics: SimulationMetrics | None = None,
        fault_results: list[InjectedFaultResult] | None = None,
        filename: str = "validation_report.json"
    ) -> str:
        """Exports complete machine-readable test run metadata as JSON."""
        data = {
            "metadata": {
                "project": "TurbineGuard",
                "version": "1.0.0",
                "organization": "Loads and Controls Engineering - Simulation & Test Automation",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "validation_suite": {
                "name": suite_res.suite_name,
                "total_requirements": suite_res.total_requirements,
                "passed": suite_res.passed_count,
                "failed": suite_res.failed_count,
                "warnings": suite_res.warning_count,
                "pass_rate_pct": suite_res.pass_rate_pct,
                "total_time_ms": suite_res.total_execution_time_ms,
                "failed_ids": suite_res.failed_req_ids,
                "items": [
                    {
                        "req_id": r.req_id,
                        "title": r.title,
                        "status": r.status.value,
                        "measured_value": r.measured_value,
                        "expected_value": r.expected_value,
                        "tolerance": r.tolerance,
                        "unit": r.unit,
                        "message": r.message,
                        "time_ms": r.execution_time_ms
                    }
                    for r in suite_res.results
                ]
            },
            "simulation_metrics": metrics.__dict__ if metrics else None,
            "fault_results": [
                {
                    "fault_id": f.fault_id,
                    "type": f.fault_type.value,
                    "severity": f.severity.value,
                    "detected": f.detected,
                    "response_time_ms": f.response_time_ms,
                    "passed": f.passed_verification,
                    "details": f.details
                }
                for f in (fault_results or [])
            ]
        }
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

    def generate_html_report(
        self,
        suite_res: ValidationSuiteResult,
        telemetry_df: pd.DataFrame | None = None,
        metrics: SimulationMetrics | None = None,
        fault_results: list[InjectedFaultResult] | None = None,
        filename: str = "validation_report.html"
    ) -> str:
        """Renders an executive-grade engineering HTML validation report with embedded charts."""
        # Generate and encode visual plots to Base64
        matrix_img_path = os.path.join(self.output_dir, "figures", "validation_matrix.png")
        TelemetryVisualizer.plot_validation_matrix(suite_res, matrix_img_path)
        
        with open(matrix_img_path, "rb") as img_f:
            matrix_b64 = base64.b64encode(img_f.read()).decode("utf-8")
        
        telemetry_b64 = ""
        if telemetry_df is not None and not telemetry_df.empty:
            telemetry_img_path = os.path.join(self.output_dir, "figures", "telemetry_run.png")
            TelemetryVisualizer.plot_closed_loop_telemetry(telemetry_df, telemetry_img_path)
            with open(telemetry_img_path, "rb") as img_f:
                telemetry_b64 = base64.b64encode(img_f.read()).decode("utf-8")

        faults_b64 = ""
        if telemetry_df is not None and fault_results:
            fault_img_path = os.path.join(self.output_dir, "figures", "fault_response.png")
            TelemetryVisualizer.plot_fault_response(telemetry_df, fault_results, fault_img_path)
            with open(fault_img_path, "rb") as img_f:
                faults_b64 = base64.b64encode(img_f.read()).decode("utf-8")

        # HTML Table rows
        val_rows = ""
        for r in suite_res.results:
            badge_class = "badge-pass" if r.status.value == "PASSED" else "badge-fail"
            val_rows += f"""
            <tr>
                <td><strong>{r.req_id}</strong></td>
                <td>{r.title}</td>
                <td><span class="badge {badge_class}">{r.status.value}</span></td>
                <td>{r.measured_value:.2f} {r.unit}</td>
                <td>{r.expected_value:.2f} &plusmn; {r.tolerance:.2f} {r.unit}</td>
                <td>{r.execution_time_ms:.1f} ms</td>
                <td class="desc-cell">{r.message}</td>
            </tr>
            """

        fault_rows = ""
        if fault_results:
            for f in fault_results:
                badge = "badge-pass" if f.passed_verification else "badge-fail"
                fault_rows += f"""
                <tr>
                    <td><strong>{f.fault_id}</strong></td>
                    <td>{f.fault_type.value}</td>
                    <td>{f.severity.value}</td>
                    <td>{'YES' if f.detected else 'NO'}</td>
                    <td>{f.response_time_ms:.1f} ms</td>
                    <td><span class="badge {badge}">{'PASS' if f.passed_verification else 'FAIL'}</span></td>
                    <td class="desc-cell">{f.details}</td>
                </tr>
                """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TurbineGuard Validation Engineering Report</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-card: #182234;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --primary: #0284c7;
            --accent: #38bdf8;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
            padding: 2.5rem;
        }}
        .header {{
            border-bottom: 2px solid var(--border);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .header h1 {{ font-size: 2rem; font-weight: 800; color: var(--accent); letter-spacing: -0.02em; }}
        .header p {{ color: var(--text-muted); font-size: 0.9rem; }}
        .badge-header {{ background: var(--primary); padding: 0.35rem 0.75rem; border-radius: 6px; font-weight: 600; font-size: 0.8rem; }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2.5rem;
        }}
        .kpi-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.25rem;
        }}
        .kpi-title {{ font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); font-weight: 700; }}
        .kpi-value {{ font-size: 1.8rem; font-weight: 800; margin-top: 0.25rem; }}
        .kpi-value.green {{ color: var(--success); }}
        .kpi-value.blue {{ color: var(--accent); }}
        .kpi-value.yellow {{ color: var(--warning); }}
        .kpi-value.red {{ color: var(--danger); }}

        .section {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        .section h2 {{ font-size: 1.25rem; font-weight: 700; margin-bottom: 1rem; color: var(--accent); border-left: 4px solid var(--primary); padding-left: 0.75rem; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.88rem;
            text-align: left;
            margin-top: 0.5rem;
        }}
        th, td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
        }}
        th {{ background: var(--surface-card); color: var(--text-muted); font-weight: 700; text-transform: uppercase; font-size: 0.75rem; }}
        .desc-cell {{ color: var(--text-muted); font-size: 0.82rem; }}
        
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.55rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
        }}
        .badge-pass {{ background: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }}
        .badge-fail {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }}
        
        .figure-container {{
            text-align: center;
            margin: 1.5rem 0;
        }}
        .figure-container img {{
            max-width: 100%;
            border-radius: 6px;
            border: 1px solid var(--border);
        }}
        .disclaimer {{
            font-size: 0.78rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border);
            padding-top: 1.5rem;
            margin-top: 3rem;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>TurbineGuard &bull; Engineering Validation Report</h1>
            <p>Automated Verification, Controller Dynamics & Fault-Injection Audit</p>
        </div>
        <div>
            <span class="badge-header">Siemens Gamesa Portfolio Reference</span>
        </div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title">Total Requirements</div>
            <div class="kpi-value blue">{suite_res.total_requirements}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Passed Requirements</div>
            <div class="kpi-value green">{suite_res.passed_count}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Failed Requirements</div>
            <div class="kpi-value {'red' if suite_res.failed_count > 0 else 'green'}">{suite_res.failed_count}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Verification Pass Rate</div>
            <div class="kpi-value green">{suite_res.pass_rate_pct}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Suite Execution Time</div>
            <div class="kpi-value">{suite_res.total_execution_time_ms:.1f} ms</div>
        </div>
    </div>

    <div class="section">
        <h2>1. Verification Matrix & Requirements Audit</h2>
        <table>
            <thead>
                <tr>
                    <th>Req ID</th>
                    <th>Requirement Title</th>
                    <th>Status</th>
                    <th>Measured</th>
                    <th>Target &plusmn; Tol</th>
                    <th>Exec Time</th>
                    <th>Diagnostics</th>
                </tr>
            </thead>
            <tbody>
                {val_rows}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>2. Requirements Verification Distribution</h2>
        <div class="figure-container">
            <img src="data:image/png;base64,{matrix_b64}" alt="Validation Matrix Breakdown" />
        </div>
    </div>

    {'<div class="section"><h2>3. Fault Injection Testing & Protection Latency</h2><table><thead><tr><th>Fault ID</th><th>Fault Type</th><th>Severity</th><th>Detected</th><th>Response Time</th><th>Outcome</th><th>Details</th></tr></thead><tbody>' + fault_rows + '</tbody></table></div>' if fault_rows else ''}

    {f'<div class="section"><h2>4. Closed-Loop Turbine Dynamic Telemetry</h2><div class="figure-container"><img src="data:image/png;base64,{telemetry_b64}" alt="Turbine Telemetry" /></div></div>' if telemetry_b64 else ''}

    {f'<div class="section"><h2>5. Fault Response & State Machine Intervention Timeline</h2><div class="figure-container"><img src="data:image/png;base64,{faults_b64}" alt="Fault Timeline" /></div></div>' if faults_b64 else ''}

    <div class="disclaimer">
        <strong>TurbineGuard Validation Platform</strong> &bull; Developed by Kumari Simran (CMR University) &bull; Software simulation for educational and portfolio verification demonstration. Not a certified physical turbine controller.
    </div>
</body>
</html>
        """
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return path

    def generate_pdf_report(
        self,
        suite_res: ValidationSuiteResult,
        metrics: SimulationMetrics | None = None,
        filename: str = "validation_report.pdf"
    ) -> str:
        """Generates a professional PDF report using ReportLab."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import (
            Image,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        pdf_path = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#0284c7"),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=14
        )
        h2_style = ParagraphStyle(
            "Heading2Custom",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=10,
            spaceAfter=6
        )

        story.append(Paragraph("TurbineGuard &bull; Engineering Validation Report", title_style))
        story.append(Paragraph(f"Automated Controller Verification Suite | Pass Rate: {suite_res.pass_rate_pct}% | Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", subtitle_style))
        story.append(Spacer(1, 8))

        # KPI Summary Table
        kpi_data = [
            ["Total Requirements", "Passed", "Failed", "Pass Rate", "Execution Time"],
            [
                str(suite_res.total_requirements),
                str(suite_res.passed_count),
                str(suite_res.failed_count),
                f"{suite_res.pass_rate_pct}%",
                f"{suite_res.total_execution_time_ms:.1f} ms"
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[108, 108, 108, 108, 108])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 14))

        # Requirements Table
        story.append(Paragraph("1. Requirements Verification Traceability Matrix", h2_style))
        req_table_data = [["Req ID", "Requirement Title", "Status", "Measured", "Target +/- Tol"]]
        for r in suite_res.results:
            req_table_data.append([
                r.req_id,
                r.title[:38] + ("..." if len(r.title) > 38 else ""),
                r.status.value,
                f"{r.measured_value:.2f} {r.unit}",
                f"{r.expected_value:.2f} +/- {r.tolerance:.2f}"
            ])

        req_table = Table(req_table_data, colWidths=[60, 220, 60, 100, 100])
        req_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(req_table)
        story.append(Spacer(1, 14))

        # Include Validation Matrix figure if generated
        matrix_fig = os.path.join(self.output_dir, "figures", "validation_matrix.png")
        if os.path.exists(matrix_fig):
            story.append(Paragraph("2. Requirements Distribution & Execution Latency", h2_style))
            story.append(Image(matrix_fig, width=500, height=200))

        story.append(Spacer(1, 14))
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontSize=7.5,
            textColor=colors.HexColor("#94a3b8"),
            alignment=1
        )
        story.append(Paragraph("TurbineGuard Validation Platform &bull; Candidate: Kumari Simran &bull; Simulation & Software Verification Portfolio", disclaimer_style))

        doc.build(story)
        return pdf_path
