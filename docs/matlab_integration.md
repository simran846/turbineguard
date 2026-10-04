# MATLAB & Simulink Integration Architecture for TurbineGuard

## Overview
In industrial wind turbine controller development (such as at Siemens Gamesa), aero-hydro-servo-elastic multi-body dynamics are frequently modeled in **MATLAB/Simulink**, **OpenFAST (NREL)**, or proprietary load simulation tools.

TurbineGuard is designed with modular data interfaces to allow automated co-simulation, hardware-in-the-loop (HIL) testing, and verification data exchange with MATLAB/Simulink pipelines.

---

## 1. Co-Simulation via REST API Bridge
Simulink can interact directly with TurbineGuard during simulation using MATLAB's `webwrite` / `webread` HTTP clients or Simulink TCP/IP S-functions.

### MATLAB Client Code Example:
```matlab
% MATLAB script to interact with TurbineGuard REST API
baseUrl = 'http://localhost:8000';

% 1. Start Simulation Scenario
simRequest = struct(...
    'duration_s', 30.0, ...
    'wind_scenario', 'gust', ...
    'base_wind_speed_ms', 11.5 ...
);
options = weboptions('MediaType', 'application/json', 'Timeout', 10);
response = webwrite([baseUrl '/simulation/start'], simRequest, options);
fprintf('Run ID: %s, Status: %s\n', response.run_id, response.status);

% 2. Retrieve Validation Status
valResults = webread([baseUrl '/validation/results'], options);
fprintf('Pass Rate: %.2f%%\n', valResults.pass_rate_pct);
```

---

## 2. Telemetry Exchange via Tabular CSV / HDF5 Datasets
Simulink aeroelastic models can export high-resolution turbine loads and dynamics into standardized CSV format, which TurbineGuard's `ValidationEngine` ingests to perform automated requirement verification.

### Exporting from Simulink to TurbineGuard CSV:
```matlab
% In Simulink Model Workspace / Post-processing
t = out.tout;
v_wind = out.wind_speed.signals.values;
rpm_gen = out.generator_rpm.signals.values;
pitch = out.pitch_deg.signals.values;
power = out.power_kw.signals.values;

T = table(t, v_wind, rpm_gen, pitch, power, ...
    'VariableNames', {'timestamp', 'wind_speed_ms', 'generator_speed_rpm', 'pitch_angle_deg', 'electrical_power_kw'});
writetable(T, 'simulink_telemetry.csv');
```

Then in Python:
```python
import pandas as pd
from turbineguard.analytics.analyzer import TelemetryAnalyzer

df = pd.read_csv("simulink_telemetry.csv")
metrics = TelemetryAnalyzer.compute_metrics(df)
print(f"Simulink Model Overshoot: {metrics.rpm_overshoot_pct}%")
```

---

## 3. C-MEX S-Function & Python Bridge
For real-time closed loop co-simulation at high sample rates (100Hz - 1kHz):
1. **Python C-API / `pyenv`:** MATLAB natively supports calling Python modules via `py.turbineguard.controller.controller.TurbineController()`.
2. **Shared Memory / Socket IPC:** High-performance inter-process communication using ZeroMQ or UDP sockets connecting Simulink with the Python validation harness.

---

## Technical Disclaimer
TurbineGuard is a Python-based software validation platform and does not require a local MATLAB license for standalone execution. This integration specification outlines the architectural bridge for deployment alongside industrial Simulink simulation suites.
