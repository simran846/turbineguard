"""Safety supervisory system and protective trip logic."""

import math

from turbineguard.config import SafetyThresholds, TurbineParameters
from turbineguard.models import SensorReadings, TurbineOperatingState


class SafetySupervisor:
    """Supervisory safety loop executing continuous envelope protection and trip evaluation."""

    def __init__(
        self,
        thresholds: SafetyThresholds | None = None,
        turbine_params: TurbineParameters | None = None
    ):
        self.thresholds = thresholds or SafetyThresholds()
        self.params = turbine_params or TurbineParameters()
        
        # Internal Protection State
        self.is_latched_estop: bool = False
        self.estop_reason: str = ""
        self.active_faults: list[str] = []
        self.active_warnings: list[str] = []
        
        # Recovery timing
        self.safe_envelope_duration_s: float = 0.0

    def reset_trips(self) -> None:
        """Manual or operator reset of latched safety trips."""
        self.is_latched_estop = False
        self.estop_reason = ""
        self.active_faults.clear()
        self.active_warnings.clear()
        self.safe_envelope_duration_s = 0.0

    def evaluate(
        self,
        dt: float,
        readings: SensorReadings,
        current_state: TurbineOperatingState
    ) -> tuple[TurbineOperatingState, list[str], list[str], str]:
        """Evaluates sensor readings against safety limits and returns recommended operating state."""
        warnings: list[str] = []
        faults: list[str] = []

        # 1. Check Latched Emergency Stop
        if self.is_latched_estop:
            return TurbineOperatingState.EMERGENCY_STOP, self.active_warnings, self.active_faults, f"LATCHED_ESTOP: {self.estop_reason}"

        # 2. Check Sensor Data Integrity & Communication
        if not readings.is_valid or readings.sensor_fault_flags:
            faults.extend(readings.sensor_fault_flags or ["INVALID_SENSOR_DATA"])
            return TurbineOperatingState.FAULT, warnings, faults, "CRITICAL_SENSOR_FAULT_FAILSAFE"

        if math.isnan(readings.generator_speed_rpm) or math.isnan(readings.rotor_speed_rpm):
            faults.append("SENSOR_NAN_VALUE")
            return TurbineOperatingState.FAULT, warnings, faults, "SENSOR_NAN_TRIP"

        # 3. Critical Overspeed Trip (Hard Trip)
        if readings.generator_speed_rpm >= self.thresholds.max_generator_rpm_trip:
            self.is_latched_estop = True
            self.estop_reason = f"CRITICAL_OVERSPEED_TRIP: {readings.generator_speed_rpm:.1f} RPM >= {self.thresholds.max_generator_rpm_trip:.1f} RPM"
            faults.append("ROTOR_OVERSPEED_CRITICAL")
            self.active_faults = faults
            return TurbineOperatingState.EMERGENCY_STOP, warnings, faults, self.estop_reason

        # 4. Critical Structural Vibration Trip
        if readings.vibration_mm_s >= self.thresholds.max_vibration_trip_mm_s:
            faults.append(f"EXCESSIVE_VIBRATION_TRIP: {readings.vibration_mm_s:.2f} mm/s")
            return TurbineOperatingState.FAULT, warnings, faults, "STRUCTURAL_VIBRATION_TRIP"

        # 5. Critical Generator Thermal Overheat Trip
        if readings.generator_temp_c >= self.thresholds.max_generator_temp_trip_c:
            faults.append(f"GENERATOR_OVERHEAT_TRIP: {readings.generator_temp_c:.1f} C")
            return TurbineOperatingState.SHUTDOWN, warnings, faults, "GENERATOR_THERMAL_SHUTDOWN"

        # 6. Storm Cut-Out Wind Speed
        if readings.wind_speed_ms >= self.thresholds.max_wind_speed_trip_ms:
            warnings.append(f"HIGH_WIND_CUTOUT: {readings.wind_speed_ms:.1f} m/s")
            return TurbineOperatingState.SHUTDOWN, warnings, faults, "HIGH_WIND_STORM_SHUTDOWN"

        # 7. Warning & Derating Level Checks
        has_warning = False

        if readings.generator_speed_rpm >= self.thresholds.max_generator_rpm_warning:
            warnings.append(f"OVERSPEED_WARNING: {readings.generator_speed_rpm:.1f} RPM")
            has_warning = True

        if readings.generator_temp_c >= self.thresholds.max_generator_temp_warning_c:
            warnings.append(f"GENERATOR_TEMP_HIGH: {readings.generator_temp_c:.1f} C")
            has_warning = True

        if readings.vibration_mm_s >= self.thresholds.max_vibration_warning_mm_s:
            warnings.append(f"VIBRATION_HIGH: {readings.vibration_mm_s:.2f} mm/s")
            has_warning = True

        self.active_warnings = warnings
        self.active_faults = faults

        # Decide State
        if faults:
            return TurbineOperatingState.FAULT, warnings, faults, "FAULT_ACTIVE"

        if has_warning:
            return TurbineOperatingState.DERATED, warnings, faults, "DERATED_FOR_SAFETY"

        # Check recovery timing if currently in SHUTDOWN / FAULT
        if current_state in (TurbineOperatingState.SHUTDOWN, TurbineOperatingState.FAULT):
            if readings.wind_speed_ms <= self.params.cut_in_restart_wind_speed_ms:
                self.safe_envelope_duration_s += dt
                if self.safe_envelope_duration_s >= self.thresholds.fault_recovery_hold_seconds:
                    return TurbineOperatingState.RESTARTING, warnings, faults, "AUTOMATIC_FAULT_RECOVERY"
            else:
                self.safe_envelope_duration_s = 0.0
            return current_state, warnings, faults, "WAITING_SAFE_ENVELOPE"

        return TurbineOperatingState.NORMAL, warnings, faults, "NORMAL_ENVELOPE"
