"""Pitch angle PID controller for above-rated aerodynamic power and speed regulation."""

from turbineguard.config import ControllerConfig, TurbineParameters


class PitchController:
    """PID Blade Pitch Controller for Region 3 aerodynamic power & rotor speed regulation."""

    def __init__(
        self,
        config: ControllerConfig | None = None,
        turbine_params: TurbineParameters | None = None
    ):
        self.config = config or ControllerConfig()
        self.params = turbine_params or TurbineParameters()
        
        # PID State
        self.integral_error = 0.0
        self.prev_error = 0.0
        self.prev_measurement = 0.0
        self.target_gen_rpm = self.params.rated_generator_rpm

    def reset(self) -> None:
        """Resets integrator and derivative history."""
        self.integral_error = 0.0
        self.prev_error = 0.0
        self.prev_measurement = 0.0

    def compute_pitch_demand(
        self,
        dt: float,
        measured_gen_rpm: float,
        wind_speed_ms: float,
        current_pitch_deg: float,
        is_feathered_mode: bool = False
    ) -> float:
        """Calculates pitch demand angle in degrees based on generator speed error in Region 3."""
        if is_feathered_mode or wind_speed_ms >= self.params.cut_out_wind_speed_ms:
            # Full feathering for shutdown / emergency
            return self.params.max_pitch_angle_deg

        # Active pitch control feedforward from wind speed
        ff_pitch = 0.0
        if wind_speed_ms > self.params.rated_wind_speed_ms:
            excess_wind = wind_speed_ms - self.params.rated_wind_speed_ms
            ff_pitch = 2.4 * excess_wind + 0.08 * (excess_wind ** 2)

        # Region 2 (Below rated speed and below rated wind): fine pitch = 0 deg
        if wind_speed_ms < self.params.rated_wind_speed_ms and measured_gen_rpm < (self.target_gen_rpm * 0.94):
            self.integral_error = max(0.0, self.integral_error - 1.0 * dt)
            self.prev_error = 0.0
            return self.params.min_pitch_angle_deg

        # Region 3 / Knee Region Pitch PID Regulation
        error = measured_gen_rpm - (self.target_gen_rpm * 0.96)
        
        # Proportional term (swift reaction to prevent overspeed excursion)
        p_term = 4.5 * (error / 50.0)
        
        # Integral term with anti-windup clamping
        self.integral_error += (error / 50.0) * dt
        self.integral_error = max(
            self.config.pitch_integral_min,
            min(self.config.pitch_integral_max, self.integral_error)
        )
        i_term = self.config.pitch_ki * self.integral_error
        
        # Derivative on measurement
        d_error = (error - self.prev_error) / max(0.001, dt)
        d_term = 0.35 * (d_error / 50.0)
        self.prev_error = error

        # Compute raw pitch command
        raw_pitch = ff_pitch + max(0.0, p_term + i_term + d_term)

        # Clamp between 0 and 90 degrees
        pitch_cmd = max(self.params.min_pitch_angle_deg, min(self.params.max_pitch_angle_deg, raw_pitch))
        return float(pitch_cmd)
