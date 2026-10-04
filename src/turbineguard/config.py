"""System configuration and physical parameters for TurbineGuard."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TurbineParameters:
    """Aerodynamic, mechanical, and electrical turbine baseline parameters.
    
    Modeled after a modern 2.5 MW class variable-speed, pitch-regulated wind turbine.
    """
    # Aerodynamic / Rotor specs
    rotor_radius_m: float = 52.0  # Rotor blade radius (m) -> Area ~ 8494 m^2
    air_density_kg_m3: float = 1.225  # Standard sea-level air density
    gearbox_ratio: float = 95.0  # Rotor speed to generator speed gear ratio
    rated_electrical_power_kw: float = 2500.0  # 2.5 MW rated power
    rated_generator_rpm: float = 1500.0  # Rated generator speed (RPM)
    rated_rotor_rpm: float = 15.79  # Rated rotor speed (RPM) = 1500 / 95
    cut_in_wind_speed_ms: float = 3.0  # Cut-in wind speed (m/s)
    rated_wind_speed_ms: float = 11.5  # Rated wind speed (m/s)
    cut_out_wind_speed_ms: float = 25.0  # Cut-out wind speed (m/s)
    cut_in_restart_wind_speed_ms: float = 22.0  # Hysteresis restart wind speed (m/s)
    
    # Inertia & Damping
    rotor_inertia_kg_m2: float = 4.5e6  # Rotor inertia
    generator_inertia_kg_m2: float = 55.0  # Generator inertia (generator side)
    drivetrain_damping: float = 1200.0  # Damping coefficient
    drivetrain_torsional_stiffness: float = 8.5e7  # Drivetrain torsional stiffness
    generator_efficiency: float = 0.94  # Generator + Converter electromechanical efficiency
    
    # Pitch Actuator Limits
    min_pitch_angle_deg: float = 0.0  # Fine pitch angle for power production
    max_pitch_angle_deg: float = 90.0  # Feathered pitch angle for shutdown
    max_pitch_rate_deg_s: float = 8.0  # Maximum pitch rate (deg/s) for normal operation
    emergency_feather_pitch_rate_deg_s: float = 12.0  # Fast pitch rate for emergency stop
    
    # Thermal & Mechanical Dynamics
    ambient_temp_c: float = 25.0
    generator_thermal_mass: float = 2500.0  # Heat capacity factor
    generator_cooling_coeff: float = 0.035  # Cooling coefficient
    generator_heating_factor: float = 0.000045  # Losses to heat conversion
    base_vibration_mm_s: float = 0.8  # Nominal baseline vibration


@dataclass(frozen=True)
class SafetyThresholds:
    """Configurable safety limits and protection trips."""
    max_generator_rpm_warning: float = 1620.0  # 108% of rated
    max_generator_rpm_trip: float = 1725.0  # 115% of rated (Hard Overspeed Trip)
    min_operational_rpm: float = 400.0  # Minimum operational generator RPM
    
    max_generator_temp_warning_c: float = 85.0  # Thermal warning
    max_generator_temp_trip_c: float = 98.0  # Thermal trip
    max_nacelle_temp_trip_c: float = 65.0  # Nacelle ambient trip
    
    max_wind_speed_trip_ms: float = 25.0  # Storm / extreme wind cut-out
    max_vibration_warning_mm_s: float = 3.5  # High vibration warning
    max_vibration_trip_mm_s: float = 5.5  # Critical structural vibration trip
    
    sensor_timeout_seconds: float = 1.0  # Maximum latency before communication fault trip
    fault_recovery_hold_seconds: float = 5.0  # Wait time before acknowledging auto-reset


@dataclass(frozen=True)
class ControllerConfig:
    """PID Gains and setpoint control configuration."""
    # Region 2 (Torque / Speed MPPT control)
    optimal_tip_speed_ratio: float = 8.1
    optimal_cp: float = 0.46
    torque_gain_k: float = 0.0233  # Optimal torque coefficient = 0.5 * rho * pi * R^5 * Cp_opt / TSR^3 / (gearbox^3)
    
    # Region 3 (Pitch PID controller gains for constant speed/power)
    pitch_kp: float = 1.65
    pitch_ki: float = 0.42
    pitch_kd: float = 0.08
    pitch_integral_min: float = 0.0
    pitch_integral_max: float = 90.0
    
    # Power Derating factor for WARNING state
    derated_power_ratio: float = 0.65  # 65% power during derated operations


@dataclass
class SimulationConfig:
    """Runtime simulation configuration."""
    dt: float = 0.05  # Simulation time step in seconds (20 Hz)
    total_duration_s: float = 60.0  # Default simulation duration
    seed: int | None = 42
    turbine_params: TurbineParameters = field(default_factory=TurbineParameters)
    safety_thresholds: SafetyThresholds = field(default_factory=SafetyThresholds)
    controller_config: ControllerConfig = field(default_factory=ControllerConfig)
    db_path: str = "data/turbineguard.db"
    reports_dir: str = "reports"
    artifacts_dir: str = "reports/figures"
