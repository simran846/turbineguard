"""Faults package initialization."""

from turbineguard.faults.fault_injection import FaultInjector, InjectedFaultResult
from turbineguard.faults.fault_types import FAULT_CRITERIA_MAP, FaultEvaluationCriteria

__all__ = ["FAULT_CRITERIA_MAP", "FaultEvaluationCriteria", "FaultInjector", "InjectedFaultResult"]
