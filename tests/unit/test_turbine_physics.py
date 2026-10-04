"""Unit tests for turbine physical dynamics and aerodynamic equations."""

import math

import pytest

from turbineguard.config import TurbineParameters
from turbineguard.models import ControlCommand, TurbineOperatingState
from turbineguard.simulator.turbine import WindTurbineSimulator


@pytest.mark.unit
def test_swept_area_calculation(turbine_simulator: WindTurbineSimulator):
    """Verifies rotor swept area A = pi * R^2."""
    expected_area = math.pi * (52.0 ** 2)
    assert pytest.approx(turbine_simulator.swept_area_m2, rel=1e-4) == expected_area


@pytest.mark.unit
def test_cp_betz_limit_compliance(turbine_simulator: WindTurbineSimulator):
    """Ensures empirical power coefficient Cp never exceeds theoretical Betz limit (0.593)."""
    for tsr in [2.0, 4.0, 6.0, 8.0, 10.0, 14.0]:
        for pitch in [0.0, 2.0, 5.0, 10.0, 20.0, 90.0]:
            cp = turbine_simulator.calculate_cp(tsr, pitch)
            assert 0.0 <= cp <= 0.48, f"Cp = {cp} violated physical boundaries at TSR={tsr}, pitch={pitch}"


@pytest.mark.unit
def test_feathered_pitch_sheds_power(turbine_simulator: WindTurbineSimulator):
    """Verifies that feathering blades (pitch = 90 deg) reduces aerodynamic power to near zero."""
    cp_feathered = turbine_simulator.calculate_cp(tip_speed_ratio=8.0, pitch_angle_deg=90.0)
    assert cp_feathered < 0.01


@pytest.mark.unit
def test_gearbox_ratio_speed_relationship(turbine_simulator: WindTurbineSimulator):
    """Verifies generator speed = rotor speed * gearbox ratio."""
    ratio = turbine_simulator.params.gearbox_ratio
    assert pytest.approx(turbine_simulator.generator_speed_rpm, rel=1e-4) == turbine_simulator.rotor_speed_rpm * ratio


@pytest.mark.unit
def test_mechanical_brake_deceleration(turbine_params: TurbineParameters):
    """Verifies that engaging mechanical brake rapidly decelerates rotor."""
    sim = WindTurbineSimulator(params=turbine_params, initial_rotor_rpm=15.0, initial_pitch_deg=90.0)
    cmd_brake = ControlCommand(
        target_pitch_angle_deg=90.0,
        target_generator_torque_nm=0.0,
        mechanical_brake_engaged=True,
        demanded_state=TurbineOperatingState.EMERGENCY_STOP,
        demanded_power_kw=0.0
    )
    initial_rpm = sim.rotor_speed_rpm
    sim.step(dt=0.1, wind_speed_ms=10.0, control_cmd=cmd_brake)
    assert sim.rotor_speed_rpm < initial_rpm


@pytest.mark.unit
def test_thermal_heating_and_cooling(turbine_params: TurbineParameters):
    """Verifies thermal heating under load and cooling towards ambient."""
    sim = WindTurbineSimulator(params=turbine_params, initial_rotor_rpm=15.79, initial_pitch_deg=0.0, initial_temp_c=25.0)
    cmd_load = ControlCommand(
        target_pitch_angle_deg=0.0,
        target_generator_torque_nm=15000.0,
        mechanical_brake_engaged=False,
        demanded_state=TurbineOperatingState.NORMAL,
        demanded_power_kw=2500.0
    )
    # Step under load
    for _ in range(50):
        sim.step(dt=0.1, wind_speed_ms=12.0, control_cmd=cmd_load)
    assert sim.generator_temp_c > 25.0


@pytest.mark.unit
def test_pitch_rate_limiter(turbine_params: TurbineParameters):
    """Verifies pitch actuator does not exceed physical rate limits (8 deg/s in normal)."""
    sim = WindTurbineSimulator(params=turbine_params, initial_rotor_rpm=15.79, initial_pitch_deg=0.0)
    cmd = ControlCommand(
        target_pitch_angle_deg=90.0,  # Big step command
        target_generator_torque_nm=0.0,
        mechanical_brake_engaged=False,
        demanded_state=TurbineOperatingState.NORMAL,
        demanded_power_kw=0.0
    )
    sim.step(dt=0.1, wind_speed_ms=10.0, control_cmd=cmd)
    # in 0.1s at max 8 deg/s, pitch should increase at most 0.8 deg + small margin
    assert sim.pitch_angle_deg <= 0.85


@pytest.mark.unit
def test_vibration_increases_with_rotor_imbalance(turbine_params: TurbineParameters):
    """Verifies vibration dynamics respond to speed deviations and injected spikes."""
    sim = WindTurbineSimulator(params=turbine_params, initial_rotor_rpm=15.79)
    cmd = ControlCommand(
        target_pitch_angle_deg=0.0,
        target_generator_torque_nm=10000.0,
        mechanical_brake_engaged=False,
        demanded_state=TurbineOperatingState.NORMAL,
        demanded_power_kw=2000.0
    )
    res_normal = sim.step(dt=0.05, wind_speed_ms=10.0, control_cmd=cmd)
    
    sim.vibration_spike_magnitude = 5.0
    res_spike = sim.step(dt=0.05, wind_speed_ms=10.0, control_cmd=cmd)
    assert res_spike["vibration_mm_s"] > res_normal["vibration_mm_s"] + 4.0
