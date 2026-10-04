"""Sensor models with realistic measurement noise, quantization, and fault injection hooks."""

import numpy as np

from turbineguard.models import SensorReadings


class SensorSuite:
    """Manages acquisition of turbine physical state with sensor imperfections and fault modes."""

    def __init__(
        self,
        enable_noise: bool = True,
        seed: int | None = 42
    ):
        self.enable_noise = enable_noise
        self.rng = np.random.RandomState(seed)
        
        # Sensor Fault Overrides
        self.fault_overrides: dict[str, dict] = {}
        self.stale_cache: SensorReadings | None = None
        self.comm_failure_active: bool = False

    def inject_sensor_override(self, sensor_name: str, override_type: str, value: float = 0.0) -> None:
        """Configures a sensor override (stuck, bias, scale, nan, zero)."""
        self.fault_overrides[sensor_name] = {
            "type": override_type,
            "value": value
        }

    def clear_sensor_overrides(self) -> None:
        """Clears all active sensor fault overrides."""
        self.fault_overrides.clear()
        self.comm_failure_active = False

    def set_comm_failure(self, active: bool) -> None:
        """Simulates complete loss of CAN/Modbus bus communication."""
        self.comm_failure_active = active

    def read_sensors(
        self,
        timestamp: float,
        actual_wind_speed_ms: float,
        actual_rotor_speed_rpm: float,
        actual_generator_speed_rpm: float,
        actual_pitch_angle_deg: float,
        actual_generator_power_kw: float,
        actual_rotor_torque_knm: float,
        actual_generator_temp_c: float,
        actual_nacelle_temp_c: float,
        actual_vibration_mm_s: float
    ) -> SensorReadings:
        """Transforms ground-truth physical state into sensed measurements with noise and faults."""
        if self.comm_failure_active:
            # Complete communication loss
            return SensorReadings(
                timestamp=timestamp,
                wind_speed_ms=0.0,
                rotor_speed_rpm=0.0,
                generator_speed_rpm=0.0,
                pitch_angle_deg=0.0,
                generator_power_kw=0.0,
                rotor_torque_knm=0.0,
                generator_temp_c=0.0,
                nacelle_temp_c=0.0,
                vibration_mm_s=0.0,
                is_valid=False,
                sensor_fault_flags=["COMMUNICATION_TIMEOUT_BUS_OFF"]
            )

        # Check for Stale Sensor Data fault
        if "stale_data" in self.fault_overrides and self.stale_cache is not None:
            cached = self.stale_cache
            return SensorReadings(
                timestamp=timestamp,
                wind_speed_ms=cached.wind_speed_ms,
                rotor_speed_rpm=cached.rotor_speed_rpm,
                generator_speed_rpm=cached.generator_speed_rpm,
                pitch_angle_deg=cached.pitch_angle_deg,
                generator_power_kw=cached.generator_power_kw,
                rotor_torque_knm=cached.rotor_torque_knm,
                generator_temp_c=cached.generator_temp_c,
                nacelle_temp_c=cached.nacelle_temp_c,
                vibration_mm_s=cached.vibration_mm_s,
                is_valid=True,
                sensor_fault_flags=["STALE_DATA_FROZEN"]
            )

        # Apply standard Gaussian sensor noise if enabled
        noise_wind = self.rng.normal(0, 0.15) if self.enable_noise else 0.0
        noise_rotor = self.rng.normal(0, 0.05) if self.enable_noise else 0.0
        noise_gen = self.rng.normal(0, 2.5) if self.enable_noise else 0.0
        noise_pitch = self.rng.normal(0, 0.04) if self.enable_noise else 0.0
        noise_power = self.rng.normal(0, 5.0) if self.enable_noise else 0.0
        noise_torque = self.rng.normal(0, 0.5) if self.enable_noise else 0.0
        noise_temp_g = self.rng.normal(0, 0.2) if self.enable_noise else 0.0
        noise_temp_n = self.rng.normal(0, 0.2) if self.enable_noise else 0.0
        noise_vib = self.rng.normal(0, 0.05) if self.enable_noise else 0.0

        s_wind = max(0.0, actual_wind_speed_ms + noise_wind)
        s_rotor = max(0.0, actual_rotor_speed_rpm + noise_rotor)
        s_gen = max(0.0, actual_generator_speed_rpm + noise_gen)
        s_pitch = actual_pitch_angle_deg + noise_pitch
        s_power = max(0.0, actual_generator_power_kw + noise_power)
        s_torque = actual_rotor_torque_knm + noise_torque
        s_gen_temp = actual_generator_temp_c + noise_temp_g
        s_nac_temp = actual_nacelle_temp_c + noise_temp_n
        s_vib = max(0.0, actual_vibration_mm_s + noise_vib)

        fault_flags: list[str] = []
        is_valid = True

        # Process Sensor Specific Overrides
        for sensor, cfg in self.fault_overrides.items():
            ftype = cfg["type"]
            fval = cfg["value"]

            if sensor == "rotor_speed":
                if ftype == "stuck":
                    s_rotor = fval
                elif ftype == "zero":
                    s_rotor = 0.0
                    fault_flags.append("ROTOR_SPEED_SENSOR_ZERO")
                elif ftype == "invalid":
                    s_rotor = float("nan")
                    is_valid = False
                    fault_flags.append("ROTOR_SPEED_SENSOR_NAN")
                elif ftype == "spike":
                    s_rotor += fval

            elif sensor == "generator_speed":
                if ftype == "stuck":
                    s_gen = fval
                elif ftype == "zero":
                    s_gen = 0.0
                    fault_flags.append("GEN_SPEED_SENSOR_ZERO")
                elif ftype == "spike":
                    s_gen += fval

            elif sensor == "wind_speed":
                if ftype == "stuck":
                    s_wind = fval
                elif ftype == "zero":
                    s_wind = 0.0
                elif ftype == "invalid":
                    s_wind = -999.0
                    is_valid = False
                    fault_flags.append("WIND_SPEED_OUT_OF_RANGE")

            elif sensor == "vibration":
                if ftype == "spike":
                    s_vib += fval

            elif sensor == "generator_temp" and ftype == "spike":
                s_gen_temp += fval

        readings = SensorReadings(
            timestamp=timestamp,
            wind_speed_ms=s_wind,
            rotor_speed_rpm=s_rotor,
            generator_speed_rpm=s_gen,
            pitch_angle_deg=s_pitch,
            generator_power_kw=s_power,
            rotor_torque_knm=s_torque,
            generator_temp_c=s_gen_temp,
            nacelle_temp_c=s_nac_temp,
            vibration_mm_s=s_vib,
            is_valid=is_valid,
            sensor_fault_flags=fault_flags
        )

        self.stale_cache = readings
        return readings
