"""Automated Validation Requirements Suite (REQ-001 through REQ-012)."""

import numpy as np
import pytest

from turbineguard.faults.fault_injection import FaultInjector
from turbineguard.faults.fault_types import FaultTypeEnum
from turbineguard.models import (
    FaultSeverity,
    SensorReadings,
    TurbineOperatingState,
)
from turbineguard.simulator.environment import WindScenarioType
from turbineguard.validation.validator import ValidationEngine


@pytest.mark.validation
def test_req_001_rotor_speed_regulation_region_2(validation_engine: ValidationEngine):
    """REQ-001: Rotor speed tracking in Region 2 MPPT regime."""
    telemetry = validation_engine.run_closed_loop_simulation(
        duration_s=15.0,
        wind_scenario=WindScenarioType.CONSTANT,
        base_wind_speed_ms=8.0,
        initial_rotor_rpm=10.0,
        initial_pitch_deg=0.0
    )
    recent_speeds = [p.generator_speed_rpm for p in telemetry if p.timestamp >= 10.0]
    mean_speed = float(np.mean(recent_speeds))
    assert 700.0 <= mean_speed <= 1500.0


@pytest.mark.validation
def test_req_002_rated_power_regulation_region_3(validation_engine: ValidationEngine):
    """REQ-002: Rated power regulation in Region 3 above rated wind."""
    telemetry = validation_engine.run_closed_loop_simulation(
        duration_s=20.0,
        wind_scenario=WindScenarioType.CONSTANT,
        base_wind_speed_ms=14.0,
        initial_rotor_rpm=15.79,
        initial_pitch_deg=6.0
    )
    recent_powers = [p.electrical_power_kw for p in telemetry if p.timestamp >= 10.0]
    mean_power = float(np.mean(recent_powers))
    assert mean_power <= 2625.0  # 2500 kW + 5% allowance


@pytest.mark.validation
@pytest.mark.safety
def test_req_003_critical_overspeed_hard_trip(validation_engine: ValidationEngine):
    """REQ-003: Critical rotor overspeed hard trip emergency shutdown."""
    fi = FaultInjector()
    fi.add_fault(
        fault_id="F-REQ3",
        fault_type=FaultTypeEnum.ROTOR_OVERSPEED,
        start_time_s=5.0,
        duration_s=2.0,
        severity=FaultSeverity.CRITICAL
    )
    validation_engine.run_closed_loop_simulation(
        duration_s=10.0,
        wind_scenario=WindScenarioType.CONSTANT,
        base_wind_speed_ms=11.5,
        fault_injector=fi,
        initial_rotor_rpm=15.79
    )
    res = fi.results[0]
    assert res.detected is True
    assert res.passed_verification is True
    assert res.response_time_ms <= 250.0


@pytest.mark.validation
def test_req_004_high_wind_storm_cutout(validation_engine: ValidationEngine):
    """REQ-004: High wind cut-out storm shutdown above 25 m/s."""
    telemetry = validation_engine.run_closed_loop_simulation(
        duration_s=30.0,
        wind_scenario=WindScenarioType.HIGH_WIND_CUTOUT,
        base_wind_speed_ms=14.0,
        initial_rotor_rpm=15.79
    )
    last_pt = telemetry[-1]
    assert last_pt.operating_state in (TurbineOperatingState.SHUTDOWN, TurbineOperatingState.PARKED)
    assert last_pt.pitch_angle_deg >= 85.0


@pytest.mark.validation
@pytest.mark.safety
def test_req_005_generator_overheat_protection(validation_engine: ValidationEngine):
    """REQ-005: Generator overheat thermal shutdown when Tg >= 98 C."""
    fi = FaultInjector()
    fi.add_fault("F-REQ5", FaultTypeEnum.GENERATOR_OVERHEAT, start_time_s=3.0, duration_s=3.0)
    validation_engine.run_closed_loop_simulation(
        duration_s=8.0,
        wind_scenario=WindScenarioType.CONSTANT,
        base_wind_speed_ms=10.0,
        fault_injector=fi
    )
    res = fi.results[0]
    assert res.detected is True
    assert res.passed_verification is True


@pytest.mark.validation
def test_req_006_thermal_warning_power_derating(validation_engine: ValidationEngine):
    """REQ-006: Thermal warning (85 C <= Tg < 98 C) derates power to 65%."""
    c = validation_engine.config
    validation_engine.validator_controller if hasattr(validation_engine, 'validator_controller') else None
    from turbineguard.controller.controller import TurbineController
    ctrl = TurbineController(c.turbine_params, c.controller_config, c.safety_thresholds)
    ctrl.current_state = TurbineOperatingState.NORMAL

    r_warm = SensorReadings(
        timestamp=1.0, wind_speed_ms=11.5, rotor_speed_rpm=15.79, generator_speed_rpm=1500.0,
        pitch_angle_deg=0.0, generator_power_kw=2500.0, rotor_torque_knm=150.0,
        generator_temp_c=88.0, nacelle_temp_c=35.0, vibration_mm_s=1.2, is_valid=True
    )
    cmd = ctrl.compute_cycle(0.05, r_warm)
    assert cmd.demanded_state == TurbineOperatingState.DERATED
    assert cmd.demanded_power_kw <= 1650.0


@pytest.mark.validation
@pytest.mark.safety
def test_req_007_structural_vibration_trip(validation_engine: ValidationEngine):
    """REQ-007: Vibration trip when Vib >= 5.5 mm/s."""
    fi = FaultInjector()
    fi.add_fault("F-REQ7", FaultTypeEnum.VIBRATION_SPIKE, start_time_s=2.0, duration_s=2.0)
    validation_engine.run_closed_loop_simulation(6.0, WindScenarioType.CONSTANT, base_wind_speed_ms=10.0, fault_injector=fi)
    res = fi.results[0]
    assert res.detected is True
    assert res.passed_verification is True


@pytest.mark.validation
def test_req_008_sensor_nan_failsafe(validation_engine: ValidationEngine):
    """REQ-008: Reject NaN/corrupt sensor data and enter safe state."""
    fi = FaultInjector()
    fi.add_fault("F-REQ8", FaultTypeEnum.INVALID_SENSOR_VALUE, start_time_s=2.0, duration_s=2.0)
    validation_engine.run_closed_loop_simulation(6.0, WindScenarioType.CONSTANT, base_wind_speed_ms=10.0, fault_injector=fi)
    res = fi.results[0]
    assert res.detected is True
    assert res.passed_verification is True


@pytest.mark.validation
def test_req_009_communication_bus_loss_protection(validation_engine: ValidationEngine):
    """REQ-009: Communication bus loss triggers failsafe within <= 500ms."""
    fi = FaultInjector()
    fi.add_fault("F-REQ9", FaultTypeEnum.COMMUNICATION_FAILURE, start_time_s=2.0, duration_s=2.0)
    validation_engine.run_closed_loop_simulation(6.0, WindScenarioType.CONSTANT, base_wind_speed_ms=10.0, fault_injector=fi)
    res = fi.results[0]
    assert res.detected is True
    assert res.passed_verification is True
    assert res.response_time_ms <= 500.0


@pytest.mark.validation
def test_req_010_pitch_rate_limiting_compliance(validation_engine: ValidationEngine):
    """REQ-010: Normal pitch slew rate <= 8.0 deg/s."""
    telemetry = validation_engine.run_closed_loop_simulation(
        duration_s=20.0,
        wind_scenario=WindScenarioType.STEP,
        base_wind_speed_ms=10.0,
        initial_rotor_rpm=15.79
    )
    dt = validation_engine.config.dt
    normal_rates = [
        abs((telemetry[i+1].pitch_angle_deg - telemetry[i].pitch_angle_deg) / dt)
        for i in range(len(telemetry)-1)
        if telemetry[i].operating_state in (TurbineOperatingState.NORMAL, TurbineOperatingState.DERATED)
    ]
    assert max(normal_rates) <= 8.05


@pytest.mark.validation
def test_req_011_auto_fault_recovery_hysteresis(validation_engine: ValidationEngine):
    """REQ-011: Holds in safe state for >= 5.0 seconds before auto-restarting."""
    from turbineguard.controller.controller import TurbineController
    c = validation_engine.config
    ctrl = TurbineController(c.turbine_params, c.controller_config, c.safety_thresholds)
    ctrl.current_state = TurbineOperatingState.SHUTDOWN

    recovered = False
    hold_time = 0.0
    for step in range(120):  # 120 * 0.05 = 6.0s
        r = SensorReadings(
            timestamp=step * 0.05, wind_speed_ms=8.0, rotor_speed_rpm=1.0, generator_speed_rpm=95.0,
            pitch_angle_deg=90.0, generator_power_kw=0.0, rotor_torque_knm=0.0,
            generator_temp_c=30.0, nacelle_temp_c=25.0, vibration_mm_s=0.8, is_valid=True
        )
        cmd = ctrl.compute_cycle(0.05, r)
        if cmd.demanded_state == TurbineOperatingState.STARTING:
            recovered = True
            hold_time = step * 0.05
            break

    assert recovered is True
    assert hold_time >= 5.0


@pytest.mark.validation
def test_req_012_extreme_gust_stability(validation_engine: ValidationEngine):
    """REQ-012: Peak generator RPM stays below hard overspeed trip (1725 RPM) during IEC gust."""
    telemetry = validation_engine.run_closed_loop_simulation(
        duration_s=30.0,
        wind_scenario=WindScenarioType.GUST,
        base_wind_speed_ms=11.5,
        initial_rotor_rpm=15.79,
        initial_pitch_deg=0.0
    )
    max_rpm = max(p.generator_speed_rpm for p in telemetry)
    assert max_rpm < 1725.0
