"""Unit tests for fault injection scheduling, plant perturbation, and latency verification."""

import pytest

from turbineguard.faults.fault_injection import FaultInjector
from turbineguard.faults.fault_types import FaultTypeEnum
from turbineguard.models import TurbineOperatingState
from turbineguard.simulator.sensors import SensorSuite
from turbineguard.simulator.turbine import WindTurbineSimulator


@pytest.mark.fault
def test_fault_registration_and_schedule():
    """Verifies adding a scheduled fault."""
    fi = FaultInjector()
    f = fi.add_fault("F-001", FaultTypeEnum.ROTOR_OVERSPEED, start_time_s=5.0, duration_s=2.0)
    assert f.fault_id == "F-001"
    assert len(fi.scheduled_faults) == 1
    assert f.is_active is False


@pytest.mark.fault
def test_fault_activation_in_window(turbine_simulator: WindTurbineSimulator, sensor_suite: SensorSuite):
    """Verifies fault is activated when simulation timestamp enters schedule window."""
    fi = FaultInjector()
    fi.add_fault("F-001", FaultTypeEnum.VIBRATION_SPIKE, start_time_s=3.0, duration_s=2.0)

    # Before window (t = 2.0s)
    active_before = fi.process_step(2.0, turbine_simulator, sensor_suite, TurbineOperatingState.NORMAL)
    assert len(active_before) == 0
    assert turbine_simulator.vibration_spike_magnitude == 0.0

    # Inside window (t = 3.5s)
    active_inside = fi.process_step(3.5, turbine_simulator, sensor_suite, TurbineOperatingState.NORMAL)
    assert len(active_inside) == 1
    assert turbine_simulator.vibration_spike_magnitude > 0.0

    # After window (t = 6.0s)
    active_after = fi.process_step(6.0, turbine_simulator, sensor_suite, TurbineOperatingState.NORMAL)
    assert len(active_after) == 0
    assert turbine_simulator.vibration_spike_magnitude == 0.0


@pytest.mark.fault
def test_fault_response_timing_pass(turbine_simulator: WindTurbineSimulator, sensor_suite: SensorSuite):
    """Verifies verification passes when controller reacts within allowed time limit."""
    fi = FaultInjector()
    fi.add_fault("F-002", FaultTypeEnum.ROTOR_OVERSPEED, start_time_s=1.0, duration_s=2.0)

    # Step at start
    fi.process_step(1.0, turbine_simulator, sensor_suite, TurbineOperatingState.NORMAL)
    # Controller trips at 1.1s (100ms response <= 250ms limit)
    fi.process_step(1.1, turbine_simulator, sensor_suite, TurbineOperatingState.EMERGENCY_STOP)

    results = fi.finalize_verification()
    assert len(results) == 1
    assert results[0].detected is True
    assert results[0].passed_verification is True
    assert results[0].response_time_ms == pytest.approx(100.0, abs=1.0)


@pytest.mark.fault
def test_fault_response_timing_fail_on_slow_reaction(turbine_simulator: WindTurbineSimulator, sensor_suite: SensorSuite):
    """Verifies verification fails when controller reacts too slowly."""
    fi = FaultInjector()
    fi.add_fault("F-003", FaultTypeEnum.ROTOR_OVERSPEED, start_time_s=1.0, duration_s=2.0)

    # Step at start
    fi.process_step(1.0, turbine_simulator, sensor_suite, TurbineOperatingState.NORMAL)
    # Step after 400ms without trip
    fi.process_step(1.4, turbine_simulator, sensor_suite, TurbineOperatingState.NORMAL)
    # Belated trip at 1.5s (500ms > 250ms limit)
    fi.process_step(1.5, turbine_simulator, sensor_suite, TurbineOperatingState.EMERGENCY_STOP)

    results = fi.finalize_verification()
    assert results[0].passed_verification is False


@pytest.mark.fault
def test_fault_clear():
    """Verifies clearing injector state."""
    fi = FaultInjector()
    fi.add_fault("F-001", FaultTypeEnum.COMMUNICATION_FAILURE, 1.0, 1.0)
    fi.clear()
    assert len(fi.scheduled_faults) == 0
    assert len(fi.active_faults) == 0
    assert len(fi.results) == 0
