"""Wind and atmospheric environment simulation models."""

import math
from enum import Enum

import numpy as np


class WindScenarioType(str, Enum):
    CONSTANT = "constant"
    STEP = "step"
    RAMP = "ramp"
    GUST = "gust"  # IEC Extreme Operating Gust (EOG)
    TURBULENT = "turbulent"
    HIGH_WIND_CUTOUT = "high_wind_cutout"
    LOW_WIND_CUTIN = "low_wind_cutin"


class WindEnvironment:
    """Simulates wind inflow conditions and atmospheric variables."""

    def __init__(
        self,
        base_wind_speed_ms: float = 9.0,
        scenario: WindScenarioType = WindScenarioType.CONSTANT,
        air_density_kg_m3: float = 1.225,
        ambient_temp_c: float = 25.0,
        turbulence_intensity: float = 0.12,
        seed: int | None = 42
    ):
        self.base_wind_speed_ms = base_wind_speed_ms
        self.scenario = scenario
        self.air_density = air_density_kg_m3
        self.ambient_temp_c = ambient_temp_c
        self.turbulence_intensity = turbulence_intensity
        self.rng = np.random.RandomState(seed)
        
        # Internal state for turbulent filtering
        self._turb_state = 0.0

    def get_wind_speed(self, t: float) -> float:
        """Calculates instantaneous hub-height wind speed at time t (seconds)."""
        v_base = self.base_wind_speed_ms

        if self.scenario == WindScenarioType.CONSTANT:
            v = v_base

        elif self.scenario == WindScenarioType.STEP:
            # Step from base to rated or high wind at t = 10s
            if t < 10.0:
                v = v_base
            elif t < 25.0:
                v = v_base + 5.0
            else:
                v = v_base + 2.0

        elif self.scenario == WindScenarioType.RAMP:
            # Smooth ramp from cut-in to rated and above
            if t < 5.0:
                v = 4.0
            elif t < 35.0:
                v = 4.0 + (16.0 - 4.0) * ((t - 5.0) / 30.0)
            else:
                v = 16.0

        elif self.scenario == WindScenarioType.GUST:
            # IEC 61400-1 Extreme Operating Gust (EOG)
            # Gust duration T = 10.5 s, peak at t0 = 15 s
            t0 = 15.0
            T_gust = 10.5
            v_gust_peak = 7.0  # +7 m/s gust amplitude
            if t0 <= t <= t0 + T_gust:
                # 1 - cos shape
                v = v_base + (v_gust_peak / 2.0) * (1.0 - math.cos(2.0 * math.pi * (t - t0) / T_gust))
            else:
                v = v_base

        elif self.scenario == WindScenarioType.TURBULENT:
            # First-order auto-regressive Markov turbulence approximation (IEC turbulence spectrum approx)
            sigma = self.turbulence_intensity * v_base
            alpha = 0.98  # Correlation factor for 20Hz
            noise = self.rng.normal(0, sigma * math.sqrt(1 - alpha**2))
            self._turb_state = alpha * self._turb_state + noise
            v = max(0.0, v_base + self._turb_state)

        elif self.scenario == WindScenarioType.HIGH_WIND_CUTOUT:
            # Wind rises above 25 m/s to trigger storm shutdown
            if t < 10.0:
                v = 14.0
            elif t < 25.0:
                v = 14.0 + (28.0 - 14.0) * ((t - 10.0) / 15.0)
            else:
                v = 28.0

        elif self.scenario == WindScenarioType.LOW_WIND_CUTIN:
            # Wind transitions from below 3 m/s to 6 m/s
            if t < 10.0:
                v = 2.0
            elif t < 20.0:
                v = 2.0 + (6.0 - 2.0) * ((t - 10.0) / 10.0)
            else:
                v = 6.0

        else:
            v = v_base

        return max(0.0, float(v))
