"""Pytest fixtures and test configurations for TurbineGuard."""

import pytest

from turbineguard.config import (
    ControllerConfig,
    SafetyThresholds,
    SimulationConfig,
    TurbineParameters,
)
from turbineguard.controller.controller import TurbineController
from turbineguard.controller.pitch_controller import PitchController
from turbineguard.controller.safety_controller import SafetySupervisor
from turbineguard.controller.speed_controller import SpeedTorqueController
from turbineguard.faults.fault_injection import FaultInjector
from turbineguard.models import SensorReadings, TurbineOperatingState
from turbineguard.simulator.sensors import SensorSuite
from turbineguard.simulator.turbine import WindTurbineSimulator
from turbineguard.validation.validator import ValidationEngine


@pytest.fixture
def turbine_params() -> TurbineParameters:
    return TurbineParameters()


@pytest.fixture
def safety_thresholds() -> SafetyThresholds:
    return SafetyThresholds()


@pytest.fixture
def controller_config() -> ControllerConfig:
    return ControllerConfig()


@pytest.fixture
def sim_config() -> SimulationConfig:
    return SimulationConfig(seed=42)


@pytest.fixture
def turbine_simulator(turbine_params: TurbineParameters) -> WindTurbineSimulator:
    return WindTurbineSimulator(params=turbine_params, initial_rotor_rpm=15.79, initial_pitch_deg=0.0)


@pytest.fixture
def sensor_suite() -> SensorSuite:
    return SensorSuite(enable_noise=False, seed=42)


@pytest.fixture
def pitch_controller(controller_config: ControllerConfig, turbine_params: TurbineParameters) -> PitchController:
    return PitchController(config=controller_config, turbine_params=turbine_params)


@pytest.fixture
def speed_controller(controller_config: ControllerConfig, turbine_params: TurbineParameters) -> SpeedTorqueController:
    return SpeedTorqueController(config=controller_config, turbine_params=turbine_params)


@pytest.fixture
def safety_supervisor(safety_thresholds: SafetyThresholds, turbine_params: TurbineParameters) -> SafetySupervisor:
    return SafetySupervisor(thresholds=safety_thresholds, turbine_params=turbine_params)


@pytest.fixture
def master_controller(turbine_params: TurbineParameters, controller_config: ControllerConfig, safety_thresholds: SafetyThresholds) -> TurbineController:
    c = TurbineController(turbine_params=turbine_params, controller_config=controller_config, safety_thresholds=safety_thresholds)
    c.current_state = TurbineOperatingState.NORMAL
    return c


@pytest.fixture
def fault_injector() -> FaultInjector:
    return FaultInjector()


@pytest.fixture
def validation_engine(sim_config: SimulationConfig) -> ValidationEngine:
    return ValidationEngine(sim_config=sim_config)


@pytest.fixture
def nominal_sensor_readings() -> SensorReadings:
    return SensorReadings(
        timestamp=10.0,
        wind_speed_ms=11.5,
        rotor_speed_rpm=15.79,
        generator_speed_rpm=1500.0,
        pitch_angle_deg=2.0,
        generator_power_kw=2500.0,
        rotor_torque_knm=151.2,
        generator_temp_c=65.0,
        nacelle_temp_c=32.0,
        vibration_mm_s=1.1,
        is_valid=True
    )
