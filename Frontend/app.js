 (() => {
  // Simply use the current origin since the frontend and backend are hosted together!
  const API_BASE = window.location.origin;
  // ... rest of your code stays exactly the same
  const fileInput = document.getElementById("vcf-file-input");
  const browseBtn = document.getElementById("browse-btn");
  const dropArea = document.getElementById("drop-area");
  const selectedFileEl = document.getElementById("selected-file");
  const validateStatusEl = document.getElementById("validate-status");
  const errorContainer = document.getElementById("error-container");
  const errorMessage = document.getElementById("error-message");
  const tryAgainBtn = document.getElementById("try-again-btn");
  const runBtn = document.getElementById("run-analysis-btn");
  const resultsCard = document.getElementById("analysis-results-card");
  const resultsContainer = document.getElementById("analysis-results");
  const resultsSummary = document.getElementById("analysis-summary");
  const downloadJsonBtn = document.getElementById("download-json-btn");
  const copyJsonBtn = document.getElementById("copy-json-btn");

  let selectedFile = null;
  let isValidFile = false;
  let currentAnalysisData = null; // Stores the fetched JSON

  function getSelectedDrugs() {
    return Array.from(
      document.querySelectorAll('input[type="checkbox"][id^="drug-"]:checked')
    ).map((el) => el.value);
  }

  function setRunState(loading) {
    runBtn.disabled = loading || !selectedFile || !isValidFile;
    runBtn.classList.toggle("opacity-60", runBtn.disabled);
    runBtn.classList.toggle("cursor-not-allowed", runBtn.disabled);

    if (loading) {
      runBtn.innerHTML =
        '<span class="material-symbols-outlined">hourglass_top</span>Running...';
      return;
    }

    runBtn.innerHTML =
      '<span class="material-symbols-outlined">analytics</span>Run Analysis';
  }

  function setStatus(message, tone = "neutral") {
    validateStatusEl.textContent = message;
    validateStatusEl.classList.remove(
      "text-slate-500",
      "text-green-600",
      "text-red-600"
    );

    if (tone === "success") {
      validateStatusEl.classList.add("text-green-600");
      return;
    }
    if (tone === "error") {
      validateStatusEl.classList.add("text-red-600");
      return;
    }
    validateStatusEl.classList.add("text-slate-500");
  }

  function showError(message) {
    errorContainer.classList.remove("hidden");
    dropArea.classList.add("hidden");
    errorMessage.textContent = message;
    setStatus("");
  }

  function clearError() {
    errorContainer.classList.add("hidden");
    dropArea.classList.remove("hidden");
    errorMessage.textContent = "";
  }

  // Everything rendered via innerHTML comes from a user-supplied VCF, form field or LLM.
  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[ch]));
  }

  function severityPillClass(severity) {
    switch ((severity || "").toLowerCase()) {
      case "unknown":
        return "bg-slate-200 text-slate-700";
      case "critical":
        return "bg-red-100 text-red-700";
      case "high":
        return "bg-orange-100 text-orange-700";
      case "moderate":
        return "bg-amber-100 text-amber-700";
      default:
        return "bg-emerald-100 text-emerald-700";
    }
  }

  function normalizeResults(payload) {
    return Array.isArray(payload) ? payload : [payload];
  }

  // Unified function for styling cards based strictly on severity
  function getSeverityCardClasses(severity) {
    const normalizedSeverity = (severity || "").toLowerCase();

    if (normalizedSeverity === "critical") {
      return {
        card: "border-red-200 bg-gradient-to-br from-red-50 to-rose-50 dark:border-red-700 dark:from-slate-800 dark:to-slate-800",
        title: "text-red-800 dark:text-red-300",
      };
    }

    if (normalizedSeverity === "high") {
      return {
        card: "border-orange-200 bg-gradient-to-br from-orange-50 to-amber-50 dark:border-orange-700 dark:from-slate-800 dark:to-slate-800",
        title: "text-orange-800 dark:text-orange-300",
      };
    }

    if (normalizedSeverity === "moderate") {
      return {
        card: "border-amber-200 bg-gradient-to-br from-amber-50 to-yellow-50 dark:border-amber-700 dark:from-slate-800 dark:to-slate-800",
        title: "text-amber-800 dark:text-amber-300",
      };
    }

    if (normalizedSeverity === "unknown") {
      return {
        card: "border-slate-300 bg-gradient-to-br from-slate-50 to-slate-100 dark:border-slate-600 dark:from-slate-800 dark:to-slate-800",
        title: "text-slate-700 dark:text-slate-300",
      };
    }

    // Default (Normal / Standard Risk)
    return {
      card: "border-emerald-200 bg-gradient-to-br from-emerald-50 to-lime-50 dark:border-emerald-700 dark:from-slate-800 dark:to-slate-800",
      title: "text-emerald-800 dark:text-emerald-300",
    };
  }

  async function validateFile(file) {
    setStatus("Validating VCF...");
    isValidFile = false;
    setRunState(false);
    clearError();

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/validate-vcf`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        throw new Error(errorPayload.detail || "VCF validation failed.");
      }

      const data = await response.json();
      isValidFile = Boolean(data.valid);
      const warningNote = (data.warnings || []).length
        ? ` (${data.warnings.length} warning${data.warnings.length > 1 ? "s" : ""}: ${data.warnings.join(" ")})`
        : "";
      setStatus(`Valid VCF detected. Variants found: ${data.variant_count ?? 0}${warningNote}`);
      setRunState(false);
    } catch (err) {
      isValidFile = false;
      setRunState(false);
      showError(err.message || "File could not be validated.");
    }
  }

  async function onFileSelected(file) {
    if (!file) return;
    selectedFile = file;
    selectedFileEl.textContent = `${file.name} (${Math.ceil(
      file.size / 1024
    )} KB)`;
    await validateFile(file);
  }

  function renderResults(data) {
    const results = normalizeResults(data);
    resultsCard.classList.remove("hidden");
    resultsSummary.textContent = `Completed analysis for ${
      results.length
    } medication${results.length > 1 ? "s" : ""}.`;

    const cards = results.map((item) => {
      const risk = item.risk_assessment || {};
      const profile = item.pharmacogenomic_profile || {};
      const recommendation = item.clinical_recommendation || {};
      const llm = item.llm_generated_explanation || {};
      
      const cardTheme = getSeverityCardClasses(risk.severity);
      
      const variants = (profile.detected_variants || [])
        .map((v) => v.rsid)
        .filter(Boolean);

      const warnings = (item.warnings || [])
        .map((w) => `<li>${esc(w)}</li>`)
        .join("");
      const confidence =
        typeof risk.confidence_score === "number"
          ? `${Math.round(risk.confidence_score * 100)}%`
          : "N/A";

      return `
        <article class="rounded-xl border p-4 ${cardTheme.card}">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <h4 class="text-base font-bold ${cardTheme.title}">${esc(
              item.drug || "Unknown Drug"
            )}</h4>
            <span class="inline-flex rounded-full px-3 py-1 text-xs font-semibold ${severityPillClass(
              risk.severity
            )}">${esc(risk.risk_label || "Unknown")} | ${esc(
        risk.severity || "unknown"
      )}</span>
          </div>
          <div class="mt-3 grid gap-2 text-sm text-slate-600 dark:text-slate-300">
            <p><strong>Gene:</strong> ${esc(profile.primary_gene || "N/A")}</p>
            <p><strong>Phenotype:</strong> ${esc(profile.phenotype || "N/A")}</p>
            <p><strong>Diplotype:</strong> ${esc(profile.diplotype || "N/A")}</p>
            <p><strong>Detected Variants:</strong> ${
              variants.length ? esc(variants.join(", ")) : "None"
            }</p>
            <p><strong>Confidence:</strong> ${esc(confidence)}</p>
            <p><strong>Recommendation:</strong> ${esc(
              recommendation.recommendation_summary || "N/A"
            )}</p>
            <p><strong>Explanation:</strong> ${esc(llm.summary || "N/A")}</p>
            ${
              warnings
                ? `<ul class="list-disc pl-5 text-xs text-amber-700 dark:text-amber-300">${warnings}</ul>`
                : ""
            }
            <p class="text-xs italic text-slate-500">${esc(item.disclaimer || "")}</p>
          </div>
        </article>
      `;
    });

    resultsContainer.innerHTML = cards.join("");
  }

  async function runAnalysis() {
    const drugs = getSelectedDrugs();
    if (!selectedFile) {
      setStatus("Please upload a VCF file first.", "error");
      return;
    }
    if (!isValidFile) {
      setStatus("Please upload a valid VCF file.", "error");
      return;
    }
    if (drugs.length === 0) {
      setStatus("Select at least one medication.", "error");
      return;
    }

    setRunState(true);
    setStatus("Running full analysis...", "success");
    
    // Hide UI elements from a previous run
    downloadJsonBtn.classList.add("hidden");
    copyJsonBtn.classList.add("hidden");
    resultsCard.classList.add("hidden");

    const formData = new FormData();
    formData.append("file", selectedFile);
    drugs.forEach((drug) => formData.append("drugs", drug));

    try {
      const response = await fetch(`${API_BASE}/full-analysis`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        throw new Error(errorPayload.detail || "Analysis failed.");
      }
      const data = await response.json();
      
      // Store data and reveal buttons upon success
      currentAnalysisData = data;
      downloadJsonBtn.classList.remove("hidden");
      copyJsonBtn.classList.remove("hidden");
      
      renderResults(data);
      setStatus("Analysis completed.", "success");
    } catch (err) {
      setStatus(err.message || "Analysis failed.", "error");
    } finally {
      setRunState(false);
    }
  }

  browseBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async (event) => {
    await onFileSelected(event.target.files?.[0]);
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropArea.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropArea.classList.add("border-primary", "bg-primary/5");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropArea.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropArea.classList.remove("border-primary", "bg-primary/5");
    });
  });

  dropArea.addEventListener("drop", async (event) => {
    const [file] = event.dataTransfer?.files || [];
    await onFileSelected(file);
  });

  tryAgainBtn.addEventListener("click", () => {
    selectedFile = null;
    isValidFile = false;
    currentAnalysisData = null;
    fileInput.value = "";
    selectedFileEl.textContent = "";
    setStatus("");
    clearError();
    setRunState(false);
    
    // Hide buttons and results
    downloadJsonBtn.classList.add("hidden");
    copyJsonBtn.classList.add("hidden");
    resultsCard.classList.add("hidden");
  });

  runBtn.addEventListener("click", runAnalysis);
  document
    .querySelectorAll('input[type="checkbox"][id^="drug-"]')
    .forEach((checkbox) => {
      checkbox.addEventListener("change", () => setRunState(false));
    });

  // Handle JSON Download Trigger
  downloadJsonBtn.addEventListener("click", () => {
    if (!currentAnalysisData) return;
    
    const dataStr = JSON.stringify(currentAnalysisData, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement("a");
    a.href = url;
    a.download = `pharmaguard_analysis_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // Handle JSON Copy Trigger
  copyJsonBtn.addEventListener("click", async () => {
    if (!currentAnalysisData) return;
    
    try {
      const dataStr = JSON.stringify(currentAnalysisData, null, 2);
      await navigator.clipboard.writeText(dataStr);
      
      // Temporary UI feedback
      const originalHTML = copyJsonBtn.innerHTML;
      copyJsonBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">check</span>Copied!';
      copyJsonBtn.classList.add("text-emerald-600", "bg-emerald-50", "dark:bg-emerald-900/20");
      
      setTimeout(() => {
        copyJsonBtn.innerHTML = originalHTML;
        copyJsonBtn.classList.remove("text-emerald-600", "bg-emerald-50", "dark:bg-emerald-900/20");
      }, 2000);
      
    } catch (err) {
      console.error("Failed to copy text: ", err);
      setStatus("Failed to copy to clipboard.", "error");
    }
  });

  setRunState(false);
})();