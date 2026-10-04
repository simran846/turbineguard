"""Wind turbine physical plant simulation.

Models aero-servo-hydro-electro-mechanical dynamics, rotor aerodynamics,
drivetrain torque balance, generator thermal evolution, and structural vibrations.

NOTE: This is an educational/simulation engineering model and NOT a certified physical model.
All models are based on simplified continuous-time differential equations discretized via Euler/RK2.
"""

import math

from turbineguard.config import TurbineParameters
from turbineguard.models import (
    ControlCommand,
    TurbineOperatingState,
)


class WindTurbineSimulator:
    """Simulates the physical dynamics of a 2.5 MW class variable-speed pitch-regulated turbine."""

    def __init__(
        self,
        params: TurbineParameters | None = None,
        initial_rotor_rpm: float = 0.0,
        initial_pitch_deg: float = 90.0,
        initial_temp_c: float = 25.0
    ):
        self.params = params or TurbineParameters()
        
        # Physical State Variables
        self.rotor_speed_rad_s = initial_rotor_rpm * (2.0 * math.pi / 60.0)
        self.pitch_angle_deg = initial_pitch_deg
        self.pitch_rate_deg_s = 0.0
        self.generator_temp_c = initial_temp_c
        self.nacelle_temp_c = initial_temp_c
        self.vibration_mm_s = self.params.base_vibration_mm_s
        self.mechanical_brake_torque_nm = 0.0
        
        # Calculated Telemetry
        self.aerodynamic_power_kw = 0.0
        self.electrical_power_kw = 0.0
        self.rotor_torque_nm = 0.0
        self.generator_torque_nm = 0.0
        self.cp = 0.0
        self.tsr = 0.0
        
        # Actuator lag time constant
        self.pitch_time_constant_s = 0.15
        
        # Fault injection modifiers
        self.pitch_stuck: bool = False
        self.pitch_stuck_angle: float = 0.0
        self.vibration_spike_magnitude: float = 0.0

    @property
    def rotor_speed_rpm(self) -> float:
        return self.rotor_speed_rad_s * (60.0 / (2.0 * math.pi))

    @property
    def generator_speed_rpm(self) -> float:
        return self.rotor_speed_rpm * self.params.gearbox_ratio

    @property
    def swept_area_m2(self) -> float:
        return math.pi * (self.params.rotor_radius_m ** 2)

    def calculate_cp(self, tip_speed_ratio: float, pitch_angle_deg: float) -> float:
        """Calculates power coefficient Cp(lambda, beta) using standard empirical aero formulation.
        
        Cp is bounded physically: 0 <= Cp <= 0.48 (Betz limit = 0.593).
        """
        beta = max(0.0, min(90.0, pitch_angle_deg))
        tsr = max(0.001, tip_speed_ratio)
        
        # Inverse lambda_i term
        denom = tsr + 0.08 * beta
        if denom <= 0:
            return 0.0
        inv_lambda_i = (1.0 / denom) - (0.035 / (beta**3 + 1.0))
        
        if inv_lambda_i <= 0:
            return 0.0

        c1, c2, c3, c4, c5, c6 = 0.5176, 116.0, 0.4, 5.0, 21.0, 0.0068
        
        try:
            exp_term = math.exp(-c5 * inv_lambda_i)
            cp_val = c1 * (c2 * inv_lambda_i - c3 * beta - c4) * exp_term + c6 * tsr
            return float(max(0.0, min(0.48, cp_val)))
        except OverflowError:
            return 0.0

    def step(
        self,
        dt: float,
        wind_speed_ms: float,
        control_cmd: ControlCommand
    ) -> dict[str, float]:
        """Advances turbine physics state by dt seconds under wind inflow and controller demands."""
        v_wind = max(0.1, wind_speed_ms)
        
        # 1. Pitch Actuator Dynamic Update (Rate limited with 1st order lag)
        target_pitch = control_cmd.target_pitch_angle_deg
        if self.pitch_stuck:
            target_pitch = self.pitch_stuck_angle

        # Fast feathering in emergency stop vs normal rate
        max_rate = (
            self.params.emergency_feather_pitch_rate_deg_s
            if control_cmd.demanded_state == TurbineOperatingState.EMERGENCY_STOP
            else self.params.max_pitch_rate_deg_s
        )

        desired_rate = (target_pitch - self.pitch_angle_deg) / max(0.01, self.pitch_time_constant_s)
        self.pitch_rate_deg_s = max(-max_rate, min(max_rate, desired_rate))
        self.pitch_angle_deg += self.pitch_rate_deg_s * dt
        self.pitch_angle_deg = max(self.params.min_pitch_angle_deg, min(self.params.max_pitch_angle_deg, self.pitch_angle_deg))

        # 2. Aerodynamic Interaction
        # Tip Speed Ratio: lambda = (omega_r * R) / v_wind
        self.tsr = (self.rotor_speed_rad_s * self.params.rotor_radius_m) / v_wind
        self.cp = self.calculate_cp(self.tsr, self.pitch_angle_deg)

        # Aerodynamic Power: P_aero = 0.5 * rho * A * Cp * v^3
        p_aero_watts = 0.5 * self.params.air_density_kg_m3 * self.swept_area_m2 * self.cp * (v_wind ** 3)
        self.aerodynamic_power_kw = p_aero_watts / 1000.0

        # Aerodynamic Torque on low-speed shaft: T_aero = P_aero / omega_r
        if self.rotor_speed_rad_s > 0.05:
            self.rotor_torque_nm = p_aero_watts / self.rotor_speed_rad_s
        else:
            # Low-speed aerodynamic static torque approximation
            self.rotor_torque_nm = 0.5 * self.params.air_density_kg_m3 * self.swept_area_m2 * (0.05) * (v_wind ** 2) * self.params.rotor_radius_m

        # 3. Mechanical Braking Torque
        if control_cmd.mechanical_brake_engaged:
            # High braking torque
            self.mechanical_brake_torque_nm = 1.2e6
        else:
            self.mechanical_brake_torque_nm = 0.0

        # 4. Generator Electromagnetic Counter-Torque
        # High speed shaft torque reflected to low speed shaft via gearbox: T_gen_reflected = N_g * T_g
        self.generator_torque_nm = max(0.0, control_cmd.target_generator_torque_nm)
        gen_torque_lss = self.params.gearbox_ratio * self.generator_torque_nm

        # 5. Drivetrain Rotational Acceleration (Lumped 2-mass equivalent inertia)
        # J_eq * d(omega_r)/dt = T_aero - N_g * T_gen - B_dt * omega_r - T_brake
        j_eq = self.params.rotor_inertia_kg_m2 + (self.params.gearbox_ratio ** 2) * self.params.generator_inertia_kg_m2
        viscous_friction_torque = self.params.drivetrain_damping * self.rotor_speed_rad_s
        
        net_torque = (
            self.rotor_torque_nm
            - gen_torque_lss
            - viscous_friction_torque
            - (self.mechanical_brake_torque_nm if self.rotor_speed_rad_s > 0 else 0.0)
        )

        d_omega_dt = net_torque / j_eq
        self.rotor_speed_rad_s += d_omega_dt * dt
        self.rotor_speed_rad_s = max(0.0, self.rotor_speed_rad_s)

        # 6. Electrical Power Output
        gen_speed_rad_s = self.rotor_speed_rad_s * self.params.gearbox_ratio
        elec_power_watts = self.params.generator_efficiency * self.generator_torque_nm * gen_speed_rad_s
        self.electrical_power_kw = max(0.0, min(self.params.rated_electrical_power_kw * 1.15, elec_power_watts / 1000.0))

        # 7. Thermal Evolution
        # Loss dissipation heating
        elec_losses_kw = max(0.0, (self.aerodynamic_power_kw - self.electrical_power_kw))
        heat_input = elec_losses_kw * self.params.generator_heating_factor * 100.0
        cooling = self.params.generator_cooling_coeff * (self.generator_temp_c - self.params.ambient_temp_c)
        d_temp_dt = (heat_input - cooling)
        self.generator_temp_c += d_temp_dt * dt
        self.generator_temp_c = max(self.params.ambient_temp_c, min(140.0, self.generator_temp_c))
        
        # Nacelle ambient heating
        self.nacelle_temp_c = self.params.ambient_temp_c + 0.15 * (self.generator_temp_c - self.params.ambient_temp_c)

        # 8. Dynamic Vibration Model
        # Vibration increases with mass imbalance, turbulent thrust, high RPM variance
        rated_rad_s = self.params.rated_rotor_rpm * (2.0 * math.pi / 60.0)
        speed_overshoot_ratio = max(0.0, (self.rotor_speed_rad_s - rated_rad_s) / max(0.1, rated_rad_s))
        
        aero_thrust_vibe = 0.025 * (v_wind ** 1.5)
        imbalance_vibe = 4.0 * (speed_overshoot_ratio ** 2)
        self.vibration_mm_s = (
            self.params.base_vibration_mm_s
            + aero_thrust_vibe
            + imbalance_vibe
            + self.vibration_spike_magnitude
        )

        return {
            "rotor_speed_rpm": self.rotor_speed_rpm,
            "generator_speed_rpm": self.generator_speed_rpm,
            "pitch_angle_deg": self.pitch_angle_deg,
            "aerodynamic_power_kw": self.aerodynamic_power_kw,
            "electrical_power_kw": self.electrical_power_kw,
            "rotor_torque_knm": self.rotor_torque_nm / 1000.0,
            "generator_temp_c": self.generator_temp_c,
            "nacelle_temp_c": self.nacelle_temp_c,
            "vibration_mm_s": self.vibration_mm_s,
            "cp": self.cp,
            "tsr": self.tsr,
        }
