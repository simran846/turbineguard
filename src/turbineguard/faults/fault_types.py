"""Fault types and definitions for fault-injection testing."""

from dataclasses import dataclass

from turbineguard.models import FaultTypeEnum, TurbineOperatingState


@dataclass
class FaultEvaluationCriteria:
    """Acceptance criteria to verify controller response to a specific fault."""
    expected_state: TurbineOperatingState
    max_response_time_s: float
    description: str


FAULT_CRITERIA_MAP: dict[FaultTypeEnum, FaultEvaluationCriteria] = {
    FaultTypeEnum.ROTOR_OVERSPEED: FaultEvaluationCriteria(
        expected_state=TurbineOperatingState.EMERGENCY_STOP,
        max_response_time_s=0.25,
        description="Controller must trigger EMERGENCY_STOP within 250ms of critical overspeed."
    ),
    FaultTypeEnum.COMMUNICATION_FAILURE: FaultEvaluationCriteria(
        expected_state=TurbineOperatingState.FAULT,
        max_response_time_s=0.50,
        description="Controller must enter FAULT state failsafe on complete communication loss."
    ),
    FaultTypeEnum.GENERATOR_OVERHEAT: FaultEvaluationCriteria(
        expected_state=TurbineOperatingState.SHUTDOWN,
        max_response_time_s=1.00,
        description="Controller must transition to SHUTDOWN upon reaching generator trip temperature."
    ),
    FaultTypeEnum.EXCESSIVE_WIND: FaultEvaluationCriteria(
        expected_state=TurbineOperatingState.SHUTDOWN,
        max_response_time_s=0.50,
        description="Controller must initiate safe cut-out shutdown when wind speed exceeds 25 m/s."
    ),
    FaultTypeEnum.VIBRATION_SPIKE: FaultEvaluationCriteria(
        expected_state=TurbineOperatingState.FAULT,
        max_response_time_s=0.30,
        description="Controller must trip on structural vibration exceeding safety limits."
    ),
    FaultTypeEnum.INVALID_SENSOR_VALUE: FaultEvaluationCriteria(
        expected_state=TurbineOperatingState.FAULT,
        max_response_time_s=0.20,
        description="Controller must reject NaN/corrupt sensor data and enter safe state."
    ),
    FaultTypeEnum.SENSOR_ROTOR_SPEED_FAILURE: FaultEvaluationCriteria(
        expected_state=TurbineOperatingState.FAULT,
        max_response_time_s=0.30,
        description="Controller must transition to FAULT upon loss of rotor speed feedback."
    ),
    FaultTypeEnum.SENSOR_WIND_SPEED_FAILURE: FaultEvaluationCriteria(
        expected_state=TurbineOperatingState.FAULT,
        max_response_time_s=0.50,
        description="Controller must handle anemometer out-of-range sensor error."
    ),
    FaultTypeEnum.STALE_SENSOR_DATA: FaultEvaluationCriteria(
        expected_state=TurbineOperatingState.FAULT,
        max_response_time_s=1.00,
        description="Controller must detect frozen telemetry data packets."
    ),
    FaultTypeEnum.WIND_GUST: FaultEvaluationCriteria(
        expected_state=TurbineOperatingState.NORMAL,  # Or DERATED depending on gust peak
        max_response_time_s=2.00,
        description="Controller pitch regulator must increase blade pitch to keep RPM stable during gust."
    ),
    FaultTypeEnum.PITCH_ACTUATOR_STUCK: FaultEvaluationCriteria(
        expected_state=TurbineOperatingState.FAULT,
        max_response_time_s=1.50,
        description="Controller or safety loop must handle stuck pitch actuator."
    ),
}
