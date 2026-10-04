"""Fault Injection Engine for simulating failures and verifying controller responses."""

from dataclasses import dataclass

from turbineguard.faults.fault_types import FAULT_CRITERIA_MAP
from turbineguard.models import (
    FaultDefinition,
    FaultSeverity,
    FaultTypeEnum,
    TurbineOperatingState,
)
from turbineguard.simulator.sensors import SensorSuite
from turbineguard.simulator.turbine import WindTurbineSimulator


@dataclass
class InjectedFaultResult:
    """Outcome of an injected fault scenario execution."""
    fault_id: str
    fault_type: FaultTypeEnum
    severity: FaultSeverity
    start_time_s: float
    duration_s: float
    detected: bool
    detection_time_s: float | None
    response_time_ms: float
    observed_state: TurbineOperatingState
    expected_state: TurbineOperatingState
    passed_verification: bool
    details: str


class FaultInjector:
    """Manages scheduling, activation, and response verification of injected plant & sensor faults."""

    def __init__(self):
        self.scheduled_faults: list[FaultDefinition] = []
        self.active_faults: list[FaultDefinition] = []
        self.results: list[InjectedFaultResult] = []
        
        # State tracking for response latency verification
        self._fault_start_times: dict[str, float] = {}
        self._fault_detected_times: dict[str, float] = {}
        self._fault_passed: dict[str, bool] = {}

    def add_fault(
        self,
        fault_id: str,
        fault_type: FaultTypeEnum,
        start_time_s: float,
        duration_s: float,
        severity: FaultSeverity = FaultSeverity.HIGH,
        magnitude: float = 1.0,
        description: str = ""
    ) -> FaultDefinition:
        """Registers a scheduled fault in the injection plan."""
        fault = FaultDefinition(
            fault_id=fault_id,
            fault_type=fault_type,
            name=fault_type.value,
            description=description or f"Injected {fault_type.value} fault at t={start_time_s}s",
            severity=severity,
            start_time_s=start_time_s,
            duration_s=duration_s,
            magnitude=magnitude,
            expected_controller_response=(
                FAULT_CRITERIA_MAP[fault_type].description
                if fault_type in FAULT_CRITERIA_MAP else "Safety reaction"
            )
        )
        self.scheduled_faults.append(fault)
        return fault

    def clear(self) -> None:
        """Clears all scheduled faults and historical results."""
        self.scheduled_faults.clear()
        self.active_faults.clear()
        self.results.clear()
        self._fault_start_times.clear()
        self._fault_detected_times.clear()
        self._fault_passed.clear()

    def process_step(
        self,
        current_time_s: float,
        simulator: WindTurbineSimulator,
        sensor_suite: SensorSuite,
        controller_state: TurbineOperatingState
    ) -> list[FaultDefinition]:
        """Evaluates active faults at timestamp and applies modifiers to physical plant/sensors."""
        active_this_step: list[FaultDefinition] = []

        for fault in self.scheduled_faults:
            t_start = fault.start_time_s
            t_end = t_start + fault.duration_s

            if t_start <= current_time_s <= t_end:
                if not fault.is_active:
                    fault.is_active = True
                    self._fault_start_times[fault.fault_id] = current_time_s
                
                active_this_step.append(fault)
                self._apply_fault_impact(fault, simulator, sensor_suite)
                self._check_controller_response(fault, current_time_s, controller_state)

            elif fault.is_active and current_time_s > t_end:
                # Fault duration expired -> remove active modifiers
                fault.is_active = False
                self._remove_fault_impact(fault, simulator, sensor_suite)

        self.active_faults = active_this_step
        return active_this_step

    def _apply_fault_impact(
        self,
        fault: FaultDefinition,
        simulator: WindTurbineSimulator,
        sensor_suite: SensorSuite
    ) -> None:
        """Injects fault perturbations into physical simulator or sensor suite."""
        ft = fault.fault_type
        mag = fault.magnitude

        if ft == FaultTypeEnum.ROTOR_OVERSPEED:
            # Force aerodynamic speed surge above trip threshold (e.g. 1800 RPM)
            target_rad_s = (1750.0 + mag * 50.0) / (simulator.params.gearbox_ratio * (60.0 / (2.0 * 3.14159265)))
            simulator.rotor_speed_rad_s = max(simulator.rotor_speed_rad_s, target_rad_s)

        elif ft == FaultTypeEnum.GENERATOR_OVERHEAT:
            # Thermal spike above trip threshold (e.g. 102 C)
            simulator.generator_temp_c = max(simulator.generator_temp_c, 99.0 + mag * 5.0)

        elif ft == FaultTypeEnum.VIBRATION_SPIKE:
            simulator.vibration_spike_magnitude = 6.0 * mag

        elif ft == FaultTypeEnum.COMMUNICATION_FAILURE:
            sensor_suite.set_comm_failure(True)

        elif ft == FaultTypeEnum.SENSOR_ROTOR_SPEED_FAILURE:
            sensor_suite.inject_sensor_override("rotor_speed", "zero", 0.0)

        elif ft == FaultTypeEnum.SENSOR_WIND_SPEED_FAILURE:
            sensor_suite.inject_sensor_override("wind_speed", "invalid", -999.0)

        elif ft == FaultTypeEnum.INVALID_SENSOR_VALUE:
            sensor_suite.inject_sensor_override("rotor_speed", "invalid", 0.0)

        elif ft == FaultTypeEnum.STALE_SENSOR_DATA:
            sensor_suite.inject_sensor_override("stale_data", "stale", 1.0)

        elif ft == FaultTypeEnum.PITCH_ACTUATOR_STUCK:
            simulator.pitch_stuck = True
            simulator.pitch_stuck_angle = simulator.pitch_angle_deg

    def _remove_fault_impact(
        self,
        fault: FaultDefinition,
        simulator: WindTurbineSimulator,
        sensor_suite: SensorSuite
    ) -> None:
        """Removes physical modifiers once fault duration ends."""
        ft = fault.fault_type

        if ft == FaultTypeEnum.VIBRATION_SPIKE:
            simulator.vibration_spike_magnitude = 0.0

        elif ft == FaultTypeEnum.COMMUNICATION_FAILURE:
            sensor_suite.set_comm_failure(False)

        elif ft in (
            FaultTypeEnum.SENSOR_ROTOR_SPEED_FAILURE,
            FaultTypeEnum.SENSOR_WIND_SPEED_FAILURE,
            FaultTypeEnum.INVALID_SENSOR_VALUE,
            FaultTypeEnum.STALE_SENSOR_DATA
        ):
            sensor_suite.clear_sensor_overrides()

        elif ft == FaultTypeEnum.PITCH_ACTUATOR_STUCK:
            simulator.pitch_stuck = False

    def _check_controller_response(
        self,
        fault: FaultDefinition,
        current_time_s: float,
        controller_state: TurbineOperatingState
    ) -> None:
        """Checks if controller transitioned to expected safe state within tolerance window."""
        criteria = FAULT_CRITERIA_MAP.get(fault.fault_type)
        if not criteria:
            return

        t_start = self._fault_start_times.get(fault.fault_id, current_time_s)
        elapsed = current_time_s - t_start

        if (
            fault.fault_id not in self._fault_detected_times
            and controller_state == criteria.expected_state
        ):
            self._fault_detected_times[fault.fault_id] = current_time_s
            passed = elapsed <= criteria.max_response_time_s
            self._fault_passed[fault.fault_id] = passed

    def finalize_verification(self) -> list[InjectedFaultResult]:
        """Compiles final verification audit for all injected faults."""
        results: list[InjectedFaultResult] = []

        for fault in self.scheduled_faults:
            criteria = FAULT_CRITERIA_MAP.get(fault.fault_type)
            expected_st = criteria.expected_state if criteria else TurbineOperatingState.FAULT
            max_resp = criteria.max_response_time_s if criteria else 1.0

            det_time = self._fault_detected_times.get(fault.fault_id)
            detected = det_time is not None
            
            if detected and det_time is not None:
                resp_ms = (det_time - fault.start_time_s) * 1000.0
                passed = resp_ms <= (max_resp * 1000.0)
                detail = f"Detected in {resp_ms:.1f}ms (Limit: {max_resp*1000:.0f}ms). State: {expected_st.value}."
            else:
                resp_ms = 9999.0
                passed = False
                detail = f"Failed to detect or transition to {expected_st.value} within {max_resp*1000:.0f}ms."

            res = InjectedFaultResult(
                fault_id=fault.fault_id,
                fault_type=fault.fault_type,
                severity=fault.severity,
                start_time_s=fault.start_time_s,
                duration_s=fault.duration_s,
                detected=detected,
                detection_time_s=det_time,
                response_time_ms=resp_ms,
                observed_state=expected_st if detected else TurbineOperatingState.NORMAL,
                expected_state=expected_st,
                passed_verification=passed,
                details=detail
            )
            results.append(res)

        self.results = results
        return results
