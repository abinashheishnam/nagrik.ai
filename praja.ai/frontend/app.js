const API = "http://127.0.0.1:8000/api/v1";

const textEl = document.getElementById("text");
const submitBtn = document.getElementById("submitBtn");
const refreshBtn = document.getElementById("refreshBtn");
const clearBtn = document.getElementById("clearBtn");
const demoBtn = document.getElementById("demoBtn");

const resultEl = document.getElementById("result");
const tableBody = document.getElementById("tableBody");
const apiStatus = document.getElementById("apiStatus");
const toastEl = document.getElementById("toast");

const kTotal = document.getElementById("kTotal");
const kCritical = document.getElementById("kCritical");
const kHigh = document.getElementById("kHigh");
const kTopCat = document.getElementById("kTopCat");
const highlightLine = document.getElementById("highlightLine");

const searchInput = document.getElementById("searchInput");
const priorityFilter = document.getElementById("priorityFilter");
const categoryFilter = document.getElementById("categoryFilter");
const sortBy = document.getElementById("sortBy");

let ALL = [];

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.remove("hidden");
  clearTimeout(toastEl._t);
  toastEl._t = setTimeout(() => toastEl.classList.add("hidden"), 2400);
}

function pill(priority) {
  const p = String(priority || "");
  if (p === "Critical") return `<span class="pill bad">Critical</span>`;
  if (p === "High") return `<span class="pill warn">High</span>`;
  if (p === "Medium") return `<span class="pill neutral">Medium</span>`;
  return `<span class="pill good">Low</span>`;
}

function slaPill(hours) {
  const h = Number(hours);
  if (h <= 2) return `<span class="pill bad">${esc(h)}h</span>`;
  if (h <= 24) return `<span class="pill warn">${esc(h)}h</span>`;
  if (h <= 72) return `<span class="pill neutral">${esc(h)}h</span>`;
  return `<span class="pill good">${esc(h)}h</span>`;
}

function tagsView(tags) {
  const list = (tags || []).filter(Boolean);
  if (!list.length) return `<span class="tagPill">—</span>`;
  return `<div class="tags">${list.map(t => `<span class="tagPill">${esc(t)}</span>`).join("")}</div>`;
}

function breakdownView(b) {
  if (!b || typeof b !== "object") return "";
  const rows = Object.entries(b).map(([k, v]) => `<li><b>${esc(k)}:</b> +${esc(v)}</li>`).join("");
  return `<div class="breakdown"><b>Score breakdown</b><ul>${rows}</ul></div>`;
}

function displayCategory(obj) {
  return (obj && (obj.ai_category_name || obj.ai_category || obj.category)) ? (obj.ai_category_name || obj.ai_category || obj.category) : "other";
}

function displayDept(obj) {
  return (obj && (obj.suggested_department || obj.department)) ? (obj.suggested_department || obj.department) : "General Administration";
}

async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`);
    if (!r.ok) throw new Error("bad");
    apiStatus.textContent = "API: connected ✅";
    apiStatus.className = "pill good";
  } catch {
    apiStatus.textContent = "API: offline ❌";
    apiStatus.className = "pill bad";
  }
}

async function submitComplaint() {
  const text = textEl.value.trim();
  if (!text) {
    toast("Type a complaint first 🙂");
    return;
  }

  submitBtn.disabled = true;
  resultEl.innerHTML = `<div class="resultEmpty">Analyzing with AI…</div>`;

  try {
    const url = `${API}/complaints/?text=${encodeURIComponent(text)}`;
    const r = await fetch(url, { method: "POST" });
    const data = await r.json();

    resultEl.innerHTML = `
      <div><b>ID:</b> ${esc(data.id)}</div>
      <div><b>Category:</b> ${esc(displayCategory(data))} &nbsp;|&nbsp; <b>Dept:</b> ${esc(displayDept(data))}</div>
      <div style="margin-top:6px;">
        <b>Priority:</b> ${pill(data.priority)} &nbsp;
        <b>Score:</b> ${esc(data.priority_score)}/100 &nbsp;
        <b>SLA:</b> ${slaPill(data.sla_hours)}
      </div>
      <div style="margin-top:10px;"><b>AI Tags:</b> ${tagsView(data.tags)}</div>
      <div style="margin-top:10px;"><b>Why:</b> ${esc(data.explanation)}</div>
      ${breakdownView(data.breakdown)}
      <div style="margin-top:10px; opacity:.9;"><b>Text:</b> ${esc(data.text)}</div>
    `;

    toast("Submitted ✅ Saved to MySQL");
    await loadComplaints();
  } catch (e) {
    resultEl.innerHTML = `<div class="resultEmpty">Error: ${esc(e.message)}</div>`;
  } finally {
    submitBtn.disabled = false;
  }
}

function computeKPIs(list) {
  const total = list.length;
  const crit = list.filter(x => x.priority === "Critical").length;
  const high = list.filter(x => x.priority === "High").length;

  const byCat = {};
  for (const x of list) {
    const c = x.category || "Unknown";
    byCat[c] = (byCat[c] || 0) + 1;
  }
  const topCat = Object.entries(byCat).sort((a, b) => b[1] - a[1])[0]?.[0] || "—";

  kTotal.textContent = total;
  kCritical.textContent = crit;
  kHigh.textContent = high;
  kTopCat.textContent = topCat;

  // highlight line
  const topPriority = list[0];
  if (topPriority) {
    highlightLine.textContent = `Top priority: ${topPriority.priority} • ${topPriority.category} (${topPriority.priority_score}/100)`;
  } else {
    highlightLine.textContent = "No grievances yet.";
  }

  // populate category filter
  const cats = ["ALL", ...Object.keys(byCat).sort()];
  categoryFilter.innerHTML = cats.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
}

function applyFilters() {
  const q = searchInput.value.trim().toLowerCase();
  const p = priorityFilter.value;
  const c = categoryFilter.value;
  const sort = sortBy.value;

  let list = [...ALL];

  if (q) {
    list = list.filter(x =>
      (x.text || "").toLowerCase().includes(q) ||
      (x.category || "").toLowerCase().includes(q) ||
      (x.department || "").toLowerCase().includes(q) ||
      (x.tags || []).join(",").toLowerCase().includes(q)
    );
  }
  if (p !== "ALL") list = list.filter(x => x.priority === p);
  if (c !== "ALL") list = list.filter(x => x.category === c);

  if (sort === "newest") {
    // We don't have created_at in DB; approximate newest by list order from backend if it returns newest first.
    // If your backend sorts by score, this keeps stable; otherwise ignore.
    // (Hackathon-simple)
  } else {
    list.sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0));
  }

  renderTable(list);
}

function renderTable(list) {
  if (!list.length) {
    tableBody.innerHTML = `<tr><td colspan="8">No matching complaints.</td></tr>`;
    return;
  }

  tableBody.innerHTML = list.map(c => `
    <tr>
      <td>${esc(c.id)}</td>
      <td>${esc(c.category)}</td>
      <td>${esc(c.department)}</td>
      <td>${tagsView(c.tags)}</td>
      <td>${slaPill(c.sla_hours)}</td>
      <td><b>${esc(c.priority_score)}</b></td>
      <td>${pill(c.priority)}</td>
      <td>${esc(c.text)}</td>
    </tr>
  `).join("");
}

async function loadComplaints() {
  tableBody.innerHTML = `<tr><td colspan="8">Loading…</td></tr>`;
  try {
    const r = await fetch(`${API}/complaints/`);
    const list = await r.json();

    // Ensure consistent fields
    ALL = (list || []).map(x => ({
      ...x,
      tags: Array.isArray(x.tags) ? x.tags : (typeof x.tags === "string" ? x.tags.split(",").filter(Boolean) : []),
      sla_hours: Number(x.sla_hours ?? 72),
      priority_score: Number(x.priority_score ?? 0),
    }));

    // default: keep AI triage feel (score desc)
    ALL.sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0));

    computeKPIs(ALL);
    applyFilters();
  } catch {
    tableBody.innerHTML = `<tr><td colspan="8">Failed to load. Is backend running?</td></tr>`;
  }
}

clearBtn.addEventListener("click", () => {
  textEl.value = "";
  toast("Cleared");
});

demoBtn.addEventListener("click", () => {
  textEl.value = "water is deadly poisonous killing people children vomiting since yesterday urgent";
  toast("Demo text loaded");
});

submitBtn.addEventListener("click", submitComplaint);
refreshBtn.addEventListener("click", loadComplaints);
searchInput.addEventListener("input", applyFilters);
priorityFilter.addEventListener("change", applyFilters);
categoryFilter.addEventListener("change", applyFilters);
sortBy.addEventListener("change", applyFilters);

checkHealth();
loadComplaints();
// ===== Voice Input (MediaRecorder -> Whisper STT) =====

let mediaRecorder = null;
let audioChunks = [];

async function startVoice() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];

    // audio/webm works well for Chrome on Linux
    mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      // Stop mic stream tracks
      stream.getTracks().forEach((t) => t.stop());

      const blob = new Blob(audioChunks, { type: "audio/webm" });

      const formData = new FormData();
      formData.append("file", blob, "voice.webm");

      // Update UI (optional)
      setVoiceStatus("Transcribing...");

      const res = await fetch("http://127.0.0.1:8000/api/v1/audio/transcribe", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text();
        console.error("STT error:", errText);
        setVoiceStatus("Voice failed ❌");
        alert("Voice transcription failed. Check backend logs.");
        return;
      }

      const data = await res.json();
      const text = (data.text || "").trim();

      // Put transcript into complaint input
      const input =
        document.querySelector("#complaintText") ||
        document.querySelector("#grievanceText") ||
        document.querySelector("textarea");

      if (input) input.value = text;

      setVoiceStatus("Done ✅");
    };

    mediaRecorder.start();
    setVoiceStatus("Recording... 🎙️");
  } catch (err) {
    console.error(err);
    alert("Mic permission denied or not available.");
  }
}

function stopVoice() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

function setVoiceStatus(msg) {
  const el = document.querySelector("#voiceStatus");
  if (el) el.textContent = msg;
}
