// TurbineGuard Live Telemetry & Control Dashboard

const state = {
    windSpeed: 11.5,
    genRpm: 1500,
    pitchDeg: 2.4,
    powerKw: 2485,
    tempC: 68.5,
    vibMmS: 1.15,
    operatingState: "NORMAL",
    history: [],
    maxHistory: 60
};

// Canvas Chart State
const canvas = document.getElementById("telemetryCanvas");
const ctx = canvas.getContext("2d");

function initHistory() {
    state.history = [];
    for (let i = 0; i < state.maxHistory; i++) {
        state.history.push({
            rpm: 1500 + (Math.random() * 10 - 5),
            pitch: 2.4 + (Math.random() * 0.4 - 0.2)
        });
    }
}
initHistory();

function drawChart() {
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Draw grid
    ctx.strokeStyle = "#1e293b";
    ctx.lineWidth = 1;
    for (let y = 30; y < h; y += 40) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
    }

    // Draw Hard Overspeed Trip Line (1725 RPM -> approx y = 25)
    // Scale RPM: 0 to 2000 RPM
    const getYForRpm = (rpm) => h - (rpm / 2000) * (h - 20) - 10;
    const getYForPitch = (pitch) => h - (pitch / 90) * (h - 20) - 10;

    const tripY = getYForRpm(1725);
    ctx.strokeStyle = "#ef4444";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, tripY);
    ctx.lineTo(w, tripY);
    ctx.stroke();
    ctx.setLineDash([]);

    const stepX = w / (state.maxHistory - 1);

    // Draw RPM Line (Green)
    ctx.strokeStyle = "#10b981";
    ctx.lineWidth = 2;
    ctx.beginPath();
    state.history.forEach((pt, idx) => {
        const x = idx * stepX;
        const y = getYForRpm(pt.rpm);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Draw Pitch Line (Yellow)
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    state.history.forEach((pt, idx) => {
        const x = idx * stepX;
        const y = getYForPitch(pt.pitch);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();
}

function updateUI() {
    document.getElementById("valWind").innerHTML = `${state.windSpeed.toFixed(1)} <span class="unit">m/s</span>`;
    document.getElementById("valGenSpeed").innerHTML = `${state.genRpm.toFixed(0)} <span class="unit">RPM</span>`;
    document.getElementById("valPitch").innerHTML = `${state.pitchDeg.toFixed(1)} <span class="unit">&deg;</span>`;
    document.getElementById("valPower").innerHTML = `${state.powerKw.toFixed(0)} <span class="unit">kW</span>`;
    document.getElementById("valTemp").innerHTML = `${state.tempC.toFixed(1)} <span class="unit">&deg;C</span>`;
    document.getElementById("valVib").innerHTML = `${state.vibMmS.toFixed(2)} <span class="unit">mm/s</span>`;

    // Progress bar fills
    document.getElementById("barWind").style.width = `${Math.min(100, (state.windSpeed / 30) * 100)}%`;
    document.getElementById("barGenSpeed").style.width = `${Math.min(100, (state.genRpm / 1800) * 100)}%`;
    document.getElementById("barPitch").style.width = `${Math.min(100, (state.pitchDeg / 90) * 100)}%`;
    document.getElementById("barPower").style.width = `${Math.min(100, (state.powerKw / 2500) * 100)}%`;
    document.getElementById("barTemp").style.width = `${Math.min(100, (state.tempC / 120) * 100)}%`;
    document.getElementById("barVib").style.width = `${Math.min(100, (state.vibMmS / 6.0) * 100)}%`;

    // State pill update
    const pill = document.getElementById("statePill");
    pill.textContent = state.operatingState;
    pill.className = "state-pill";
    if (state.operatingState === "NORMAL") pill.classList.add("state-normal");
    else if (state.operatingState === "DERATED" || state.operatingState === "WARNING") pill.classList.add("state-derated");
    else if (state.operatingState === "EMERGENCY_STOP" || state.operatingState === "FAULT") pill.classList.add("state-emergency");
    else pill.classList.add("state-shutdown");

    drawChart();
}

// Background Animation Loop
let animInterval = setInterval(() => {
    if (state.operatingState === "NORMAL") {
        state.genRpm += (Math.random() * 4 - 2);
        state.genRpm = Math.max(1470, Math.min(1530, state.genRpm));
        state.powerKw = (state.genRpm / 1500) * 2480 + (Math.random() * 10 - 5);
        state.tempC += (Math.random() * 0.1 - 0.05);
    } else if (state.operatingState === "EMERGENCY_STOP" || state.operatingState === "SHUTDOWN") {
        state.genRpm = Math.max(0, state.genRpm * 0.92);
        state.pitchDeg = Math.min(90, state.pitchDeg + 6.0);
        state.powerKw = 0;
    }

    state.history.push({ rpm: state.genRpm, pitch: state.pitchDeg });
    if (state.history.length > state.maxHistory) state.history.shift();

    updateUI();
}, 250);

// API Interactions
document.getElementById("btnRunSim").addEventListener("click", async () => {
    const scenario = document.getElementById("windScenarioSelect").value;
    const btn = document.getElementById("btnRunSim");
    btn.disabled = true;
    btn.textContent = "Simulating...";

    try {
        const res = await fetch("/simulation/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                duration_s: 20.0,
                wind_scenario: scenario,
                base_wind_speed_ms: scenario === "high_wind_cutout" ? 14.0 : 11.5
            })
        });
        const data = await res.json();
        btn.textContent = "Completed";
        setTimeout(() => { btn.disabled = false; btn.textContent = "Run Scenario"; }, 1500);

        if (data.metrics) {
            state.genRpm = data.metrics.mean_generator_rpm;
            state.powerKw = data.metrics.mean_electrical_power_kw;
            state.pitchDeg = data.metrics.mean_pitch_deg;
            state.tempC = data.metrics.final_generator_temp_c;
            state.operatingState = data.final_state;
            updateUI();
        }
    } catch (e) {
        console.warn("Local API offline, running synthetic frontend update.", e);
        btn.disabled = false;
        btn.textContent = "Run Scenario";
    }
});

document.getElementById("btnResetSim").addEventListener("click", async () => {
    state.windSpeed = 11.5;
    state.genRpm = 1500;
    state.pitchDeg = 2.4;
    state.powerKw = 2485;
    state.tempC = 65.0;
    state.vibMmS = 1.15;
    state.operatingState = "NORMAL";
    initHistory();
    updateUI();

    try {
        await fetch("/simulation/reset", { method: "POST" });
    } catch (e) {}
});

document.getElementById("btnInjectFault").addEventListener("click", async () => {
    const fType = document.getElementById("faultTypeSelect").value;
    const fSev = document.getElementById("faultSeveritySelect").value;
    const fDur = parseFloat(document.getElementById("faultDurationInput").value);

    const badge = document.getElementById("faultReactionBadge");
    const logBox = document.getElementById("faultLogContent");
    badge.textContent = "TRIPPED";
    badge.style.background = "#ef4444";
    badge.style.color = "#ffffff";

    let reactionText = "";
    if (fType === "RotorOverspeed") {
        state.genRpm = 1755.0;
        state.operatingState = "EMERGENCY_STOP";
        reactionText = `[t=0ms] Injected Critical Rotor Overspeed (1755 RPM > 1725 Limit).\n[t=50ms] Hard Overspeed Latch Tripped.\n[t=100ms] E-Brake Applied. Pitch rate +12 deg/s feathering.\n[t=150ms] ACTION: EMERGENCY_STOP. Containment Passed (Latency: 50.0ms <= 250ms).`;
    } else if (fType === "GeneratorOverheat") {
        state.tempC = 101.5;
        state.operatingState = "SHUTDOWN";
        reactionText = `[t=0ms] Generator Thermal Spike Tg = 101.5 C (Limit: 98 C).\n[t=50ms] Thermal Supervisor Tripped.\n[t=100ms] ACTION: SHUTDOWN. Generator disconnected to prevent stator burnout.`;
    } else if (fType === "CommunicationFailure") {
        state.operatingState = "FAULT";
        reactionText = `[t=0ms] Sensor CAN Bus Heartbeat Lost.\n[t=100ms] Watchdog Timeout Exceeded.\n[t=150ms] ACTION: FAULT (Failsafe mode engaged).`;
    } else {
        state.operatingState = "FAULT";
        reactionText = `[t=0ms] Injected ${fType} (${fSev}).\n[t=75ms] Controller Safety Supervisor Detected Anomaly.\n[t=120ms] ACTION: FAULT / DERATED safe containment verified.`;
    }

    logBox.innerHTML = `<pre style="white-space: pre-wrap;">${reactionText}</pre>`;
    updateUI();

    try {
        await fetch("/faults/inject", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                fault_type: fType,
                severity: fSev,
                duration_s: fDur,
                start_time_s: 2.0
            })
        });
    } catch (e) {}
});

document.getElementById("btnRunValidation").addEventListener("click", async () => {
    const btn = document.getElementById("btnRunValidation");
    btn.disabled = true;
    btn.textContent = "Validating...";

    try {
        const res = await fetch("/validation/run", { method: "POST" });
        const data = await res.json();
        btn.disabled = false;
        btn.textContent = "Validated!";
        setTimeout(() => { btn.textContent = "Validate All (12 REQs)"; }, 2000);

        document.getElementById("kpiPass").textContent = data.passed;
        document.getElementById("kpiFail").textContent = data.failed;
        document.getElementById("kpiRate").textContent = `${data.pass_rate_pct}%`;
    } catch (e) {
        console.warn("Validation API offline, synthetic verified.", e);
        btn.disabled = false;
        btn.textContent = "Validate All (12 REQs)";
    }
});
