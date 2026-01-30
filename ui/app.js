const inputBib = document.getElementById("inputBib");
const outputBib = document.getElementById("outputBib");
const keepFields = document.getElementById("keepFields");
const journalAbbrev = document.getElementById("journalAbbrev");
const titlecase = document.getElementById("titlecase");
const regenKeys = document.getElementById("regenKeys");
const autoClean = document.getElementById("autoClean");
const inputCount = document.getElementById("inputCount");
const outputStatus = document.getElementById("outputStatus");

const cleanBtn = document.getElementById("cleanBtn");
const copyBtn = document.getElementById("copyBtn");
const downloadBtn = document.getElementById("downloadBtn");
const loadExampleBtn = document.getElementById("loadExampleBtn");
const clearBtn = document.getElementById("clearBtn");
const optionsToggle = document.getElementById("optionsToggle");
const optionsBody = document.getElementById("optionsBody");

const fieldOptions = [
  "author",
  "title",
  "shorttitle",
  "journal",
  "booktitle",
  "year",
  "month",
  "day",
  "volume",
  "number",
  "pages",
  "doi",
  "isbn",
  "issn",
  "url",
  "urldate",
  "publisher",
  "address",
  "series",
  "location",
  "note",
  "copyright",
  "category",
  "metadata",
];

const defaultKeep = ["author", "title", "journal", "year", "volume", "number", "pages", "doi"];

function renderKeepFields() {
  keepFields.innerHTML = "";
  fieldOptions.forEach((field) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = field;
    input.checked = defaultKeep.includes(field);
    input.addEventListener("change", scheduleClean);

    const text = document.createElement("span");
    text.textContent = field;

    label.appendChild(input);
    label.appendChild(text);
    keepFields.appendChild(label);
  });
}

renderKeepFields();

let debounceTimer = null;

function setStatus(message, isError = false) {
  outputStatus.textContent = message;
  outputStatus.style.color = isError ? "#b23b2a" : "";
}

function parseKeepFields() {
  const selected = Array.from(
    keepFields.querySelectorAll("input[type=\"checkbox\"]:checked")
  ).map((el) => el.value);
  return selected;
}

function parseJournalAbbrev() {
  const lines = journalAbbrev.value.split("\n");
  const map = {};
  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    const parts = trimmed.split("=");
    if (parts.length < 2) return;
    const key = parts[0].trim();
    const value = parts.slice(1).join("=").trim();
    if (key && value) {
      map[key] = value;
    }
  });
  return Object.keys(map).length ? map : null;
}

async function runClean() {
  const payload = {
    input: inputBib.value,
    keep_fields: parseKeepFields(),
    titlecase: titlecase.checked,
    regen_keys: regenKeys.checked,
    journal_abbrev: parseJournalAbbrev(),
  };

  if (!payload.input.trim()) {
    outputBib.value = "";
    setStatus("Ready");
    return;
  }

  setStatus("Cleaning...");

  try {
    const res = await fetch("/api/clean", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Failed to clean bibliography.");
    }

    outputBib.value = data.output || "";
    setStatus("Cleaned");
  } catch (err) {
    outputBib.value = "";
    setStatus(err.message, true);
  }
}

function scheduleClean() {
  if (!autoClean.checked) return;
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(runClean, 350);
}

function updateCounts() {
  inputCount.textContent = `${inputBib.value.length} chars`;
}

cleanBtn.addEventListener("click", runClean);
copyBtn.addEventListener("click", async () => {
  if (!outputBib.value) return;
  await navigator.clipboard.writeText(outputBib.value);
  setStatus("Copied to clipboard");
});

downloadBtn.addEventListener("click", () => {
  if (!outputBib.value) return;
  const blob = new Blob([outputBib.value], { type: "text/x-bibtex" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "cleaned.bib";
  link.click();
  URL.revokeObjectURL(url);
});

loadExampleBtn.addEventListener("click", async () => {
  const res = await fetch("sample.bib");
  inputBib.value = await res.text();
  updateCounts();
  runClean();
});

clearBtn.addEventListener("click", () => {
  inputBib.value = "";
  outputBib.value = "";
  setStatus("Ready");
  updateCounts();
});

[inputBib, journalAbbrev].forEach((el) => {
  el.addEventListener("input", () => {
    updateCounts();
    scheduleClean();
  });
});

[titlecase, regenKeys].forEach((el) => {
  el.addEventListener("change", () => scheduleClean());
});

autoClean.addEventListener("change", () => {
  if (autoClean.checked) {
    runClean();
  }
});

optionsToggle.addEventListener("click", () => {
  const isOpen = optionsBody.classList.toggle("is-open");
  optionsToggle.textContent = isOpen ? "Hide advanced" : "Show advanced";
});

updateCounts();
setStatus("Ready");
