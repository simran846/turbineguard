"""Master Wind Turbine Controller and Finite State Machine orchestrator."""

from turbineguard.config import ControllerConfig, SafetyThresholds, TurbineParameters
from turbineguard.controller.pitch_controller import PitchController
from turbineguard.controller.safety_controller import SafetySupervisor
from turbineguard.controller.speed_controller import SpeedTorqueController
from turbineguard.models import ControlCommand, ControlRegion, SensorReadings, TurbineOperatingState


class TurbineController:
    """Integrated master controller managing state transitions, aerodynamics, generator, and safety."""

    def __init__(
        self,
        turbine_params: TurbineParameters | None = None,
        controller_config: ControllerConfig | None = None,
        safety_thresholds: SafetyThresholds | None = None
    ):
        self.params = turbine_params or TurbineParameters()
        self.config = controller_config or ControllerConfig()
        self.thresholds = safety_thresholds or SafetyThresholds()
        
        # Sub-controllers
        self.pitch_controller = PitchController(self.config, self.params)
        self.speed_controller = SpeedTorqueController(self.config, self.params)
        self.safety_supervisor = SafetySupervisor(self.thresholds, self.params)
        
        # Master State Machine
        self.current_state = TurbineOperatingState.STARTING
        self.current_region = ControlRegion.REGION_1
        self.startup_timer_s = 0.0

    def reset(self, initial_state: TurbineOperatingState = TurbineOperatingState.STARTING) -> None:
        """Resets controller state machines and sub-controllers."""
        self.pitch_controller.reset()
        self.safety_supervisor.reset_trips()
        self.current_state = initial_state
        self.current_region = ControlRegion.REGION_1
        self.startup_timer_s = 0.0

    def compute_cycle(
        self,
        dt: float,
        readings: SensorReadings
    ) -> ControlCommand:
        """Executes one real-time control cycle and outputs actuator setpoints."""
        # 1. Run Safety Supervisory Checks
        safety_state, warnings, faults, safety_note = self.safety_supervisor.evaluate(
            dt=dt,
            readings=readings,
            current_state=self.current_state
        )

        # 2. State Machine Transitions
        if safety_state == TurbineOperatingState.EMERGENCY_STOP:
            self.current_state = TurbineOperatingState.EMERGENCY_STOP
        elif safety_state in (TurbineOperatingState.FAULT, TurbineOperatingState.SHUTDOWN):
            self.current_state = safety_state
        elif safety_state == TurbineOperatingState.DERATED:
            self.current_state = TurbineOperatingState.DERATED
        elif safety_state == TurbineOperatingState.NORMAL and self.current_state == TurbineOperatingState.DERATED:
            self.current_state = TurbineOperatingState.NORMAL
        elif safety_state == TurbineOperatingState.RESTARTING:
            self.current_state = TurbineOperatingState.STARTING
            self.startup_timer_s = 0.0

        # State Execution Logic
        target_pitch = self.params.max_pitch_angle_deg
        target_torque = 0.0
        brake_engaged = False
        demanded_power = 0.0
        action_note = safety_note

        if self.current_state == TurbineOperatingState.EMERGENCY_STOP:
            # Full feathering, mechanical brake applied, zero generator torque
            target_pitch = self.params.max_pitch_angle_deg
            target_torque = 0.0
            brake_engaged = True
            action_note = f"EMERGENCY_SHUTDOWN_ACTIVE: {safety_note}"

        elif self.current_state in (TurbineOperatingState.SHUTDOWN, TurbineOperatingState.FAULT):
            # Normal shutdown feathering
            target_pitch = self.params.max_pitch_angle_deg
            target_torque = 0.0
            brake_engaged = (readings.rotor_speed_rpm < 2.0)
            action_note = f"SHUTDOWN_FEATHERING: {safety_note}"

        elif self.current_state == TurbineOperatingState.PARKED:
            target_pitch = self.params.max_pitch_angle_deg
            target_torque = 0.0
            brake_engaged = True
            action_note = "TURBINE_PARKED"

        elif self.current_state == TurbineOperatingState.STARTING:
            # Startup ramp: pitch smoothly transitions towards 0 deg fine pitch
            self.startup_timer_s += dt
            if readings.wind_speed_ms < self.params.cut_in_wind_speed_ms:
                target_pitch = 60.0
                target_torque = 0.0
                brake_engaged = False
                action_note = "STARTING_WAITING_CUT_IN_WIND"
            else:
                # Release brake and pitch down smoothly
                brake_engaged = False
                target_pitch = max(0.0, 90.0 - (self.startup_timer_s * 6.0))
                target_torque = 0.0
                if target_pitch <= 0.0 and readings.generator_speed_rpm >= self.thresholds.min_operational_rpm:
                    self.current_state = TurbineOperatingState.NORMAL
                    action_note = "STARTUP_COMPLETE_ENTER_NORMAL"

        elif self.current_state in (TurbineOperatingState.NORMAL, TurbineOperatingState.DERATED, TurbineOperatingState.WARNING):
            derate_factor = self.config.derated_power_ratio if self.current_state == TurbineOperatingState.DERATED else 1.0
            
            # Compute Pitch angle
            target_pitch = self.pitch_controller.compute_pitch_demand(
                dt=dt,
                measured_gen_rpm=readings.generator_speed_rpm,
                wind_speed_ms=readings.wind_speed_ms,
                current_pitch_deg=readings.pitch_angle_deg,
                is_feathered_mode=False
            )

            # Compute Generator Torque
            target_torque, region = self.speed_controller.compute_torque_demand(
                wind_speed_ms=readings.wind_speed_ms,
                measured_gen_rpm=readings.generator_speed_rpm,
                derated_ratio=derate_factor,
                is_braking=False
            )
            self.current_region = region
            brake_engaged = False
            demanded_power = self.params.rated_electrical_power_kw * derate_factor

            if warnings:
                action_note = f"OPERATING_DERATED_WARNING: {', '.join(warnings)}"
            else:
                action_note = f"NORMAL_CONTROL_{region.value}"

        return ControlCommand(
            target_pitch_angle_deg=float(target_pitch),
            target_generator_torque_nm=float(target_torque),
            mechanical_brake_engaged=brake_engaged,
            demanded_state=self.current_state,
            demanded_power_kw=float(demanded_power),
            active_warnings=warnings,
            active_faults=faults,
            action_note=action_note
        )
