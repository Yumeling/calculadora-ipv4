"use strict";

const tabButtons = document.querySelectorAll(".mode-tab");
const cidrForm = document.getElementById("form-cidr");
const maskForm = document.getElementById("form-mask");
const errorBox = document.getElementById("error-message");
const resultsPanel = document.getElementById("results-panel");
const emptyState = document.getElementById("empty-state");
const resultsContent = document.getElementById("results-content");
const resultStatus = document.getElementById("result-status");

function setText(id, value) {
  document.getElementById(id).textContent = value === null || value === undefined || value === "" ? "No aplica" : String(value);
}

function formatNumber(value) {
  if (value === null || value === undefined) return "No aplica";
  return new Intl.NumberFormat("es-CO").format(value);
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
  resultStatus.innerHTML = '<span class="status-dot"></span> REVISAR ENTRADA';
}

function clearError() {
  errorBox.textContent = "";
  errorBox.classList.add("hidden");
}

function renderNotes(notes) {
  const notesBox = document.getElementById("notes-box");
  const notesList = document.getElementById("notes-list");
  notesList.replaceChildren();
  if (!notes || notes.length === 0) {
    notesBox.classList.add("hidden");
    return;
  }
  for (const note of notes) {
    const item = document.createElement("li");
    item.textContent = note;
    notesList.appendChild(item);
  }
  notesBox.classList.remove("hidden");
}

function renderResults(data) {
  setText("result-address", data.address);
  setText("result-prefix", `/${data.prefix_length}`);
  setText("result-class", data.traditional_class);
  setText("result-category", data.classification.category);
  setText("result-detail", data.classification.detail);
  setText("result-network", data.network_address);
  setText("result-broadcast", data.directed_broadcast);
  setText("result-mask", data.subnet_mask);
  setText("result-wildcard", data.wildcard_mask);
  setText("result-total", formatNumber(data.total_addresses));
  setText("result-usable", formatNumber(data.usable_hosts));
  setText("result-first", data.first_usable_host);
  setText("result-last", data.last_usable_host);
  renderNotes(data.notes);
  emptyState.classList.add("hidden");
  resultsContent.classList.remove("hidden");
  resultStatus.innerHTML = '<span class="status-dot"></span> CÁLCULO COMPLETADO';
}

async function calculate(payload) {
  clearError();
  resultsPanel.setAttribute("aria-busy", "true");
  resultStatus.textContent = "CALCULANDO…";

  try {
    const response = await fetch("/api/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok || !body.success) {
      showError(body.error || "No fue posible realizar el cálculo.");
      return;
    }
    renderResults(body.results);
  } catch (error) {
    showError("No se pudo conectar con el servidor. Verifica que la aplicación esté ejecutándose e intenta de nuevo.");
  } finally {
    resultsPanel.setAttribute("aria-busy", "false");
  }
}

for (const button of tabButtons) {
  button.addEventListener("click", () => {
    const mode = button.dataset.mode;
    for (const tab of tabButtons) {
      const selected = tab === button;
      tab.classList.toggle("active", selected);
      tab.setAttribute("aria-selected", selected ? "true" : "false");
    }
    cidrForm.classList.toggle("hidden", mode !== "cidr");
    maskForm.classList.toggle("hidden", mode !== "mask");
    clearError();
  });
}

cidrForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const cidr = document.getElementById("cidr-input").value.trim();
  calculate({ cidr });
});

maskForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const ip = document.getElementById("ip-input").value.trim();
  const mask = document.getElementById("mask-input").value.trim();
  calculate({ ip, mask });
});

// Resultado inicial de ejemplo: permite ver la aplicación lista al abrirla.
calculate({ cidr: document.getElementById("cidr-input").value.trim() });
