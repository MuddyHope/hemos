(function () {
  const loginView = document.getElementById("loginView");
  const dashboardView = document.getElementById("dashboardView");
  const loginError = document.getElementById("loginError");
  const usernameInput = document.getElementById("username");
  const passwordInput = document.getElementById("password");
  const loginBtn = document.getElementById("loginBtn");
  const statusHint = document.getElementById("statusHint");
  const strengthBar = document.getElementById("strengthBar");
  const capsHint = document.getElementById("capsHint");
  const rememberBox = document.getElementById("rememberBox");
  const togglePassword = document.getElementById("togglePassword");

  let vitalsChart = null;
  let dashboardTimer = null;

  function updateFormState() {
    if (!usernameInput || !passwordInput || !loginBtn || !statusHint || !strengthBar) return;

    const u = usernameInput.value.trim();
    const p = passwordInput.value.trim();
    const ready = u.length >= 2 && p.length >= 4;

    loginBtn.disabled = !ready;
    statusHint.textContent = ready
      ? "Looks good. Press Enter or click the button to continue."
      : "Enter a username and password to enable sign-in.";

    const strength = Math.min(
      100,
      p.length * 14 + (/[A-Z]/.test(p) ? 15 : 0) + (/[0-9]/.test(p) ? 15 : 0)
    );

    strengthBar.style.width = `${Math.max(8, strength)}%`;
  }

  async function login() {
    if (!usernameInput || !passwordInput || !loginBtn || !loginError) return;

    loginError.textContent = "";
    loginError.classList.remove("okmsg");
    loginBtn.disabled = true;
    loginBtn.textContent = "Signing in...";

    try {
      const res = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: usernameInput.value.trim(),
          password: passwordInput.value.trim()
        })
      });

      if (!res.ok) {
        loginError.textContent = "Login failed. Try demo / demo123";
        return;
      }

      const data = await res.json();

      if (rememberBox && rememberBox.checked) {
        sessionStorage.setItem("hemosUser", JSON.stringify(data));
      }

      loginError.textContent = "Login successful.";
      loginError.classList.add("okmsg");

      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 350);
    } catch (err) {
      loginError.textContent = "Server error. Check that FastAPI is running.";
    } finally {
      loginBtn.textContent = "Sign in to dashboard";
      updateFormState();
    }
  }

  function fmt(v, suffix = "") {
    return v === null || v === undefined ? "--" : `${Number(v).toFixed(2)}${suffix}`;
  }

  function renderOrUpdateVitalsChart(history) {
    const canvas = document.getElementById("vitalsChart");
    if (!canvas || typeof Chart === "undefined") return;

    const ordered = Array.isArray(history) ? [...history].reverse() : [];

    const labels = ordered.map(row => {
      if (!row.timestamp) return "";
      const d = new Date(row.timestamp);
      return d.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      });
    });

    const heartRates = ordered.map(row => row.heart_rate);
    const temperatures = ordered.map(row => row.body_temperature);

    if (!vitalsChart) {
      vitalsChart = new Chart(canvas, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Heart Rate (BPM)",
              data: heartRates,
              borderColor: "#0f766e",
              backgroundColor: "rgba(15, 118, 110, 0.15)",
              tension: 0.35,
              yAxisID: "y",
              fill: true
            },
            {
              label: "Temperature (°C)",
              data: temperatures,
              borderColor: "#2563eb",
              backgroundColor: "rgba(37, 99, 235, 0.10)",
              tension: 0.35,
              yAxisID: "y1",
              fill: false
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          animation: false,
          interaction: {
            mode: "index",
            intersect: false
          },
          scales: {
            y: {
              type: "linear",
              position: "left",
              title: {
                display: true,
                text: "Heart Rate"
              }
            },
            y1: {
              type: "linear",
              position: "right",
              grid: {
                drawOnChartArea: false
              },
              title: {
                display: true,
                text: "Temperature"
              }
            }
          }
        }
      });
      return;
    }

    vitalsChart.data.labels = labels;
    vitalsChart.data.datasets[0].data = heartRates;
    vitalsChart.data.datasets[1].data = temperatures;
    vitalsChart.update();
  }

  async function loadDashboard() {
    const latestHr = document.getElementById("latestHr");
    if (!latestHr) return;

    try {
      const [latestRes, historyRes, recoveryRes] = await Promise.all([
        fetch("/api/latest"),
        fetch("/api/history?limit=15"),
        fetch("/api/recovery")
      ]);

      if (!latestRes.ok || !historyRes.ok || !recoveryRes.ok) {
        throw new Error("Failed to fetch dashboard data");
      }

      const latest = await latestRes.json();
      const history = await historyRes.json();
      const recovery = await recoveryRes.json();

      if (latest.status !== "no data") {
        document.getElementById("latestHr").textContent = latest.heart_rate ?? "--";
        document.getElementById("latestTemp").textContent =
          latest.body_temperature != null ? Number(latest.body_temperature).toFixed(2) : "--";
        document.getElementById("deviceId").textContent = latest.device_id ?? "--";
        document.getElementById("latestTime").textContent = latest.timestamp ?? "--";
        document.getElementById("latestHrText").textContent = latest.heart_rate ?? "--";
        document.getElementById("latestTempText").textContent =
          latest.body_temperature != null
            ? `${Number(latest.body_temperature).toFixed(2)} C`
            : "--";
      }

      document.getElementById("recoveryScore").textContent = recovery.recovery_score ?? "--";

      const stateEl = document.getElementById("recoveryState");
      stateEl.textContent = recovery.state ?? "--";
      stateEl.className =
        "kpi status " +
        (recovery.recovery_score >= 85 ? "ok" : recovery.recovery_score >= 65 ? "warn" : "bad");

      document.getElementById("recoverySummary").textContent =
        recovery.status === "ok"
          ? `Average heart rate: ${fmt(recovery.avg_heart_rate)} BPM. Average temperature: ${fmt(recovery.avg_temperature, " C")}. Current recovery estimate: ${recovery.state}.`
          : "No recovery data available yet.";

      renderOrUpdateVitalsChart(history);

      const savedUser = sessionStorage.getItem("hemosUser");
      if (savedUser) {
        const data = JSON.parse(savedUser);
        const fullName = document.getElementById("fullName");
        if (fullName) fullName.textContent = data.full_name;
      }
    } catch (err) {
      console.error("Dashboard auto-update failed:", err);
    }
  }

  function startDashboardAutoRefresh() {
    if (dashboardTimer) clearInterval(dashboardTimer);
    loadDashboard();
    dashboardTimer = setInterval(loadDashboard, 3000);
  }

  if (usernameInput) usernameInput.addEventListener("input", updateFormState);

  if (passwordInput) {
    passwordInput.addEventListener("input", updateFormState);
    passwordInput.addEventListener("keydown", (e) => {
      if (capsHint) {
        capsHint.textContent =
          e.getModifierState && e.getModifierState("CapsLock") ? "Caps Lock is on" : "";
      }
      if (e.key === "Enter") login();
    });
  }

  if (usernameInput) {
    usernameInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") login();
    });
  }

  if (togglePassword && passwordInput) {
    togglePassword.addEventListener("click", () => {
      const show = passwordInput.type === "password";
      passwordInput.type = show ? "text" : "password";
      togglePassword.textContent = show ? "Hide" : "Show";
      passwordInput.focus();
    });
  }

  if (loginBtn) loginBtn.addEventListener("click", login);

  const refreshBtn = document.getElementById("refreshBtn");
  if (refreshBtn) {
    refreshBtn.style.display = "none";
  }

  if (loginView) updateFormState();
  if (dashboardView) startDashboardAutoRefresh();
})();


// REGISTER PAGE

(function () {
  const form = document.getElementById("registerForm");
  const msg = document.getElementById("registerMsg");
  const metricFields = document.getElementById("metricFields");
  const usFields = document.getElementById("usFields");

  function currentUnit() {
    const checked = document.querySelector('input[name="preferred_unit"]:checked');
    return checked ? checked.value : "metric";
  }

  function toggleUnits() {
    const unit = currentUnit();
    metricFields.hidden = unit !== "metric";
    usFields.hidden = unit !== "us";
  }

  async function submitForm(e) {
    e.preventDefault();
    msg.textContent = "";

    const sex = document.querySelector('input[name="sex"]:checked')?.value;
    const smoking = document.querySelector('input[name="smoking_status"]:checked')?.value;
    const preferred_unit = currentUnit();

    const payload = {
      full_name: document.getElementById("full_name").value.trim(),
      username: document.getElementById("username").value.trim(),
      password: document.getElementById("password").value.trim(),
      age: Number(document.getElementById("age").value) || null,
      sex,
      smoking_status: smoking,
      preferred_unit,
      height_cm: preferred_unit === "metric" ? Number(document.getElementById("height_cm").value) || null : null,
      weight_kg: preferred_unit === "metric" ? Number(document.getElementById("weight_kg").value) || null : null,
      height_ft: preferred_unit === "us" ? Number(document.getElementById("height_ft").value) || null : null,
      height_in: preferred_unit === "us" ? Number(document.getElementById("height_in").value) || null : null,
      weight_lb: preferred_unit === "us" ? Number(document.getElementById("weight_lb").value) || null : null
    };

    try {
      const res = await fetch("/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok) {
        msg.textContent = data.detail || "Registration failed";
        return;
      }

      msg.textContent = `Registered successfully. BMI: ${data.bmi ?? "--"} (${data.bmi_category ?? "N/A"}). Redirecting to login...`;

      setTimeout(() => {
        window.location.href = "/login";
      }, 1500);
    } catch (err) {
      msg.textContent = "Server error while registering.";
    }
  }

  document.querySelectorAll('input[name="preferred_unit"]').forEach(el => {
    el.addEventListener("change", toggleUnits);
  });

  if (form) form.addEventListener("submit", submitForm);
  toggleUnits();
})();