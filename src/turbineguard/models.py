"""Data structures, enums, and domain models for TurbineGuard."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TurbineOperatingState(str, Enum):
    """High-level finite state machine operating states of the wind turbine."""
    PARKED = "PARKED"
    STARTING = "STARTING"
    NORMAL = "NORMAL"
    DERATED = "DERATED"
    WARNING = "WARNING"
    FAULT = "FAULT"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    SHUTDOWN = "SHUTDOWN"
    RESTARTING = "RESTARTING"


class ControlRegion(str, Enum):
    """Wind turbine operating aerodynamics control regions."""
    REGION_1 = "REGION_1"  # Below cut-in wind speed (idling / parking)
    REGION_2 = "REGION_2"  # Between cut-in and rated (MPPT variable speed, fine pitch = 0 deg)
    REGION_2_5 = "REGION_2_5"  # Transition knee region approaching rated speed
    REGION_3 = "REGION_3"  # Above rated wind speed (Full pitch regulation for constant rated power)
    REGION_4 = "REGION_4"  # Above cut-out wind speed (Storm feathering & safe shutdown)


class FaultSeverity(str, Enum):
    """Classification of fault severity."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FaultTypeEnum(str, Enum):
    """Catalog of fault types supported by the fault injection engine."""
    SENSOR_ROTOR_SPEED_FAILURE = "SensorRotorSpeedFailure"
    SENSOR_WIND_SPEED_FAILURE = "SensorWindSpeedFailure"
    ROTOR_OVERSPEED = "RotorOverspeed"
    GENERATOR_OVERHEAT = "GeneratorOverheat"
    EXCESSIVE_WIND = "ExcessiveWind"
    WIND_GUST = "WindGust"
    VIBRATION_SPIKE = "VibrationSpike"
    COMMUNICATION_FAILURE = "CommunicationFailure"
    INVALID_SENSOR_VALUE = "InvalidSensorValue"
    STALE_SENSOR_DATA = "StaleSensorData"
    CONTROLLER_RESPONSE_DELAY = "ControllerResponseDelay"
    PITCH_ACTUATOR_STUCK = "PitchActuatorStuck"


class ValidationStatus(str, Enum):
    """Validation outcome status."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


@dataclass
class SensorReadings:
    """Readings collected from nacelle and drivetrain sensors."""
    timestamp: float
    wind_speed_ms: float
    rotor_speed_rpm: float
    generator_speed_rpm: float
    pitch_angle_deg: float
    generator_power_kw: float
    rotor_torque_knm: float
    generator_temp_c: float
    nacelle_temp_c: float
    vibration_mm_s: float
    is_valid: bool = True
    sensor_fault_flags: list[str] = field(default_factory=list)


@dataclass
class ControlCommand:
    """Actuator command demands calculated by the turbine controller."""
    target_pitch_angle_deg: float
    target_generator_torque_nm: float
    mechanical_brake_engaged: bool
    demanded_state: TurbineOperatingState
    demanded_power_kw: float
    pitch_rate_deg_s: float = 0.0
    active_warnings: list[str] = field(default_factory=list)
    active_faults: list[str] = field(default_factory=list)
    action_note: str = ""


@dataclass
class TurbineTelemetry:
    """Complete instantaneous snapshot of the turbine physical plant and controller state."""
    step: int
    timestamp: float
    wind_speed_ms: float
    pitch_angle_deg: float
    target_pitch_deg: float
    rotor_speed_rpm: float
    generator_speed_rpm: float
    target_torque_nm: float
    aerodynamic_power_kw: float
    electrical_power_kw: float
    generator_temp_c: float
    nacelle_temp_c: float
    vibration_mm_s: float
    operating_state: TurbineOperatingState
    control_region: ControlRegion
    brake_engaged: bool
    active_fault: str | None = None
    action_log: str = ""


@dataclass
class FaultDefinition:
    """Specification of an injectable fault."""
    fault_id: str
    fault_type: FaultTypeEnum
    name: str
    description: str
    severity: FaultSeverity
    start_time_s: float
    duration_s: float
    magnitude: float = 1.0
    expected_controller_response: str = ""
    is_active: bool = False


@dataclass
class ValidationRequirement:
    """Engineering requirement specification for automated verification."""
    req_id: str
    title: str
    description: str
    input_conditions: str
    expected_behavior: str
    acceptance_criteria: str
    tolerance: float
    target_field: str


@dataclass
class ValidationResultItem:
    """Evaluation result of a specific requirement."""
    req_id: str
    title: str
    status: ValidationStatus
    measured_value: float
    expected_value: float
    tolerance: float
    unit: str
    message: str
    execution_time_ms: float
    traceability_tag: str = ""


# Pydantic Schemas for API Interaction
class SimulationStartRequest(BaseModel):
    duration_s: float = Field(default=30.0, ge=1.0, le=600.0, description="Simulation duration in seconds")
    wind_scenario: str = Field(default="normal_step", description="Wind profile scenario name")
    base_wind_speed_ms: float = Field(default=9.0, ge=0.0, le=40.0)
    injected_faults: list[dict[str, Any]] = Field(default_factory=list)


class FaultInjectRequest(BaseModel):
    fault_type: FaultTypeEnum
    start_time_s: float = Field(default=5.0, ge=0.0)
    duration_s: float = Field(default=10.0, ge=0.1)
    magnitude: float = Field(default=1.0)
    severity: FaultSeverity = Field(default=FaultSeverity.HIGH)
    description: str | None = None


class ValidationRunRequest(BaseModel):
    scenarios: list[str] = Field(default_factory=lambda: ["normal_sweep", "overspeed_trip", "sensor_loss", "high_wind_gust"])
    generate_report: bool = True
