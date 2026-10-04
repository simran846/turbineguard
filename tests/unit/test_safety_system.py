"""Unit tests for safety supervisory system, trip thresholds, and hysteresis recovery."""

import pytest

from turbineguard.controller.safety_controller import SafetySupervisor
from turbineguard.models import SensorReadings, TurbineOperatingState


@pytest.mark.safety
def test_hard_overspeed_trip_latches_emergency_stop(safety_supervisor: SafetySupervisor, nominal_sensor_readings: SensorReadings):
    """Verifies generator speed >= 1725 RPM triggers latched EMERGENCY_STOP."""
    nominal_sensor_readings.generator_speed_rpm = 1730.0
    state, _warnings, _faults, note = safety_supervisor.evaluate(0.05, nominal_sensor_readings, TurbineOperatingState.NORMAL)
    assert state == TurbineOperatingState.EMERGENCY_STOP
    assert safety_supervisor.is_latched_estop is True
    assert "CRITICAL_OVERSPEED_TRIP" in note


@pytest.mark.safety
def test_latched_estop_persists_even_after_speed_drops(safety_supervisor: SafetySupervisor, nominal_sensor_readings: SensorReadings):
    """Verifies once latched in EMERGENCY_STOP, state stays locked until manual reset."""
    nominal_sensor_readings.generator_speed_rpm = 1750.0
    safety_supervisor.evaluate(0.05, nominal_sensor_readings, TurbineOperatingState.NORMAL)
    
    # Speed drops to normal
    nominal_sensor_readings.generator_speed_rpm = 1000.0
    state, _, _, _ = safety_supervisor.evaluate(0.05, nominal_sensor_readings, TurbineOperatingState.EMERGENCY_STOP)
    assert state == TurbineOperatingState.EMERGENCY_STOP
    
    # After reset
    safety_supervisor.reset_trips()
    state_after_reset, _, _, _ = safety_supervisor.evaluate(0.05, nominal_sensor_readings, TurbineOperatingState.NORMAL)
    assert state_after_reset == TurbineOperatingState.NORMAL


@pytest.mark.safety
def test_thermal_overheat_triggers_shutdown(safety_supervisor: SafetySupervisor, nominal_sensor_readings: SensorReadings):
    """Verifies generator temp >= 98 C triggers SHUTDOWN."""
    nominal_sensor_readings.generator_temp_c = 99.5
    state, _warnings, faults, _note = safety_supervisor.evaluate(0.05, nominal_sensor_readings, TurbineOperatingState.NORMAL)
    assert state == TurbineOperatingState.SHUTDOWN
    assert any("GENERATOR_OVERHEAT_TRIP" in f for f in faults)


@pytest.mark.safety
def test_thermal_warning_triggers_derated(safety_supervisor: SafetySupervisor, nominal_sensor_readings: SensorReadings):
    """Verifies generator temp between 85 C and 98 C triggers DERATED operation."""
    nominal_sensor_readings.generator_temp_c = 88.0
    state, warnings, _faults, _note = safety_supervisor.evaluate(0.05, nominal_sensor_readings, TurbineOperatingState.NORMAL)
    assert state == TurbineOperatingState.DERATED
    assert any("GENERATOR_TEMP_HIGH" in w for w in warnings)


@pytest.mark.safety
def test_structural_vibration_trip(safety_supervisor: SafetySupervisor, nominal_sensor_readings: SensorReadings):
    """Verifies vibration >= 5.5 mm/s triggers FAULT trip."""
    nominal_sensor_readings.vibration_mm_s = 6.2
    state, _warnings, faults, _note = safety_supervisor.evaluate(0.05, nominal_sensor_readings, TurbineOperatingState.NORMAL)
    assert state == TurbineOperatingState.FAULT
    assert any("EXCESSIVE_VIBRATION_TRIP" in f for f in faults)


@pytest.mark.safety
def test_storm_wind_triggers_cutout_shutdown(safety_supervisor: SafetySupervisor, nominal_sensor_readings: SensorReadings):
    """Verifies wind speed >= 25 m/s transitions to SHUTDOWN."""
    nominal_sensor_readings.wind_speed_ms = 26.5
    state, _warnings, _faults, _note = safety_supervisor.evaluate(0.05, nominal_sensor_readings, TurbineOperatingState.NORMAL)
    assert state == TurbineOperatingState.SHUTDOWN
