"""Engineering requirements specification catalog for TurbineGuard verification."""


from turbineguard.models import ValidationRequirement

ENGINEERING_REQUIREMENTS: dict[str, ValidationRequirement] = {
    "REQ-001": ValidationRequirement(
        req_id="REQ-001",
        title="Rotor Speed Regulation in Region 2",
        description="The controller shall track optimal tip-speed ratio and maintain generator speed within operating boundaries below rated wind.",
        input_conditions="Wind speed 8.0 m/s (Region 2 MPPT operating regime).",
        expected_behavior="Generator speed stays bounded below 1500 RPM while producing aerodynamic torque.",
        acceptance_criteria="Generator RPM between 700 and 1450 RPM in steady state.",
        tolerance=50.0,
        target_field="generator_speed_rpm"
    ),
    "REQ-002": ValidationRequirement(
        req_id="REQ-002",
        title="Rated Power Regulation in Region 3",
        description="The controller pitch regulator shall prevent electrical power from exceeding rated capacity by more than 5% in above-rated wind.",
        input_conditions="Wind speed 14.0 m/s (Above rated wind speed).",
        expected_behavior="Pitch increases dynamically to shed aerodynamic lift and regulate power around 2500 kW.",
        acceptance_criteria="Mean electrical power <= 2625 kW (2500 kW + 5% allowance).",
        tolerance=125.0,
        target_field="electrical_power_kw"
    ),
    "REQ-003": ValidationRequirement(
        req_id="REQ-003",
        title="Critical Rotor Overspeed Hard Trip",
        description="The safety system shall trigger EMERGENCY_STOP when generator speed reaches or exceeds 1725 RPM.",
        input_conditions="Injected rapid aerodynamic acceleration / overspeed scenario.",
        expected_behavior="Immediate transition to EMERGENCY_STOP, latching mechanical brakes and max feathering rate.",
        acceptance_criteria="Controller enters EMERGENCY_STOP within 250 ms.",
        tolerance=50.0,
        target_field="response_time_ms"
    ),
    "REQ-004": ValidationRequirement(
        req_id="REQ-004",
        title="High Wind Cut-Out Storm Shutdown",
        description="The controller shall transition to SHUTDOWN and feather blades when wind speed exceeds 25.0 m/s.",
        input_conditions="Wind speed ramp exceeding 25.0 m/s.",
        expected_behavior="Blades pitch to 90 degrees and generator torque drops to zero to protect structure.",
        acceptance_criteria="Turbine enters SHUTDOWN state with pitch angle >= 85 deg within 8.0 seconds.",
        tolerance=5.0,
        target_field="pitch_angle_deg"
    ),
    "REQ-005": ValidationRequirement(
        req_id="REQ-005",
        title="Generator Thermal Overheat Protective Trip",
        description="The safety supervisor shall trigger protective SHUTDOWN when generator temperature reaches 98 C.",
        input_conditions="Injected thermal spike / loss of cooling fan (Tg >= 98 C).",
        expected_behavior="Controller transitions to SHUTDOWN state preventing thermal breakdown.",
        acceptance_criteria="Controller enters SHUTDOWN within 1.0 s of temperature trip.",
        tolerance=1.0,
        target_field="response_time_s"
    ),
    "REQ-006": ValidationRequirement(
        req_id="REQ-006",
        title="Thermal High-Warning Power Derating",
        description="The controller shall derate electrical power output to 65% when generator temperature exceeds 85 C warning limit.",
        input_conditions="Generator temperature 86 C <= Tg < 98 C.",
        expected_behavior="Turbine enters DERATED state and caps power output to 1625 kW (65% of 2500 kW).",
        acceptance_criteria="Demanded power <= 1650 kW while warning is active.",
        tolerance=50.0,
        target_field="demanded_power_kw"
    ),
    "REQ-007": ValidationRequirement(
        req_id="REQ-007",
        title="Structural Vibration Trip",
        description="The safety supervisor shall trigger FAULT trip when nacelle vibration exceeds 5.5 mm/s.",
        input_conditions="Injected mechanical vibration spike > 5.5 mm/s.",
        expected_behavior="Controller detects excessive vibration and enters FAULT state.",
        acceptance_criteria="Controller transitions to FAULT state within 300 ms.",
        tolerance=0.3,
        target_field="response_time_s"
    ),
    "REQ-008": ValidationRequirement(
        req_id="REQ-008",
        title="Sensor Data Integrity and Failsafe",
        description="The controller shall reject corrupt, negative, or NaN sensor data and transition to a safe state.",
        input_conditions="Injected sensor NaN / corrupt data packet.",
        expected_behavior="Safety system flags sensor fault and enters safe FAULT mode.",
        acceptance_criteria="Turbine enters FAULT state without numeric crash.",
        tolerance=0.0,
        target_field="status_code"
    ),
    "REQ-009": ValidationRequirement(
        req_id="REQ-009",
        title="Communication Bus Loss Protection",
        description="The controller shall detect loss of sensor bus communication within 500 ms and enter FAULT mode.",
        input_conditions="Injected bus communication dropout.",
        expected_behavior="Heartbeat loss detected, turbine transitions to FAULT state.",
        acceptance_criteria="Transition to FAULT within <= 500 ms.",
        tolerance=50.0,
        target_field="response_time_ms"
    ),
    "REQ-010": ValidationRequirement(
        req_id="REQ-010",
        title="Pitch Actuator Normal Rate Limiting",
        description="The pitch actuator shall limit blade slew rate to <= 8.0 deg/s during normal operational pitch regulation.",
        input_conditions="Step wind change from 10 m/s to 15 m/s.",
        expected_behavior="Pitch rate magnitude does not exceed 8.0 deg/s.",
        acceptance_criteria="Maximum observed absolute pitch rate <= 8.0 deg/s.",
        tolerance=0.1,
        target_field="pitch_rate_deg_s"
    ),
    "REQ-011": ValidationRequirement(
        req_id="REQ-011",
        title="Automatic Fault Recovery Hysteresis",
        description="The turbine shall hold in safe state for at least 5.0 seconds before initiating automatic restart once wind returns below restart threshold (22 m/s).",
        input_conditions="Post high-wind storm abatement scenario.",
        expected_behavior="Turbine waits for 5.0s stability hold before transitioning from SHUTDOWN to RESTARTING.",
        acceptance_criteria="Recovery delay >= 5.0 seconds.",
        tolerance=0.5,
        target_field="recovery_delay_s"
    ),
    "REQ-012": ValidationRequirement(
        req_id="REQ-012",
        title="Extreme Operating Gust (EOG) Dynamic Stability",
        description="The controller shall absorb an IEC extreme operating gust without exceeding the hard overspeed trip threshold (1725 RPM).",
        input_conditions="10.5-second IEC Extreme Operating Gust with +7 m/s peak amplitude.",
        expected_behavior="Pitch controller reacts dynamically, keeping generator RPM < 1725 RPM.",
        acceptance_criteria="Peak generator RPM < 1725 RPM during gust transient.",
        tolerance=20.0,
        target_field="max_generator_rpm"
    ),
}


def get_all_requirements() -> list[ValidationRequirement]:
    """Returns the list of all defined validation requirements."""
    return list(ENGINEERING_REQUIREMENTS.values())


def get_requirement_by_id(req_id: str) -> ValidationRequirement | None:
    """Retrieves requirement by ID."""
    return ENGINEERING_REQUIREMENTS.get(req_id)
