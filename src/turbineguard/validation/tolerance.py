"""Tolerance and engineering metrics verification helpers."""

from turbineguard.models import ValidationStatus


def check_max_limit(
    measured: float,
    limit: float,
    tolerance: float = 0.0
) -> tuple[ValidationStatus, str]:
    """Verifies that measured value does not exceed maximum limit (plus tolerance)."""
    allowed_max = limit + tolerance
    if measured <= allowed_max:
        return ValidationStatus.PASSED, f"Measured {measured:.3f} <= Limit {limit:.3f} (Tolerance: +{tolerance:.3f})"
    return ValidationStatus.FAILED, f"Measured {measured:.3f} EXCEEDED Limit {limit:.3f} (Allowed: {allowed_max:.3f})"


def check_min_limit(
    measured: float,
    limit: float,
    tolerance: float = 0.0
) -> tuple[ValidationStatus, str]:
    """Verifies that measured value does not fall below minimum limit (minus tolerance)."""
    allowed_min = limit - tolerance
    if measured >= allowed_min:
        return ValidationStatus.PASSED, f"Measured {measured:.3f} >= Limit {limit:.3f} (Tolerance: -{tolerance:.3f})"
    return ValidationStatus.FAILED, f"Measured {measured:.3f} FELL BELOW Limit {limit:.3f} (Allowed: {allowed_min:.3f})"


def check_boundary_tolerance(
    measured: float,
    target: float,
    tolerance: float
) -> tuple[ValidationStatus, str]:
    """Verifies that measured value is within [target - tolerance, target + tolerance]."""
    diff = abs(measured - target)
    if diff <= tolerance:
        return ValidationStatus.PASSED, f"Measured {measured:.3f} within target {target:.3f} +/- {tolerance:.3f} (Diff: {diff:.3f})"
    return ValidationStatus.FAILED, f"Measured {measured:.3f} OUTSIDE target {target:.3f} +/- {tolerance:.3f} (Diff: {diff:.3f})"


def check_relative_tolerance(
    measured: float,
    target: float,
    percent_tolerance: float
) -> tuple[ValidationStatus, str]:
    """Verifies that relative error is within percentage tolerance."""
    if abs(target) < 1e-6:
        return check_boundary_tolerance(measured, target, tolerance=0.05)
    rel_error = abs(measured - target) / abs(target) * 100.0
    if rel_error <= percent_tolerance:
        return ValidationStatus.PASSED, f"Rel Error {rel_error:.2f}% <= Allowed {percent_tolerance:.2f}%"
    return ValidationStatus.FAILED, f"Rel Error {rel_error:.2f}% EXCEEDED Allowed {percent_tolerance:.2f}%"


def calculate_overshoot_pct(
    values: list[float],
    setpoint: float
) -> float:
    """Computes maximum percentage overshoot beyond setpoint."""
    if not values or abs(setpoint) < 1e-6:
        return 0.0
    max_val = max(values)
    if max_val <= setpoint:
        return 0.0
    return float((max_val - setpoint) / setpoint * 100.0)


def calculate_settling_time(
    time_series: list[float],
    values: list[float],
    setpoint: float,
    tolerance_pct: float = 5.0
) -> float | None:
    """Calculates time at which response stays within +-tolerance_pct of setpoint."""
    if len(time_series) != len(values) or not values:
        return None
    
    band = abs(setpoint) * (tolerance_pct / 100.0)
    lower = setpoint - band
    upper = setpoint + band
    
    last_outside_idx = -1
    for i, v in enumerate(values):
        if v < lower or v > upper:
            last_outside_idx = i
            
    if last_outside_idx == -1:
        return 0.0
    if last_outside_idx == len(values) - 1:
        return None  # Never settled
        
    return float(time_series[last_outside_idx + 1])
