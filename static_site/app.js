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

const PROTECT_TITLE_TOKENS = [
  "PROTAC",
  "PROTACs",
  "BRD4",
  "BET",
  "CRBN",
  "Nrf2",
  "Keap1",
  "DNA",
  "RNA",
  "ATP",
  "X-ray",
  "SAR",
];

const REQUIRED_FIELDS = ["author", "title", "journal", "year", "volume", "pages"];

const SMALL_WORDS = new Set([
  "a",
  "an",
  "and",
  "as",
  "at",
  "but",
  "by",
  "for",
  "in",
  "nor",
  "of",
  "on",
  "or",
  "per",
  "the",
  "to",
  "vs",
  "via",
  "with",
  "without",
  "over",
  "into",
  "from",
]);

let debounceTimer = null;

function setStatus(message, isError = false) {
  outputStatus.textContent = message;
  outputStatus.style.color = isError ? "#b23b2a" : "";
}

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

function parseKeepFields() {
  return Array.from(
    keepFields.querySelectorAll("input[type=\"checkbox\"]:checked")
  ).map((el) => el.value);
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

function normalizePages(pages) {
  if (!pages) return pages;
  const trimmed = pages.trim();
  if (trimmed.includes("--")) {
    return trimmed.replace(/\s*--\s*/g, "--");
  }
  const parts = trimmed.split(/\s*(?:–|—|-)\s*/g);
  if (parts.length === 2 && /^\d+$/.test(parts[0]) && /^\d+$/.test(parts[1])) {
    return `${parts[0]}--${parts[1]}`;
  }
  return trimmed.replace(/\s*(?:–|—|-)\s*/g, "--");
}

function splitByBraces(text) {
  const parts = [];
  let current = "";
  let depth = 0;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (ch === "{") {
      if (depth === 0 && current) {
        parts.push({ text: current, braced: false });
        current = "";
      }
      depth += 1;
      current += ch;
    } else if (ch === "}") {
      depth = Math.max(0, depth - 1);
      current += ch;
      if (depth === 0) {
        parts.push({ text: current, braced: true });
        current = "";
      }
    } else {
      current += ch;
    }
  }

  if (current) {
    parts.push({ text: current, braced: depth > 0 });
  }

  return parts;
}

function protectTokensInTitle(title, tokens) {
  if (!title) return title;
  const parts = splitByBraces(title);
  const sorted = [...new Set(tokens)].sort((a, b) => b.length - a.length);

  const updated = parts.map((part) => {
    if (part.braced) return part.text;
    let out = part.text;
    sorted.forEach((token) => {
      const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const regex = new RegExp(`(^|[^\\w])(${escaped})(?!\\w)`, "g");
      out = out.replace(regex, (match, prefix, tok) => `${prefix}{${tok}}`);
    });
    return out;
  });

  return updated.join("");
}

function shouldCapitalize(word, index, text) {
  const lower = word.toLowerCase();
  if (index === 0) return true;

  let i = index - 1;
  while (i >= 0 && /\s/.test(text[i])) i -= 1;
  if (i < 0) return true;
  if (":.;!?".includes(text[i])) return true;

  return !SMALL_WORDS.has(lower);
}

function titlecaseSegment(text) {
  return text.replace(/\b([A-Za-z][A-Za-z0-9'’\-]*)\b/g, (match, word, offset) => {
    if (!shouldCapitalize(word, offset, text)) {
      return word.toLowerCase();
    }
    const lower = word.toLowerCase();
    return lower.charAt(0).toUpperCase() + lower.slice(1);
  });
}

function smartTitlecase(title) {
  if (!title) return title;
  const protectedTitle = protectTokensInTitle(title, PROTECT_TITLE_TOKENS);
  const parts = splitByBraces(protectedTitle);
  return parts
    .map((part) => (part.braced ? part.text : titlecaseSegment(part.text)))
    .join("");
}

function abbreviateJournal(journal, overrides) {
  if (!journal) return journal;
  if (overrides && overrides[journal]) return overrides[journal];
  return journal;
}

function makeKey(entry) {
  const author = entry.fields.author || "";
  const year = entry.fields.year || "";
  const title = entry.fields.title || "";

  const first = author.split(" and ")[0].trim();
  let last = "unknown";
  if (first.includes(",")) {
    last = first.split(",")[0].trim();
  } else if (first) {
    last = first.split(/\s+/).slice(-1)[0].trim();
  }

  const words = (title.match(/[A-Za-z0-9]+/g) || []).slice(0, 4);
  const short = words.map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join("") || "untitled";
  const lastSlug = last.toLowerCase().replace(/[^A-Za-z0-9]+/g, "") || "unknown";
  const yearSlug = (year.match(/\d+/g) || []).join("") || "nd";

  return `${lastSlug}${yearSlug}_${short}`;
}

function splitTopLevel(input) {
  const parts = [];
  let current = "";
  let depth = 0;
  let inQuotes = false;

  for (let i = 0; i < input.length; i += 1) {
    const ch = input[i];
    if (inQuotes) {
      current += ch;
      if (ch === '"' && input[i - 1] !== "\\") {
        inQuotes = false;
      }
      continue;
    }
    if (ch === '"') {
      inQuotes = true;
      current += ch;
      continue;
    }
    if (ch === "{") depth += 1;
    if (ch === "}") depth = Math.max(0, depth - 1);

    if (ch === "," && depth === 0) {
      parts.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  if (current.trim()) parts.push(current);
  return parts;
}

function splitKeyValue(segment) {
  let depth = 0;
  let inQuotes = false;
  for (let i = 0; i < segment.length; i += 1) {
    const ch = segment[i];
    if (inQuotes) {
      if (ch === '"' && segment[i - 1] !== "\\") {
        inQuotes = false;
      }
      continue;
    }
    if (ch === '"') {
      inQuotes = true;
      continue;
    }
    if (ch === "{") depth += 1;
    if (ch === "}") depth = Math.max(0, depth - 1);
    if (ch === "=" && depth === 0) {
      return [segment.slice(0, i).trim(), segment.slice(i + 1).trim()];
    }
  }
  return [null, null];
}

function stripEnclosing(value) {
  if (!value) return value;
  let out = value.trim();
  if ((out.startsWith("{") && out.endsWith("}")) || (out.startsWith('"') && out.endsWith('"'))) {
    out = out.slice(1, -1).trim();
  }
  return out;
}

function parseBibtex(text) {
  const entries = [];
  let i = 0;

  while (i < text.length) {
    const at = text.indexOf("@", i);
    if (at === -1) break;
    let j = at + 1;
    while (j < text.length && /\s/.test(text[j])) j += 1;
    let type = "";
    while (j < text.length && /[A-Za-z]/.test(text[j])) {
      type += text[j];
      j += 1;
    }
    while (j < text.length && /\s/.test(text[j])) j += 1;
    const open = text[j];
    if (open !== "{" && open !== "(") {
      i = at + 1;
      continue;
    }
    const close = open === "{" ? "}" : ")";
    j += 1;
    const contentStart = j;
    let depth = 1;
    while (j < text.length && depth > 0) {
      const ch = text[j];
      if (ch === open) depth += 1;
      if (ch === close) depth -= 1;
      j += 1;
    }
    const contentEnd = j - 1;
    const content = text.slice(contentStart, contentEnd);

    const parts = splitTopLevel(content);
    const id = (parts.shift() || "unknown").trim();
    const fields = {};
    const order = [];

    parts.forEach((part) => {
      const [key, rawValue] = splitKeyValue(part);
      if (!key) return;
      const value = stripEnclosing(rawValue);
      fields[key.toLowerCase()] = value;
      order.push(key.toLowerCase());
    });

    entries.push({ type: type.toLowerCase(), id, fields, order });
    i = j;
  }

  return entries;
}

function normalizeEntry(entry, keepOrder, opts) {
  if (entry.type !== "article") {
    return { ...entry, outputOrder: entry.order };
  }

  const outFields = {};
  keepOrder.forEach((field) => {
    if (entry.fields[field] && entry.fields[field].trim()) {
      outFields[field] = entry.fields[field].trim();
    }
  });

  if (outFields.author) outFields.author = outFields.author;
  if (outFields.title) {
    const t = outFields.title;
    outFields.title = opts.titlecase ? smartTitlecase(t) : t;
  }
  if (outFields.journal) {
    outFields.journal = abbreviateJournal(outFields.journal, opts.journalAbbrev);
  }
  if (outFields.pages) {
    outFields.pages = normalizePages(outFields.pages);
  }

  const missing = REQUIRED_FIELDS.filter((field) => !outFields[field]);
  if (missing.length) {
    const note = outFields.note ? `${outFields.note} ` : "";
    outFields.note = `${note}[MISSING: ${missing.join(", ")}]`.trim();
  }

  const outEntry = {
    type: "article",
    id: opts.regenKeys ? makeKey({ fields: outFields }) : entry.id,
    fields: outFields,
    outputOrder: keepOrder,
  };

  return outEntry;
}

function serializeEntry(entry) {
  const lines = [`@${entry.type}{${entry.id},`];
  const used = new Set();

  entry.outputOrder.forEach((field) => {
    const value = entry.fields[field];
    if (value) {
      lines.push(`  ${field} = {${value}},`);
      used.add(field);
    }
  });

  Object.keys(entry.fields).forEach((field) => {
    if (!used.has(field)) {
      lines.push(`  ${field} = {${entry.fields[field]}},`);
    }
  });

  lines.push("}");
  return lines.join("\n");
}

function cleanBibtex(text, options) {
  const entries = parseBibtex(text);
  const keepOrder = options.keepFields;
  const normalized = entries.map((entry) => normalizeEntry(entry, keepOrder, options));
  normalized.sort((a, b) => a.id.localeCompare(b.id));
  return normalized.map(serializeEntry).join("\n\n");
}

function updateCounts() {
  inputCount.textContent = `${inputBib.value.length} chars`;
}

function runClean() {
  const payload = {
    input: inputBib.value,
    keepFields: parseKeepFields(),
    titlecase: titlecase.checked,
    regenKeys: regenKeys.checked,
    journalAbbrev: parseJournalAbbrev(),
  };

  if (!payload.input.trim()) {
    outputBib.value = "";
    setStatus("Ready");
    return;
  }

  try {
    const output = cleanBibtex(payload.input, payload);
    outputBib.value = output;
    setStatus("Cleaned");
  } catch (err) {
    outputBib.value = "";
    setStatus(err.message || "Failed to clean bibliography.", true);
  }
}

function scheduleClean() {
  if (!autoClean.checked) return;
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(runClean, 350);
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

renderKeepFields();
updateCounts();
setStatus("Ready");
