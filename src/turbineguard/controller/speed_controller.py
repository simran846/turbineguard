"""Generator torque and rotor speed controller across operating aerodynamic regions."""

import math

from turbineguard.config import ControllerConfig, TurbineParameters
from turbineguard.models import ControlRegion


class SpeedTorqueController:
    """Calculates demanded generator electromagnetic torque across all aerodynamic control regions."""

    def __init__(
        self,
        config: ControllerConfig | None = None,
        turbine_params: TurbineParameters | None = None
    ):
        self.config = config or ControllerConfig()
        self.params = turbine_params or TurbineParameters()
        self.rated_torque_nm = (self.params.rated_electrical_power_kw * 1000.0) / (
            self.params.rated_generator_rpm * (2.0 * math.pi / 60.0) * self.params.generator_efficiency
        )

    def determine_region(self, wind_speed_ms: float, gen_rpm: float) -> ControlRegion:
        """Identifies aerodynamic control region from environmental wind and generator speed."""
        if wind_speed_ms < self.params.cut_in_wind_speed_ms:
            return ControlRegion.REGION_1
        elif wind_speed_ms >= self.params.cut_out_wind_speed_ms:
            return ControlRegion.REGION_4
        elif gen_rpm >= self.params.rated_generator_rpm * 0.96 or wind_speed_ms >= self.params.rated_wind_speed_ms:
            return ControlRegion.REGION_3
        elif gen_rpm >= self.params.rated_generator_rpm * 0.85:
            return ControlRegion.REGION_2_5
        else:
            return ControlRegion.REGION_2

    def compute_torque_demand(
        self,
        wind_speed_ms: float,
        measured_gen_rpm: float,
        derated_ratio: float = 1.0,
        is_braking: bool = False
    ) -> tuple[float, ControlRegion]:
        """Calculates electromagnetic generator torque command in Newton-meters (Nm)."""
        if is_braking:
            return 0.0, ControlRegion.REGION_4

        region = self.determine_region(wind_speed_ms, measured_gen_rpm)
        gen_rad_s = max(0.1, measured_gen_rpm * (2.0 * math.pi / 60.0))

        # Effective maximum rated torque factoring derating
        max_power_w = (self.params.rated_electrical_power_kw * 1000.0) * derated_ratio
        rated_rad_s = self.params.rated_generator_rpm * (2.0 * math.pi / 60.0)
        nominal_rated_torque_nm = max_power_w / (rated_rad_s * self.params.generator_efficiency)

        if region == ControlRegion.REGION_1:
            # Below cut-in: zero torque demand to allow rotor to accelerate
            torque_demand = 0.0

        elif region == ControlRegion.REGION_2:
            # Variable-speed MPPT Region: T_gen = k_opt * omega_g^2
            k_opt = self.config.torque_gain_k
            torque_demand = k_opt * (gen_rad_s ** 2)

        elif region == ControlRegion.REGION_2_5:
            # Transition knee region approaching rated speed
            t_mppt = self.config.torque_gain_k * (gen_rad_s ** 2)
            slope = (nominal_rated_torque_nm - t_mppt) / max(1.0, (self.params.rated_generator_rpm * 0.15))
            torque_demand = t_mppt + slope * max(0.0, (measured_gen_rpm - self.params.rated_generator_rpm * 0.85))

        elif region == ControlRegion.REGION_3:
            # Above rated: Constant torque / power with strong counter-torque on speed overshoot
            if measured_gen_rpm >= self.params.rated_generator_rpm:
                # Provide full rated counter-torque + proportional damping to hold speed stable
                speed_excess = (measured_gen_rpm - self.params.rated_generator_rpm) / 100.0
                torque_demand = nominal_rated_torque_nm * (1.0 + 0.15 * speed_excess)
            else:
                torque_demand = max_power_w / (gen_rad_s * self.params.generator_efficiency)

        else:  # REGION_4 Cut-out
            torque_demand = 0.0

        # Safety clamp torque command
        clamped_torque = max(0.0, min(nominal_rated_torque_nm * 1.25, torque_demand))
        return float(clamped_torque), region
