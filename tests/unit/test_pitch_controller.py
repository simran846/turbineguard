"""Unit tests for pitch PID regulator."""

import pytest

from turbineguard.controller.pitch_controller import PitchController


@pytest.mark.unit
def test_region_2_optimum_fine_pitch(pitch_controller: PitchController):
    """Verifies pitch angle stays at 0 deg when below rated wind speed."""
    cmd = pitch_controller.compute_pitch_demand(
        dt=0.05,
        measured_gen_rpm=1200.0,
        wind_speed_ms=8.0,
        current_pitch_deg=0.0
    )
    assert cmd == 0.0


@pytest.mark.unit
def test_region_3_pitch_increases_on_overspeed(pitch_controller: PitchController):
    """Verifies pitch increases when generator exceeds rated RPM (1500 RPM) in high wind."""
    cmd = pitch_controller.compute_pitch_demand(
        dt=0.05,
        measured_gen_rpm=1580.0,
        wind_speed_ms=13.0,
        current_pitch_deg=4.0
    )
    assert cmd > 0.0


@pytest.mark.unit
def test_feathered_mode_demands_90_degrees(pitch_controller: PitchController):
    """Verifies pitch controller demands 90 degrees when feathered mode is commanded."""
    cmd = pitch_controller.compute_pitch_demand(
        dt=0.05,
        measured_gen_rpm=1500.0,
        wind_speed_ms=10.0,
        current_pitch_deg=10.0,
        is_feathered_mode=True
    )
    assert cmd == 90.0


@pytest.mark.unit
def test_storm_wind_triggers_full_pitch(pitch_controller: PitchController):
    """Verifies wind speed above 25 m/s causes pitch demand of 90 degrees."""
    cmd = pitch_controller.compute_pitch_demand(
        dt=0.05,
        measured_gen_rpm=1400.0,
        wind_speed_ms=26.0,
        current_pitch_deg=20.0
    )
    assert cmd == 90.0


@pytest.mark.unit
def test_anti_windup_clamping(pitch_controller: PitchController):
    """Verifies integrator error is clamped within configured limits."""
    # Feed prolonged speed error
    for _ in range(200):
        pitch_controller.compute_pitch_demand(0.1, 1700.0, 15.0, 10.0)
    assert pitch_controller.integral_error <= pitch_controller.config.pitch_integral_max


@pytest.mark.unit
def test_pitch_controller_reset(pitch_controller: PitchController):
    """Verifies reset zeroes integral error and historical states."""
    pitch_controller.integral_error = 45.0
    pitch_controller.prev_error = 100.0
    pitch_controller.reset()
    assert pitch_controller.integral_error == 0.0
    assert pitch_controller.prev_error == 0.0
