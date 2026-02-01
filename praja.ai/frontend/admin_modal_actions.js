(() => {
  const API_ROOT = "http://127.0.0.1:8000";
  const API_V1 = `${API_ROOT}/api/v1`;

  // We will store the currently opened complaint id here
  window.activeComplaintId = null;

  function getAdminToken() {
    return localStorage.getItem("admin_token") || localStorage.getItem("ADMIN_TOKEN") || sessionStorage.getItem("admin_token");
  }

  async function adminFetch(path, options = {}) {
    const token = getAdminToken();
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_ROOT}${path}`, { ...options, headers });

    let body = null;
    try { body = await res.json(); } catch (_) { }

    if (!res.ok) {
      const msg = (body && (body.detail || body.message)) || `${res.status} ${res.statusText}`;
      throw new Error(msg);
    }
    return body;
  }

  function escapeHTML(str) {
    return String(str || "").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  }

  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.innerText = val || "-";
  }

  function renderTimeline(items) {
    const box = document.getElementById("modalTimeline");
    if (!box) return;

    if (!items || items.length === 0) {
      box.innerHTML = `<div style="color:var(--text-sub); font-size:13px;">No timeline entries yet.</div>`;
      return;
    }

    box.innerHTML = items.map(ev => {
      const who = ev.changed_by_admin_id ? `Admin#${ev.changed_by_admin_id}` :
        ev.changed_by_user_id ? `User#${ev.changed_by_user_id}` : "System";
      const time = ev.created_at ? new Date(ev.created_at).toLocaleString() : "-";
      const note = ev.note ? escapeHTML(ev.note) : "";
      const status = escapeHTML(ev.status || "-");

      return `
        <div style="border:1px solid var(--border); border-radius:10px; padding:10px 12px; background:var(--surface);">
          <div style="display:flex; justify-content:space-between; gap:10px;">
            <div style="font-weight:800; color:var(--text-main);">${status}</div>
            <div style="font-size:12px; color:var(--text-sub);">${time}</div>
          </div>
          <div style="font-size:12px; color:var(--text-sub); margin-top:4px;">${who}</div>
          ${note ? `<div style="margin-top:8px; color:var(--text-main); font-size:13px;">${note}</div>` : ""}
        </div>
      `;
    }).join("");
  }

  async function loadTimelineForComplaint(complaintId) {
    const box = document.getElementById("modalTimeline");
    if (box) box.innerHTML = `<div style="color:var(--text-sub); font-size:13px;">Loading timeline...</div>`;

    const items = await adminFetch(`/api/v1/admin/complaints/${complaintId}/timeline`, { method: "GET" });
    renderTimeline(items);
  }

  function renderStepper(status) {
    const box = document.getElementById("modalStepper");
    if (!box) return;

    const steps = ["Open", "In Progress", "Resolved", "Closed"];
    let currentIndex = steps.indexOf(status);
    let isRejected = false;

    if (currentIndex === -1) {
      // Check for rejected
      if (status === "Rejected") isRejected = true;
      // Treat Reopened as Open-ish for stepper or handle separately. 
      // For now, if "Reopened", let's map it to index 0 ("Open") but show text Reopened
      if (status === "Reopened") currentIndex = 0;
    }

    if (isRejected) {
      box.innerHTML = `
        <div class="stepper-container">
            <div class="stepper-line-bg"></div>
             ${steps.map((s, i) => {
        return `
                 <div class="step-item">
                    <div class="step-circle" style="border-color:#ccc; background:#f4f4f4;">${i + 1}</div>
                    <span>${s}</span>
                 </div>`;
      }).join('')}
             <!-- Rejected Overlay -->
             <div style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; background:rgba(255,255,255,0.7); font-weight:bold; color:#ef4444; font-size:16px;">
                🚫 REJECTED
             </div>
        </div>`;
      return;
    }

    box.innerHTML = `
    <div class="stepper-container">
        <div class="stepper-line-bg"></div>
        ${steps.map((s, i) => {
      let cls = "";
      let check = i + 1;
      if (i < currentIndex) {
        cls = "completed";
        check = "✓";
      } else if (i === currentIndex) {
        cls = "active";
      }
      return `
            <div class="step-item ${cls}">
                <div class="step-circle">${check}</div>
                <span>${s}</span>
            </div>
            `;
    }).join('')}
    </div>
    `;
  }

  function filterStatusOptions(currentStatus) {
    const sel = document.getElementById("modalStatusSelect");
    if (!sel) return;

    const levels = { "Open": 0, "In Progress": 1, "Resolved": 2, "Closed": 3 };
    const currentLevel = levels[currentStatus];

    // Reset all
    Array.from(sel.options).forEach(opt => {
      opt.disabled = false;
      opt.style.color = "";
    });

    if (currentStatus === "Rejected") {
      // Can reopen
      return;
    }

    // If recognized level
    if (currentLevel !== undefined) {
      Array.from(sel.options).forEach(opt => {
        const val = opt.value;
        const lvl = levels[val];

        // Always allow Rejected and Reopened
        if (val === "Rejected" || val === "Reopened") return;

        // Disable if going backwards (lvl < currentLevel)
        // We also typically disable the *current* status so they don't pick it again, but that's optional.
        if (lvl !== undefined && lvl < currentLevel) {
          opt.disabled = true;
          opt.style.color = "#ccc";
        }
      });
    }
  }

  // Expose these to admin.html script
  window.prajaModalActions = {
    initForComplaint: async (complaint) => {
      window.activeComplaintId = complaint.id;

      // Current status view + preselect
      setText("modalStatus", complaint.status);
      const sel = document.getElementById("modalStatusSelect");
      if (sel) sel.value = complaint.status || "Open";

      // Render Stepper and Filter Options
      renderStepper(complaint.status || "Open");
      filterStatusOptions(complaint.status || "Open");

      const msg = document.getElementById("modalActionMsg");
      if (msg) msg.textContent = "";

      const note = document.getElementById("modalStatusNote");
      if (note) note.value = "";

      // Load timeline
      try {
        await loadTimelineForComplaint(complaint.id);
      } catch (e) {
        const box = document.getElementById("modalTimeline");
        if (box) box.innerHTML = `<div style="color:#b91c1c; font-size:13px;">❌ ${escapeHTML(e.message)}</div>`;
      }
    },

    updateStatusFromModal: async (refreshCallback) => {
      const msg = document.getElementById("modalActionMsg");
      const btn = document.getElementById("btnUpdateStatus");
      const token = getAdminToken();

      if (!token) {
        if (msg) msg.textContent = "❌ Admin token missing. Login again.";
        return;
      }
      if (!window.activeComplaintId) {
        if (msg) msg.textContent = "❌ No complaint selected.";
        return;
      }

      const status = (document.getElementById("modalStatusSelect")?.value || "").trim();
      const note = (document.getElementById("modalStatusNote")?.value || "").trim();

      if (!status) {
        if (msg) msg.textContent = "❌ Choose a status.";
        return;
      }

      if (btn) {
        btn.disabled = true;
        btn.textContent = "Updating...";
      }
      if (msg) msg.textContent = "";

      try {
        const updated = await adminFetch(`/api/v1/admin/complaints/${window.activeComplaintId}/status`, {
          method: "POST",
          body: JSON.stringify({ status, note: note || null }),
        });

        // Update status UI
        setText("modalStatus", updated.status);
        const sel = document.getElementById("modalStatusSelect");
        if (sel) sel.value = updated.status || status;

        // Re-render stepper and filter
        renderStepper(updated.status);
        filterStatusOptions(updated.status);

        if (msg) msg.textContent = `✅ Updated to "${updated.status}".`;

        // Refresh list/table
        if (typeof refreshCallback === "function") refreshCallback();

        // Refresh timeline
        await loadTimelineForComplaint(window.activeComplaintId);

      } catch (e) {
        if (msg) msg.textContent = `❌ ${e.message}`;
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.textContent = "Update Status";
        }
      }
    }
  };
})();
