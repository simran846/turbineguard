"""Unit tests for speed torque controller and aerodynamic region classification."""

import pytest

from turbineguard.controller.speed_controller import SpeedTorqueController
from turbineguard.models import ControlRegion


@pytest.mark.unit
def test_region_1_zero_torque(speed_controller: SpeedTorqueController):
    """Verifies below cut-in wind speed demands zero generator torque."""
    torque, region = speed_controller.compute_torque_demand(wind_speed_ms=2.0, measured_gen_rpm=300.0)
    assert torque == 0.0
    assert region == ControlRegion.REGION_1


@pytest.mark.unit
def test_region_2_mppt_torque_quadratic_scaling(speed_controller: SpeedTorqueController):
    """Verifies Region 2 torque scales quadratically with speed T = k * omega^2."""
    t1, reg1 = speed_controller.compute_torque_demand(wind_speed_ms=6.0, measured_gen_rpm=800.0)
    t2, reg2 = speed_controller.compute_torque_demand(wind_speed_ms=8.0, measured_gen_rpm=1100.0)
    assert reg1 == ControlRegion.REGION_2
    assert reg2 == ControlRegion.REGION_2
    assert t2 > t1


@pytest.mark.unit
def test_region_3_constant_power_torque(speed_controller: SpeedTorqueController):
    """Verifies Region 3 demands constant power torque."""
    t_reg3, region = speed_controller.compute_torque_demand(wind_speed_ms=13.0, measured_gen_rpm=1500.0)
    assert region == ControlRegion.REGION_3
    assert t_reg3 > 10000.0


@pytest.mark.unit
def test_derated_torque_scales_proportionately(speed_controller: SpeedTorqueController):
    """Verifies derated power ratio reduces maximum torque demand."""
    t_full, _ = speed_controller.compute_torque_demand(wind_speed_ms=13.0, measured_gen_rpm=1500.0, derated_ratio=1.0)
    t_derated, _ = speed_controller.compute_torque_demand(wind_speed_ms=13.0, measured_gen_rpm=1500.0, derated_ratio=0.65)
    assert pytest.approx(t_derated, rel=1e-2) == t_full * 0.65


@pytest.mark.unit
def test_braking_demands_zero_generator_torque(speed_controller: SpeedTorqueController):
    """Verifies mechanical braking mode zeros generator torque demand."""
    torque, _ = speed_controller.compute_torque_demand(wind_speed_ms=10.0, measured_gen_rpm=1400.0, is_braking=True)
    assert torque == 0.0
