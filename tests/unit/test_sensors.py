"""Unit tests for sensor suite, noise modeling, and sensor fault overrides."""

import math

import pytest

from turbineguard.simulator.sensors import SensorSuite


@pytest.mark.unit
def test_nominal_sensor_reading_without_noise(sensor_suite: SensorSuite):
    """Verifies perfect sensing when noise is disabled."""
    r = sensor_suite.read_sensors(
        timestamp=1.0,
        actual_wind_speed_ms=10.0,
        actual_rotor_speed_rpm=15.0,
        actual_generator_speed_rpm=1425.0,
        actual_pitch_angle_deg=0.0,
        actual_generator_power_kw=2000.0,
        actual_rotor_torque_knm=120.0,
        actual_generator_temp_c=60.0,
        actual_nacelle_temp_c=30.0,
        actual_vibration_mm_s=1.0
    )
    assert r.wind_speed_ms == 10.0
    assert r.generator_speed_rpm == 1425.0
    assert r.is_valid is True
    assert len(r.sensor_fault_flags) == 0


@pytest.mark.unit
def test_sensor_communication_loss(sensor_suite: SensorSuite):
    """Verifies sensor suite outputs invalid readings and flag on communication bus loss."""
    sensor_suite.set_comm_failure(True)
    r = sensor_suite.read_sensors(1.0, 10.0, 15.0, 1425.0, 0.0, 2000.0, 120.0, 60.0, 30.0, 1.0)
    assert r.is_valid is False
    assert "COMMUNICATION_TIMEOUT_BUS_OFF" in r.sensor_fault_flags


@pytest.mark.unit
def test_sensor_stuck_override(sensor_suite: SensorSuite):
    """Verifies sensor override locks sensor output to target value."""
    sensor_suite.inject_sensor_override("rotor_speed", "stuck", 12.5)
    r = sensor_suite.read_sensors(1.0, 10.0, 18.0, 1710.0, 0.0, 2000.0, 120.0, 60.0, 30.0, 1.0)
    assert r.rotor_speed_rpm == 12.5


@pytest.mark.unit
def test_sensor_nan_injection(sensor_suite: SensorSuite):
    """Verifies NaN sensor injection marks reading invalid."""
    sensor_suite.inject_sensor_override("rotor_speed", "invalid", 0.0)
    r = sensor_suite.read_sensors(1.0, 10.0, 15.0, 1425.0, 0.0, 2000.0, 120.0, 60.0, 30.0, 1.0)
    assert math.isnan(r.rotor_speed_rpm)
    assert r.is_valid is False


@pytest.mark.unit
def test_stale_sensor_data_caching(sensor_suite: SensorSuite):
    """Verifies stale sensor data holds previous values."""
    # First reading
    r1 = sensor_suite.read_sensors(1.0, 10.0, 15.0, 1425.0, 0.0, 2000.0, 120.0, 60.0, 30.0, 1.0)
    sensor_suite.inject_sensor_override("stale_data", "stale", 1.0)
    # Second reading with changed actuals
    r2 = sensor_suite.read_sensors(2.0, 25.0, 30.0, 2800.0, 10.0, 3000.0, 200.0, 90.0, 50.0, 5.0)
    assert r2.wind_speed_ms == r1.wind_speed_ms
    assert "STALE_DATA_FROZEN" in r2.sensor_fault_flags
