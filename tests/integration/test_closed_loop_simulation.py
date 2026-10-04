"""Integration tests for closed-loop turbine dynamics and simulation orchestration."""

import pytest

from turbineguard.analytics.analyzer import TelemetryAnalyzer
from turbineguard.simulator.environment import WindScenarioType
from turbineguard.validation.validator import ValidationEngine


@pytest.mark.integration
def test_closed_loop_simulation_steady_state_run(validation_engine: ValidationEngine):
    """Verifies that a 10-second closed loop run executes without NaN or crashes."""
    telemetry = validation_engine.run_closed_loop_simulation(
        duration_s=10.0,
        wind_scenario=WindScenarioType.CONSTANT,
        base_wind_speed_ms=11.5
    )
    assert len(telemetry) == int(10.0 / validation_engine.config.dt)
    
    # Check data integrity
    for pt in telemetry:
        assert not any(v is None for v in [pt.wind_speed_ms, pt.generator_speed_rpm, pt.electrical_power_kw])
        assert pt.generator_speed_rpm > 0.0


@pytest.mark.integration
def test_simulation_metrics_calculation(validation_engine: ValidationEngine):
    """Verifies derived performance metrics computation from closed loop run."""
    telemetry = validation_engine.run_closed_loop_simulation(
        duration_s=15.0,
        wind_scenario=WindScenarioType.CONSTANT,
        base_wind_speed_ms=11.5
    )
    df = TelemetryAnalyzer.to_dataframe(telemetry)
    metrics = TelemetryAnalyzer.compute_metrics(df)

    assert metrics.total_duration_s == pytest.approx(15.0, abs=0.2)
    assert metrics.mean_electrical_power_kw > 1500.0
    assert metrics.total_energy_yield_kwh > 0.0


@pytest.mark.integration
def test_power_production_scales_with_wind_speed(validation_engine: ValidationEngine):
    """Verifies higher wind in Region 2 produces more electrical power."""
    t_low = validation_engine.run_closed_loop_simulation(10.0, WindScenarioType.CONSTANT, base_wind_speed_ms=6.0)
    t_high = validation_engine.run_closed_loop_simulation(10.0, WindScenarioType.CONSTANT, base_wind_speed_ms=9.0)

    p_low = sum(p.electrical_power_kw for p in t_low) / len(t_low)
    p_high = sum(p.electrical_power_kw for p in t_high) / len(t_high)

    assert p_high > p_low


@pytest.mark.integration
def test_step_wind_pitch_response(validation_engine: ValidationEngine):
    """Verifies pitch angle increases following a step increase in wind above rated."""
    telemetry = validation_engine.run_closed_loop_simulation(
        duration_s=25.0,
        wind_scenario=WindScenarioType.STEP,
        base_wind_speed_ms=10.0
    )
    initial_pitch = telemetry[50].pitch_angle_deg  # at t = 2.5s (10 m/s)
    high_wind_pitch = telemetry[350].pitch_angle_deg  # at t = 17.5s (15 m/s)
    
    assert high_wind_pitch > initial_pitch + 2.0
