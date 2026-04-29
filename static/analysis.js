async function loadAnalysisPage() {
  try {
    const res = await fetch("/api/analysis", { cache: "no-store" });
    const data = await res.json();

    console.log("ANALYSIS DATA:", data);

    const result = data?.analysis;

    // ---------------- DOM DEBUG ----------------
    const domCheck = {
      analysisResult: document.getElementById("analysisResult"),
      analysisConfidence: document.getElementById("analysisConfidence"),
      analysisReason: document.getElementById("analysisReason"),
      analysisSamples: document.getElementById("analysisSamples"),
      analysisRaw: document.getElementById("analysisRaw"),
    };

    console.log("DOM CHECK:", domCheck);

    // always show raw JSON (if exists)
    if (domCheck.analysisRaw) {
      domCheck.analysisRaw.textContent = JSON.stringify(data, null, 2);
    }

    if (!result) {
      console.warn("No analysis result found");
      return;
    }

    // ---------------- MAIN RESULT ----------------
    if (domCheck.analysisResult) {
      domCheck.analysisResult.textContent = result.prediction ?? "--";
    }

    if (domCheck.analysisConfidence) {
      domCheck.analysisConfidence.textContent =
        result.confidence != null ? `${result.confidence}%` : "--";
    }

    if (domCheck.analysisReason) {
      domCheck.analysisReason.textContent =
        result.reason ?? "No reason provided";
    }

    if (domCheck.analysisSamples) {
      domCheck.analysisSamples.textContent = data.samples_used ?? "--";
    }

    // ---------------- FEATURES ----------------
    const f = result.features || {};

    const set = (id, value) => {
      const el = document.getElementById(id);
      if (!el) {
        console.warn(`Missing element: ${id}`);
        return;
      }
      el.textContent = value ?? "--";
    };

    set("f_hrv", f.hrv);
    set("f_hrtrend", f.hr_trend);
    set("f_temptrend", f.temp_trend);
    set("f_hrmean", f.hr_rolling_mean);
    set("f_corr", f.bpm_temp_corr);

  } catch (err) {
    console.error("Analysis fetch error:", err);
  }
}

// ---------------- SAFE INIT ----------------
(function initAnalysisPage() {
  function start() {
    if (!window.location.pathname.includes("analysis")) return;

    loadAnalysisPage();

    if (window.__analysisInterval) {
      clearInterval(window.__analysisInterval);
    }

    window.__analysisInterval = setInterval(loadAnalysisPage, 3000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();