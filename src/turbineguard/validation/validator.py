"""Automated Validation Engine for TurbineGuard engineering verification."""

import time
from dataclasses import dataclass, field

import numpy as np

from turbineguard.config import (
    SimulationConfig,
)
from turbineguard.controller.controller import TurbineController
from turbineguard.faults.fault_injection import FaultInjector
from turbineguard.faults.fault_types import FaultTypeEnum
from turbineguard.models import (
    FaultSeverity,
    SensorReadings,
    TurbineOperatingState,
    TurbineTelemetry,
    ValidationResultItem,
    ValidationStatus,
)
from turbineguard.simulator.environment import WindEnvironment, WindScenarioType
from turbineguard.simulator.sensors import SensorSuite
from turbineguard.simulator.turbine import WindTurbineSimulator
from turbineguard.validation.requirements import ENGINEERING_REQUIREMENTS
from turbineguard.validation.tolerance import (
    check_boundary_tolerance,
    check_max_limit,
)


@dataclass
class ValidationSuiteResult:
    """Consolidated summary of an entire automated validation test execution."""
    suite_name: str
    total_requirements: int
    passed_count: int
    failed_count: int
    warning_count: int
    pass_rate_pct: float
    total_execution_time_ms: float
    results: list[ValidationResultItem] = field(default_factory=list)
    failed_req_ids: list[str] = field(default_factory=list)


class ValidationEngine:
    """Orchestrates closed-loop simulations and evaluates formal engineering requirements."""

    def __init__(self, sim_config: SimulationConfig | None = None):
        self.config = sim_config or SimulationConfig()

    def run_closed_loop_simulation(
        self,
        duration_s: float,
        wind_scenario: WindScenarioType = WindScenarioType.CONSTANT,
        base_wind_speed_ms: float = 9.0,
        fault_injector: FaultInjector | None = None,
        initial_rotor_rpm: float = 12.0,
        initial_pitch_deg: float = 0.0,
        initial_temp_c: float = 40.0
    ) -> list[TurbineTelemetry]:
        """Runs a complete time-domain closed-loop simulation and records high-resolution telemetry."""
        dt = self.config.dt
        steps = int(duration_s / dt)
        
        env = WindEnvironment(
            base_wind_speed_ms=base_wind_speed_ms,
            scenario=wind_scenario,
            air_density_kg_m3=self.config.turbine_params.air_density_kg_m3,
            ambient_temp_c=self.config.turbine_params.ambient_temp_c,
            seed=self.config.seed
        )
        # If starting in high wind with default 0 deg pitch, set aerodynamic baseline initial pitch
        init_pitch = initial_pitch_deg
        if base_wind_speed_ms > 11.5 and initial_pitch_deg == 0.0:
            init_pitch = max(0.0, 1.85 * (base_wind_speed_ms - 11.5))

        simulator = WindTurbineSimulator(
            params=self.config.turbine_params,
            initial_rotor_rpm=initial_rotor_rpm,
            initial_pitch_deg=init_pitch,
            initial_temp_c=initial_temp_c
        )
        sensors = SensorSuite(enable_noise=False, seed=self.config.seed)
        controller = TurbineController(
            turbine_params=self.config.turbine_params,
            controller_config=self.config.controller_config,
            safety_thresholds=self.config.safety_thresholds
        )
        # Set controller initial state to NORMAL if starting spinning
        if initial_rotor_rpm > 5.0:
            controller.current_state = TurbineOperatingState.NORMAL

        telemetry: list[TurbineTelemetry] = []

        for step_idx in range(steps):
            t = step_idx * dt
            
            # Fault injection step update
            active_faults = []
            if fault_injector:
                active_faults = fault_injector.process_step(
                    current_time_s=t,
                    simulator=simulator,
                    sensor_suite=sensors,
                    controller_state=controller.current_state
                )

            # Inflow Wind
            v_wind = env.get_wind_speed(t)

            # Sensor acquisition
            sensed = sensors.read_sensors(
                timestamp=t,
                actual_wind_speed_ms=v_wind,
                actual_rotor_speed_rpm=simulator.rotor_speed_rpm,
                actual_generator_speed_rpm=simulator.generator_speed_rpm,
                actual_pitch_angle_deg=simulator.pitch_angle_deg,
                actual_generator_power_kw=simulator.electrical_power_kw,
                actual_rotor_torque_knm=simulator.rotor_torque_nm / 1000.0,
                actual_generator_temp_c=simulator.generator_temp_c,
                actual_nacelle_temp_c=simulator.nacelle_temp_c,
                actual_vibration_mm_s=simulator.vibration_mm_s
            )

            # Controller computation
            cmd = controller.compute_cycle(dt, sensed)

            # Physical plant step
            sim_out = simulator.step(dt, v_wind, cmd)

            # Record telemetry
            active_fault_str = active_faults[0].name if active_faults else None
            record = TurbineTelemetry(
                step=step_idx,
                timestamp=round(t, 4),
                wind_speed_ms=v_wind,
                pitch_angle_deg=sim_out["pitch_angle_deg"],
                target_pitch_deg=cmd.target_pitch_angle_deg,
                rotor_speed_rpm=sim_out["rotor_speed_rpm"],
                generator_speed_rpm=sim_out["generator_speed_rpm"],
                target_torque_nm=cmd.target_generator_torque_nm,
                aerodynamic_power_kw=sim_out["aerodynamic_power_kw"],
                electrical_power_kw=sim_out["electrical_power_kw"],
                generator_temp_c=sim_out["generator_temp_c"],
                nacelle_temp_c=sim_out["nacelle_temp_c"],
                vibration_mm_s=sim_out["vibration_mm_s"],
                operating_state=cmd.demanded_state,
                control_region=controller.current_region,
                brake_engaged=cmd.mechanical_brake_engaged,
                active_fault=active_fault_str,
                action_log=cmd.action_note
            )
            telemetry.append(record)

        if fault_injector:
            fault_injector.finalize_verification()

        return telemetry

    def validate_all(self) -> ValidationSuiteResult:
        """Executes full automated verification suite across all engineering requirements."""
        start_wall = time.perf_counter()
        results: list[ValidationResultItem] = []

        # REQ-001: Region 2 MPPT rotor speed tracking
        t0 = time.perf_counter()
        telemetry_r2 = self.run_closed_loop_simulation(
            duration_s=15.0,
            wind_scenario=WindScenarioType.CONSTANT,
            base_wind_speed_ms=8.0,
            initial_rotor_rpm=10.0,
            initial_pitch_deg=0.0
        )
        # Check steady state generator speed (last 5 seconds)
        recent_speeds = [p.generator_speed_rpm for p in telemetry_r2 if p.timestamp >= 10.0]
        mean_speed = float(np.mean(recent_speeds))
        status, msg = check_boundary_tolerance(mean_speed, target=1100.0, tolerance=400.0)
        results.append(ValidationResultItem(
            req_id="REQ-001",
            title=ENGINEERING_REQUIREMENTS["REQ-001"].title,
            status=status,
            measured_value=mean_speed,
            expected_value=1100.0,
            tolerance=400.0,
            unit="RPM",
            message=msg,
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        # REQ-002: Region 3 rated power regulation
        t0 = time.perf_counter()
        telemetry_r3 = self.run_closed_loop_simulation(
            duration_s=20.0,
            wind_scenario=WindScenarioType.CONSTANT,
            base_wind_speed_ms=14.0,
            initial_rotor_rpm=15.79,
            initial_pitch_deg=6.0
        )
        recent_powers = [p.electrical_power_kw for p in telemetry_r3 if p.timestamp >= 10.0]
        mean_power = float(np.mean(recent_powers))
        status, msg = check_max_limit(mean_power, limit=2500.0, tolerance=125.0)
        results.append(ValidationResultItem(
            req_id="REQ-002",
            title=ENGINEERING_REQUIREMENTS["REQ-002"].title,
            status=status,
            measured_value=mean_power,
            expected_value=2500.0,
            tolerance=125.0,
            unit="kW",
            message=msg,
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        # REQ-003: Critical Rotor Overspeed Hard Trip
        t0 = time.perf_counter()
        fi_overspeed = FaultInjector()
        fi_overspeed.add_fault(
            fault_id="F-OVERSPEED",
            fault_type=FaultTypeEnum.ROTOR_OVERSPEED,
            start_time_s=5.0,
            duration_s=2.0,
            severity=FaultSeverity.CRITICAL,
            magnitude=1.0
        )
        self.run_closed_loop_simulation(
            duration_s=10.0,
            wind_scenario=WindScenarioType.CONSTANT,
            base_wind_speed_ms=11.5,
            fault_injector=fi_overspeed,
            initial_rotor_rpm=15.79
        )
        f_res = fi_overspeed.results[0]
        status = ValidationStatus.PASSED if f_res.passed_verification else ValidationStatus.FAILED
        results.append(ValidationResultItem(
            req_id="REQ-003",
            title=ENGINEERING_REQUIREMENTS["REQ-003"].title,
            status=status,
            measured_value=f_res.response_time_ms,
            expected_value=250.0,
            tolerance=50.0,
            unit="ms",
            message=f_res.details,
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        # REQ-004: High Wind Cut-Out Storm Shutdown
        t0 = time.perf_counter()
        telemetry_storm = self.run_closed_loop_simulation(
            duration_s=30.0,
            wind_scenario=WindScenarioType.HIGH_WIND_CUTOUT,
            base_wind_speed_ms=14.0,
            initial_rotor_rpm=15.79
        )
        final_pitch = telemetry_storm[-1].pitch_angle_deg
        final_state = telemetry_storm[-1].operating_state
        is_shut = final_state in (TurbineOperatingState.SHUTDOWN, TurbineOperatingState.PARKED) and final_pitch >= 85.0
        status = ValidationStatus.PASSED if is_shut else ValidationStatus.FAILED
        results.append(ValidationResultItem(
            req_id="REQ-004",
            title=ENGINEERING_REQUIREMENTS["REQ-004"].title,
            status=status,
            measured_value=final_pitch,
            expected_value=90.0,
            tolerance=5.0,
            unit="deg",
            message=f"State: {final_state.value}, Pitch: {final_pitch:.1f} deg",
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        # REQ-005: Generator Overheat Protective Trip
        t0 = time.perf_counter()
        fi_heat = FaultInjector()
        fi_heat.add_fault(
            fault_id="F-OVERHEAT",
            fault_type=FaultTypeEnum.GENERATOR_OVERHEAT,
            start_time_s=4.0,
            duration_s=3.0,
            severity=FaultSeverity.CRITICAL
        )
        self.run_closed_loop_simulation(
            duration_s=10.0,
            wind_scenario=WindScenarioType.CONSTANT,
            base_wind_speed_ms=10.0,
            fault_injector=fi_heat,
            initial_rotor_rpm=14.0
        )
        f_heat_res = fi_heat.results[0]
        status = ValidationStatus.PASSED if f_heat_res.passed_verification else ValidationStatus.FAILED
        results.append(ValidationResultItem(
            req_id="REQ-005",
            title=ENGINEERING_REQUIREMENTS["REQ-005"].title,
            status=status,
            measured_value=f_heat_res.response_time_ms,
            expected_value=1000.0,
            tolerance=200.0,
            unit="ms",
            message=f_heat_res.details,
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        # REQ-006: Thermal High-Warning Power Derating
        t0 = time.perf_counter()
        # Test direct controller derate logic on 88 C
        test_controller = TurbineController(
            turbine_params=self.config.turbine_params,
            controller_config=self.config.controller_config,
            safety_thresholds=self.config.safety_thresholds
        )
        test_controller.current_state = TurbineOperatingState.NORMAL
        readings_warm = SensorReadings(
            timestamp=1.0,
            wind_speed_ms=11.5,
            rotor_speed_rpm=15.79,
            generator_speed_rpm=1500.0,
            pitch_angle_deg=0.0,
            generator_power_kw=2500.0,
            rotor_torque_knm=150.0,
            generator_temp_c=88.0,  # Warning level
            nacelle_temp_c=35.0,
            vibration_mm_s=1.2
        )
        cmd_derate = test_controller.compute_cycle(0.05, readings_warm)
        is_derated = cmd_derate.demanded_state == TurbineOperatingState.DERATED and cmd_derate.demanded_power_kw <= 1650.0
        status = ValidationStatus.PASSED if is_derated else ValidationStatus.FAILED
        results.append(ValidationResultItem(
            req_id="REQ-006",
            title=ENGINEERING_REQUIREMENTS["REQ-006"].title,
            status=status,
            measured_value=cmd_derate.demanded_power_kw,
            expected_value=1625.0,
            tolerance=50.0,
            unit="kW",
            message=f"State: {cmd_derate.demanded_state.value}, Demanded Power: {cmd_derate.demanded_power_kw:.1f} kW",
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        # REQ-007: Structural Vibration Trip
        t0 = time.perf_counter()
        fi_vib = FaultInjector()
        fi_vib.add_fault(
            fault_id="F-VIB",
            fault_type=FaultTypeEnum.VIBRATION_SPIKE,
            start_time_s=3.0,
            duration_s=2.0,
            severity=FaultSeverity.HIGH,
            magnitude=1.0
        )
        self.run_closed_loop_simulation(
            duration_s=8.0,
            wind_scenario=WindScenarioType.CONSTANT,
            base_wind_speed_ms=10.0,
            fault_injector=fi_vib,
            initial_rotor_rpm=14.0
        )
        f_vib_res = fi_vib.results[0]
        status = ValidationStatus.PASSED if f_vib_res.passed_verification else ValidationStatus.FAILED
        results.append(ValidationResultItem(
            req_id="REQ-007",
            title=ENGINEERING_REQUIREMENTS["REQ-007"].title,
            status=status,
            measured_value=f_vib_res.response_time_ms,
            expected_value=300.0,
            tolerance=100.0,
            unit="ms",
            message=f_vib_res.details,
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        # REQ-008: Sensor Data Integrity & Failsafe
        t0 = time.perf_counter()
        fi_nan = FaultInjector()
        fi_nan.add_fault(
            fault_id="F-NAN",
            fault_type=FaultTypeEnum.INVALID_SENSOR_VALUE,
            start_time_s=3.0,
            duration_s=2.0,
            severity=FaultSeverity.HIGH
        )
        self.run_closed_loop_simulation(
            duration_s=8.0,
            wind_scenario=WindScenarioType.CONSTANT,
            base_wind_speed_ms=10.0,
            fault_injector=fi_nan,
            initial_rotor_rpm=14.0
        )
        f_nan_res = fi_nan.results[0]
        status = ValidationStatus.PASSED if f_nan_res.passed_verification else ValidationStatus.FAILED
        results.append(ValidationResultItem(
            req_id="REQ-008",
            title=ENGINEERING_REQUIREMENTS["REQ-008"].title,
            status=status,
            measured_value=f_nan_res.response_time_ms,
            expected_value=200.0,
            tolerance=100.0,
            unit="ms",
            message=f_nan_res.details,
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        # REQ-009: Communication Bus Loss Protection
        t0 = time.perf_counter()
        fi_comm = FaultInjector()
        fi_comm.add_fault(
            fault_id="F-COMM",
            fault_type=FaultTypeEnum.COMMUNICATION_FAILURE,
            start_time_s=3.0,
            duration_s=2.0,
            severity=FaultSeverity.CRITICAL
        )
        self.run_closed_loop_simulation(
            duration_s=8.0,
            wind_scenario=WindScenarioType.CONSTANT,
            base_wind_speed_ms=10.0,
            fault_injector=fi_comm,
            initial_rotor_rpm=14.0
        )
        f_comm_res = fi_comm.results[0]
        status = ValidationStatus.PASSED if f_comm_res.passed_verification else ValidationStatus.FAILED
        results.append(ValidationResultItem(
            req_id="REQ-009",
            title=ENGINEERING_REQUIREMENTS["REQ-009"].title,
            status=status,
            measured_value=f_comm_res.response_time_ms,
            expected_value=500.0,
            tolerance=100.0,
            unit="ms",
            message=f_comm_res.details,
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        # REQ-010: Pitch Actuator Normal Rate Limiting
        t0 = time.perf_counter()
        telemetry_step = self.run_closed_loop_simulation(
            duration_s=20.0,
            wind_scenario=WindScenarioType.STEP,
            base_wind_speed_ms=10.0,
            initial_rotor_rpm=15.79
        )
        dt = self.config.dt
        normal_rates = [
            abs((telemetry_step[i+1].pitch_angle_deg - telemetry_step[i].pitch_angle_deg) / dt)
            for i in range(len(telemetry_step)-1)
            if telemetry_step[i].operating_state in (TurbineOperatingState.NORMAL, TurbineOperatingState.DERATED)
        ]
        max_pitch_rate = float(max(normal_rates)) if normal_rates else 0.0
        status, msg = check_max_limit(max_pitch_rate, limit=8.0, tolerance=0.1)
        results.append(ValidationResultItem(
            req_id="REQ-010",
            title=ENGINEERING_REQUIREMENTS["REQ-010"].title,
            status=status,
            measured_value=max_pitch_rate,
            expected_value=8.0,
            tolerance=0.1,
            unit="deg/s",
            message=msg,
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        # REQ-011: Automatic Fault Recovery Hysteresis
        t0 = time.perf_counter()
        test_sup = TurbineController(
            turbine_params=self.config.turbine_params,
            controller_config=self.config.controller_config,
            safety_thresholds=self.config.safety_thresholds
        )
        test_sup.current_state = TurbineOperatingState.SHUTDOWN
        # Pass 6 seconds of calm wind (v = 8 m/s < 22 m/s restart threshold)
        recovered = False
        hold_time = 0.0
        for step in range(120):  # 120 * 0.05 = 6.0s
            r = SensorReadings(
                timestamp=step * 0.05,
                wind_speed_ms=8.0,
                rotor_speed_rpm=1.0,
                generator_speed_rpm=95.0,
                pitch_angle_deg=90.0,
                generator_power_kw=0.0,
                rotor_torque_knm=0.0,
                generator_temp_c=30.0,
                nacelle_temp_c=25.0,
                vibration_mm_s=0.8
            )
            c = test_sup.compute_cycle(0.05, r)
            if c.demanded_state == TurbineOperatingState.STARTING:
                recovered = True
                hold_time = step * 0.05
                break
        status = ValidationStatus.PASSED if (recovered and hold_time >= 5.0) else ValidationStatus.FAILED
        results.append(ValidationResultItem(
            req_id="REQ-011",
            title=ENGINEERING_REQUIREMENTS["REQ-011"].title,
            status=status,
            measured_value=hold_time,
            expected_value=5.0,
            tolerance=0.5,
            unit="s",
            message=f"Auto recovery triggered at t={hold_time:.2f}s (Required hold: 5.0s)",
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        # REQ-012: Extreme Operating Gust (EOG) Dynamic Stability
        t0 = time.perf_counter()
        telemetry_gust = self.run_closed_loop_simulation(
            duration_s=30.0,
            wind_scenario=WindScenarioType.GUST,
            base_wind_speed_ms=11.5,
            initial_rotor_rpm=15.79,
            initial_pitch_deg=0.0
        )
        max_rpm_during_gust = float(max(p.generator_speed_rpm for p in telemetry_gust))
        status, msg = check_max_limit(max_rpm_during_gust, limit=1725.0, tolerance=0.0)
        results.append(ValidationResultItem(
            req_id="REQ-012",
            title=ENGINEERING_REQUIREMENTS["REQ-012"].title,
            status=status,
            measured_value=max_rpm_during_gust,
            expected_value=1725.0,
            tolerance=0.0,
            unit="RPM",
            message=msg,
            execution_time_ms=(time.perf_counter() - t0) * 1000.0
        ))

        total_exec_ms = (time.perf_counter() - start_wall) * 1000.0
        passed = [r for r in results if r.status == ValidationStatus.PASSED]
        failed = [r for r in results if r.status == ValidationStatus.FAILED]
        warnings = [r for r in results if r.status == ValidationStatus.WARNING]
        pass_rate = (len(passed) / len(results) * 100.0) if results else 0.0

        return ValidationSuiteResult(
            suite_name="TurbineGuard Core Engineering Verification Suite",
            total_requirements=len(results),
            passed_count=len(passed),
            failed_count=len(failed),
            warning_count=len(warnings),
            pass_rate_pct=round(pass_rate, 2),
            total_execution_time_ms=round(total_exec_ms, 2),
            results=results,
            failed_req_ids=[r.req_id for r in failed]
        )
