"""Engineering visualization generator using Matplotlib."""

import os

import matplotlib

matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from turbineguard.faults.fault_injection import InjectedFaultResult
from turbineguard.validation.validator import ValidationSuiteResult


class TelemetryVisualizer:
    """Generates high-resolution engineering plots for validation reports and dashboards."""

    @staticmethod
    def apply_style() -> None:
        """Configures clean engineering plot aesthetics."""
        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
        plt.rcParams["axes.edgecolor"] = "#cccccc"
        plt.rcParams["axes.linewidth"] = 0.8
        plt.rcParams["grid.color"] = "#e5e5e5"
        plt.rcParams["grid.linestyle"] = "--"

    @classmethod
    def plot_closed_loop_telemetry(
        cls,
        df: pd.DataFrame,
        output_path: str,
        title: str = "Turbine Closed-Loop Operational Telemetry"
    ) -> str:
        """Generates a 4-panel comprehensive telemetry time-series plot."""
        cls.apply_style()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        fig, axes = plt.subplots(4, 1, figsize=(11, 10), sharex=True)
        t = df["timestamp"]

        # Panel 1: Wind Speed & Pitch Angle
        ax1 = axes[0]
        ax1.plot(t, df["wind_speed_ms"], color="#1f77b4", linewidth=1.8, label="Wind Speed (m/s)")
        ax1.axhline(11.5, color="#1f77b4", linestyle=":", alpha=0.7, label="Rated Wind (11.5 m/s)")
        ax1.axhline(25.0, color="#d62728", linestyle=":", alpha=0.7, label="Cut-out Wind (25 m/s)")
        ax1.set_ylabel("Wind Speed [m/s]", color="#1f77b4", fontweight="bold")
        ax1.tick_params(axis="y", labelcolor="#1f77b4")
        ax1.grid(True)

        ax1_twin = ax1.twinx()
        ax1_twin.plot(t, df["pitch_angle_deg"], color="#ff7f0e", linewidth=1.8, linestyle="--", label="Pitch Angle (deg)")
        ax1_twin.set_ylabel("Pitch Angle [deg]", color="#ff7f0e", fontweight="bold")
        ax1_twin.tick_params(axis="y", labelcolor="#ff7f0e")
        ax1.set_title(title, fontsize=12, fontweight="bold", pad=10)

        # Panel 2: Rotor & Generator Speed
        ax2 = axes[1]
        ax2.plot(t, df["generator_speed_rpm"], color="#2ca02c", linewidth=1.8, label="Generator Speed (RPM)")
        ax2.axhline(1500.0, color="#2ca02c", linestyle=":", label="Rated Speed (1500 RPM)")
        ax2.axhline(1725.0, color="#d62728", linestyle="--", linewidth=1.5, label="Overspeed Trip (1725 RPM)")
        ax2.set_ylabel("Speed [RPM]", fontweight="bold")
        ax2.legend(loc="upper right", framealpha=0.9, fontsize=9)
        ax2.grid(True)

        # Panel 3: Power Production
        ax3 = axes[2]
        ax3.plot(t, df["aerodynamic_power_kw"], color="#9467bd", linewidth=1.5, alpha=0.7, label="Aerodynamic Power (kW)")
        ax3.plot(t, df["electrical_power_kw"], color="#17becf", linewidth=1.8, label="Electrical Output (kW)")
        ax3.axhline(2500.0, color="#d62728", linestyle=":", label="Rated Capacity (2500 kW)")
        ax3.set_ylabel("Power [kW]", fontweight="bold")
        ax3.legend(loc="upper right", framealpha=0.9, fontsize=9)
        ax3.grid(True)

        # Panel 4: Thermal & Vibration
        ax4 = axes[3]
        ax4.plot(t, df["generator_temp_c"], color="#e377c2", linewidth=1.8, label="Generator Temp (C)")
        ax4.axhline(98.0, color="#d62728", linestyle="--", label="Thermal Trip (98 C)")
        ax4.set_ylabel("Temp [C]", color="#e377c2", fontweight="bold")
        ax4.tick_params(axis="y", labelcolor="#e377c2")

        ax4_twin = ax4.twinx()
        ax4_twin.plot(t, df["vibration_mm_s"], color="#7f7f7f", linewidth=1.5, linestyle="-.", label="Vibration (mm/s)")
        ax4_twin.axhline(5.5, color="#bcbd22", linestyle=":", label="Vibration Trip (5.5 mm/s)")
        ax4_twin.set_ylabel("Vibration [mm/s]", color="#7f7f7f", fontweight="bold")
        ax4_twin.tick_params(axis="y", labelcolor="#7f7f7f")

        ax4.set_xlabel("Simulation Time [seconds]", fontweight="bold")
        ax4.grid(True)

        plt.tight_layout()
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return output_path

    @classmethod
    def plot_fault_response(
        cls,
        df: pd.DataFrame,
        fault_results: list[InjectedFaultResult],
        output_path: str
    ) -> str:
        """Generates a dedicated fault injection and protective reaction timeline graph."""
        cls.apply_style()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        t = df["timestamp"]

        # Top: Physical telemetry
        ax1.plot(t, df["generator_speed_rpm"], color="#2ca02c", linewidth=1.8, label="Generator RPM")
        ax1.axhline(1725.0, color="#d62728", linestyle="--", label="Overspeed Trip Limit (1725 RPM)")
        ax1.set_ylabel("Generator Speed [RPM]", fontweight="bold")
        ax1.grid(True)

        # Highlight injected fault windows
        for f in fault_results:
            ax1.axvspan(f.start_time_s, f.start_time_s + f.duration_s, color="#ff9999", alpha=0.3, label=f"Injected {f.fault_type.value}")
            if f.detection_time_s:
                ax1.axvline(f.detection_time_s, color="#d62728", linestyle="-.", linewidth=2, label=f"Detection ({f.response_time_ms:.1f}ms)")

        ax1.set_title("Fault Injection Response Timeline and Controller Reaction", fontsize=12, fontweight="bold")
        ax1.legend(loc="lower right", fontsize=8)

        # Bottom: Pitch & Brake Response
        ax2.plot(t, df["pitch_angle_deg"], color="#ff7f0e", linewidth=1.8, label="Pitch Angle (deg)")
        ax2.plot(t, df["brake_engaged"].astype(int) * 80.0, color="#d62728", linewidth=1.5, linestyle=":", label="Mechanical Brake Engaged")
        ax2.set_ylabel("Pitch Angle [deg]", fontweight="bold")
        ax2.set_xlabel("Time [seconds]", fontweight="bold")
        ax2.legend(loc="upper right", fontsize=8)
        ax2.grid(True)

        plt.tight_layout()
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return output_path

    @classmethod
    def plot_validation_matrix(
        cls,
        suite_res: ValidationSuiteResult,
        output_path: str
    ) -> str:
        """Generates visual bar charts of requirement execution results and tolerances."""
        cls.apply_style()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), gridspec_kw={"width_ratios": [1, 2]})

        # Chart 1: Pass/Fail Pie Chart
        counts = [suite_res.passed_count, suite_res.failed_count, suite_res.warning_count]
        labels = ["Passed", "Failed", "Warnings"]
        colors = ["#2ca02c", "#d62728", "#ff7f0e"]
        
        valid_indices = [i for i, c in enumerate(counts) if c > 0]
        ax1.pie(
            [counts[i] for i in valid_indices],
            labels=[labels[i] for i in valid_indices],
            colors=[colors[i] for i in valid_indices],
            autopct="%1.1f%%",
            startangle=140,
            textprops={"fontweight": "bold"}
        )
        ax1.set_title(f"Test Pass Rate: {suite_res.pass_rate_pct}%", fontsize=11, fontweight="bold")

        # Chart 2: Requirement Execution Timings
        req_ids = [r.req_id for r in suite_res.results]
        exec_times = [r.execution_time_ms for r in suite_res.results]
        bar_colors = ["#2ca02c" if r.status.value == "PASSED" else "#d62728" for r in suite_res.results]

        y_pos = np.arange(len(req_ids))
        ax2.barh(y_pos, exec_times, color=bar_colors, alpha=0.85, edgecolor="#555555", height=0.6)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(req_ids, fontsize=8, fontweight="bold")
        ax2.invert_yaxis()
        ax2.set_xlabel("Execution Time [ms]", fontweight="bold")
        ax2.set_title("Automated Requirement Validation Audit", fontsize=11, fontweight="bold")
        ax2.grid(True, axis="x")

        plt.tight_layout()
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return output_path
