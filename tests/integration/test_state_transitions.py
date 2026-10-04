"""Integration tests for finite state machine transitions across operating cycles."""

import pytest

from turbineguard.controller.controller import TurbineController
from turbineguard.models import SensorReadings, TurbineOperatingState


@pytest.mark.integration
def test_startup_sequence_transitions_to_normal(master_controller: TurbineController):
    """Verifies STARTING transitions to NORMAL once rated speed and 0 deg pitch are reached."""
    master_controller.current_state = TurbineOperatingState.STARTING
    master_controller.startup_timer_s = 20.0  # Finished pitch down ramp

    readings = SensorReadings(
        timestamp=20.0,
        wind_speed_ms=10.0,
        rotor_speed_rpm=14.0,
        generator_speed_rpm=1330.0,
        pitch_angle_deg=0.0,
        generator_power_kw=1800.0,
        rotor_torque_knm=120.0,
        generator_temp_c=50.0,
        nacelle_temp_c=25.0,
        vibration_mm_s=1.0,
        is_valid=True
    )

    cmd = master_controller.compute_cycle(0.05, readings)
    assert master_controller.current_state == TurbineOperatingState.NORMAL
    assert cmd.demanded_state == TurbineOperatingState.NORMAL


@pytest.mark.integration
def test_warning_derated_recovery_to_normal(master_controller: TurbineController):
    """Verifies turbine enters DERATED on high temp and returns to NORMAL when temp cools."""
    master_controller.current_state = TurbineOperatingState.NORMAL
    
    # High temp (88 C > 85 C warning)
    r_hot = SensorReadings(
        timestamp=1.0, wind_speed_ms=11.5, rotor_speed_rpm=15.79, generator_speed_rpm=1500.0,
        pitch_angle_deg=0.0, generator_power_kw=2500.0, rotor_torque_knm=150.0,
        generator_temp_c=88.0, nacelle_temp_c=35.0, vibration_mm_s=1.2, is_valid=True
    )
    master_controller.compute_cycle(0.05, r_hot)
    assert master_controller.current_state == TurbineOperatingState.DERATED

    # Temp cools back to 75 C
    r_cool = SensorReadings(
        timestamp=2.0, wind_speed_ms=11.5, rotor_speed_rpm=15.79, generator_speed_rpm=1500.0,
        pitch_angle_deg=0.0, generator_power_kw=2500.0, rotor_torque_knm=150.0,
        generator_temp_c=75.0, nacelle_temp_c=30.0, vibration_mm_s=1.2, is_valid=True
    )
    master_controller.compute_cycle(0.05, r_cool)
    assert master_controller.current_state == TurbineOperatingState.NORMAL


@pytest.mark.integration
def test_emergency_stop_overrides_all_other_states(master_controller: TurbineController):
    """Verifies critical fault immediately forces EMERGENCY_STOP and locks brake."""
    master_controller.current_state = TurbineOperatingState.NORMAL
    r_critical = SensorReadings(
        timestamp=1.0, wind_speed_ms=11.5, rotor_speed_rpm=19.0, generator_speed_rpm=1805.0,
        pitch_angle_deg=0.0, generator_power_kw=2500.0, rotor_torque_knm=150.0,
        generator_temp_c=65.0, nacelle_temp_c=30.0, vibration_mm_s=1.2, is_valid=True
    )
    cmd = master_controller.compute_cycle(0.05, r_critical)
    assert cmd.demanded_state == TurbineOperatingState.EMERGENCY_STOP
    assert cmd.mechanical_brake_engaged is True
    assert cmd.target_pitch_angle_deg == 90.0


@pytest.mark.integration
def test_controller_reset_cycle(master_controller: TurbineController):
    """Verifies reset returns controller to default starting state."""
    master_controller.current_state = TurbineOperatingState.EMERGENCY_STOP
    master_controller.reset(TurbineOperatingState.STARTING)
    assert master_controller.current_state == TurbineOperatingState.STARTING
