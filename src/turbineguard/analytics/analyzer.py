"""Data analysis engine for simulation telemetry and test metrics."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from turbineguard.models import TurbineTelemetry


@dataclass
class SimulationMetrics:
    """Consolidated engineering performance indicators from a simulation run."""
    total_duration_s: float
    total_energy_yield_kwh: float
    mean_electrical_power_kw: float
    peak_electrical_power_kw: float
    mean_generator_rpm: float
    max_generator_rpm: float
    rpm_overshoot_pct: float
    mean_pitch_deg: float
    max_pitch_rate_deg_s: float
    final_generator_temp_c: float
    max_generator_temp_c: float
    peak_vibration_mm_s: float
    operating_states_breakdown: dict[str, float]  # Percentage time in each state


class TelemetryAnalyzer:
    """Analyzes time-series data from simulation executions using Pandas & NumPy."""

    @staticmethod
    def to_dataframe(telemetry: list[TurbineTelemetry]) -> pd.DataFrame:
        """Converts telemetry records list into a structured Pandas DataFrame."""
        records = [
            {
                "step": t.step,
                "timestamp": t.timestamp,
                "wind_speed_ms": t.wind_speed_ms,
                "pitch_angle_deg": t.pitch_angle_deg,
                "target_pitch_deg": t.target_pitch_deg,
                "rotor_speed_rpm": t.rotor_speed_rpm,
                "generator_speed_rpm": t.generator_speed_rpm,
                "target_torque_nm": t.target_torque_nm,
                "aerodynamic_power_kw": t.aerodynamic_power_kw,
                "electrical_power_kw": t.electrical_power_kw,
                "generator_temp_c": t.generator_temp_c,
                "nacelle_temp_c": t.nacelle_temp_c,
                "vibration_mm_s": t.vibration_mm_s,
                "operating_state": t.operating_state.value if hasattr(t.operating_state, "value") else str(t.operating_state),
                "control_region": t.control_region.value if hasattr(t.control_region, "value") else str(t.control_region),
                "brake_engaged": t.brake_engaged,
                "active_fault": t.active_fault,
                "action_log": t.action_log
            }
            for t in telemetry
        ]
        return pd.DataFrame(records)

    @staticmethod
    def compute_metrics(df: pd.DataFrame, rated_rpm: float = 1500.0) -> SimulationMetrics:
        """Calculates derived performance, safety, and energy statistics from telemetry DataFrame."""
        if df.empty:
            return SimulationMetrics(
                total_duration_s=0.0,
                total_energy_yield_kwh=0.0,
                mean_electrical_power_kw=0.0,
                peak_electrical_power_kw=0.0,
                mean_generator_rpm=0.0,
                max_generator_rpm=0.0,
                rpm_overshoot_pct=0.0,
                mean_pitch_deg=0.0,
                max_pitch_rate_deg_s=0.0,
                final_generator_temp_c=0.0,
                max_generator_temp_c=0.0,
                peak_vibration_mm_s=0.0,
                operating_states_breakdown={}
            )

        duration = float(df["timestamp"].iloc[-1] - df["timestamp"].iloc[0])
        dt = float(df["timestamp"].diff().mean()) if len(df) > 1 else 0.05
        
        # Energy yield = integral of electrical power (kW * s -> kWh)
        energy_kwh = float(np.trapezoid(df["electrical_power_kw"], df["timestamp"]) / 3600.0) if len(df) > 1 else 0.0

        # Pitch rates
        pitch_diff = df["pitch_angle_deg"].diff().abs() / max(1e-4, dt)
        max_pitch_rate = float(pitch_diff.max()) if not pitch_diff.isna().all() else 0.0

        # RPM overshoot
        max_rpm = float(df["generator_speed_rpm"].max())
        overshoot_pct = max(0.0, (max_rpm - rated_rpm) / rated_rpm * 100.0)

        # State percentages
        state_counts = df["operating_state"].value_counts(normalize=True) * 100.0
        state_dict = {str(k): round(float(v), 2) for k, v in state_counts.items()}

        return SimulationMetrics(
            total_duration_s=round(duration, 2),
            total_energy_yield_kwh=round(energy_kwh, 4),
            mean_electrical_power_kw=round(float(df["electrical_power_kw"].mean()), 2),
            peak_electrical_power_kw=round(float(df["electrical_power_kw"].max()), 2),
            mean_generator_rpm=round(float(df["generator_speed_rpm"].mean()), 2),
            max_generator_rpm=round(max_rpm, 2),
            rpm_overshoot_pct=round(overshoot_pct, 2),
            mean_pitch_deg=round(float(df["pitch_angle_deg"].mean()), 2),
            max_pitch_rate_deg_s=round(max_pitch_rate, 2),
            final_generator_temp_c=round(float(df["generator_temp_c"].iloc[-1]), 2),
            max_generator_temp_c=round(float(df["generator_temp_c"].max()), 2),
            peak_vibration_mm_s=round(float(df["vibration_mm_s"].max()), 2),
            operating_states_breakdown=state_dict
        )
