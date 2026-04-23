(function () {
  // Selectors
  const form = document.getElementById("registerForm");
  const msg = document.getElementById("registerMsg");
  const registerBtn = document.getElementById("registerBtn");

  const metricFields = document.getElementById("metricFields");
  const usFields = document.getElementById("usFields");

  const heightCm = document.getElementById("height_cm");
  const weightKg = document.getElementById("weight_kg");
  const heightFt = document.getElementById("height_ft");
  const heightIn = document.getElementById("height_in");
  const weightLb = document.getElementById("weight_lb");

  let currentUnit = document.querySelector('input[name="preferred_unit"]:checked')?.value || "metric";

  // --- Math Helpers ---
  const cmToUs = (cm) => {
    const totalInches = cm / 2.54;
    let ft = Math.floor(totalInches / 12);
    let inch = Math.round(totalInches - ft * 12);
    if (inch === 12) { ft += 1; inch = 0; }
    return { ft, inch };
  };

  const usToCm = (ft, inch) => ((ft * 12) + inch) * 2.54;
  const kgToLb = (kg) => kg * 2.20462;
  const lbToKg = (lb) => lb / 2.20462;

  // --- UI Logic ---
  function setUnit(unit, force = false) {
    if (!force && unit === currentUnit) return;

    if (unit === "us") {
      const cm = parseFloat(heightCm?.value);
      const kg = parseFloat(weightKg?.value);

      if (!isNaN(cm)) {
        const converted = cmToUs(cm);
        if (heightFt) heightFt.value = converted.ft;
        if (heightIn) heightIn.value = converted.inch;
      }
      if (!isNaN(kg) && weightLb) weightLb.value = kgToLb(kg).toFixed(1);

      metricFields.hidden = true;
      usFields.hidden = false;
    } else {
      const ft = parseFloat(heightFt?.value);
      const inch = parseFloat(heightIn?.value || 0);
      const lb = parseFloat(weightLb?.value);

      if (!isNaN(ft)) heightCm.value = usToCm(ft, isNaN(inch) ? 0 : inch).toFixed(1);
      if (!isNaN(lb)) weightKg.value = lbToKg(lb).toFixed(1);

      metricFields.hidden = false;
      usFields.hidden = true;
    }
    currentUnit = unit;
  }

  // --- Utility ---
  const getCheckedValue = (name) => document.querySelector(`input[name="${name}"]:checked`)?.value || null;
  const toNumberOrNull = (value) => {
    if (value === "" || value == null) return null;
    const num = Number(value);
    return isNaN(num) ? null : num;
  };

  // --- Listeners ---
  document.querySelectorAll('input[name="preferred_unit"]').forEach((radio) => {
    radio.addEventListener("change", () => setUnit(radio.value));
  });

  // Run initial state
  setUnit(currentUnit, true);

  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const preferredUnit = getCheckedValue("preferred_unit");
    const sex = getCheckedValue("sex");
    const smokingStatus = getCheckedValue("smoking_status");

    const payload = {
      username: document.getElementById("username")?.value.trim(),
      password: document.getElementById("password")?.value,
      full_name: document.getElementById("full_name")?.value.trim(),
      sex,
      smoking_status: smokingStatus,
      age: toNumberOrNull(document.getElementById("age")?.value),
      preferred_unit: preferredUnit,
      height_cm: toNumberOrNull(heightCm?.value),
      weight_kg: toNumberOrNull(weightKg?.value),
      height_ft: toNumberOrNull(heightFt?.value),
      height_in: toNumberOrNull(heightIn?.value),
      weight_lb: toNumberOrNull(weightLb?.value),
      notes: document.getElementById("notes")?.value.trim() || null
    };

    // Validation
    if (!payload.username || !payload.password || !payload.full_name || !payload.sex || !payload.smoking_status) {
      msg.textContent = "Please complete all required fields.";
      msg.style.color = "var(--danger, #b42318)";
      return;
    }

    // Contextual unit validation
    if (payload.preferred_unit === "metric" && (payload.height_cm == null || payload.weight_kg == null)) {
      msg.textContent = "Metric selection requires height (cm) and weight (kg).";
      msg.style.color = "var(--danger, #b42318)";
      return;
    }

    if (payload.preferred_unit === "us" && (payload.height_ft == null || payload.weight_lb == null)) {
      msg.textContent = "US selection requires height (ft) and weight (lb).";
      msg.style.color = "var(--danger, #b42318)";
      return;
    }

    // Submit Action
    registerBtn.disabled = true;
    registerBtn.textContent = "Creating profile...";
    msg.textContent = "";

    try {
      const response = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) throw new Error(data.detail || "Registration failed");

      msg.style.color = "var(--ok, #166534)";
      msg.textContent = `Success! ${data.bmi ? `BMI: ${data.bmi} (${data.bmi_category}).` : ""} Redirecting...`;

      setTimeout(() => {
        window.location.href = "/login";
      }, 1500);

    } catch (error) {
      msg.textContent = error.message;
      msg.style.color = "var(--danger, #b42318)";
      registerBtn.disabled = false;
      registerBtn.textContent = "Create account";
    }
  });
})();