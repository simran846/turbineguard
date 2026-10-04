"""Unit tests for wind environment scenarios and wind profiles."""

import pytest

from turbineguard.simulator.environment import WindEnvironment, WindScenarioType


@pytest.mark.unit
def test_constant_wind_speed():
    """Verifies constant wind speed scenario output."""
    env = WindEnvironment(base_wind_speed_ms=11.5, scenario=WindScenarioType.CONSTANT)
    for t in [0.0, 5.0, 15.0, 30.0]:
        assert env.get_wind_speed(t) == 11.5


@pytest.mark.unit
def test_step_wind_speed():
    """Verifies step wind profile transition."""
    env = WindEnvironment(base_wind_speed_ms=8.0, scenario=WindScenarioType.STEP)
    assert env.get_wind_speed(5.0) == 8.0
    assert env.get_wind_speed(15.0) == 13.0


@pytest.mark.unit
def test_iec_extreme_operating_gust():
    """Verifies IEC 61400-1 gust profile rises and returns to baseline."""
    env = WindEnvironment(base_wind_speed_ms=11.5, scenario=WindScenarioType.GUST)
    v_base = env.get_wind_speed(5.0)
    v_peak = env.get_wind_speed(15.0 + 10.5 / 2.0)  # Peak at t0 + T/2
    v_after = env.get_wind_speed(30.0)

    assert v_base == 11.5
    assert v_peak > 18.0
    assert v_after == 11.5


@pytest.mark.unit
def test_high_wind_cutout_profile():
    """Verifies storm cut-out scenario exceeds 25 m/s."""
    env = WindEnvironment(scenario=WindScenarioType.HIGH_WIND_CUTOUT)
    assert env.get_wind_speed(0.0) == 14.0
    assert env.get_wind_speed(30.0) == 28.0


@pytest.mark.unit
def test_turbulent_wind_non_negative():
    """Verifies stochastic turbulent wind profile remains non-negative."""
    env = WindEnvironment(base_wind_speed_ms=8.0, scenario=WindScenarioType.TURBULENT, seed=123)
    for t in range(100):
        v = env.get_wind_speed(t * 0.1)
        assert v >= 0.0
