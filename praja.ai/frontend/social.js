const API = window.API_BASE || 'http://127.0.0.1:8000/api/v1';

const form = document.getElementById('socialForm');
const submitBtn = document.getElementById('submitBtn');
const btnText = document.getElementById('btnText');
const errorMsg = document.getElementById('errorMsg');
const resetBtn = document.getElementById('resetBtn');

const resultSection = document.getElementById('resultSection');
const statusBadge = document.getElementById('statusBadge');
const refreshSpinner = document.getElementById('refreshSpinner');
const sourceIdDisp = document.getElementById('sourceIdDisp');
const complaintIdDisp = document.getElementById('complaintIdDisp');

const contentGrid = document.getElementById('contentGrid');
const postText = document.getElementById('postText');
const postLen = document.getElementById('postLen');
const transcriptText = document.getElementById('transcriptText');
const transLen = document.getElementById('transLen');
const metaContent = document.getElementById('metaContent');

// AI Fields
const aiCategory = document.getElementById('aiCategory');
const aiPriority = document.getElementById('aiPriority');
const aiConfidence = document.getElementById('aiConfidence');
const aiSummary = document.getElementById('aiSummary');
const aiRationale = document.getElementById('aiRationale');

const finalSubmitBtn = document.getElementById('finalSubmitBtn');
const manualEntrySection = document.getElementById('manualEntrySection');
const successSection = document.getElementById('successSection');
const successCompId = document.getElementById('successCompId');
const successSourceId = document.getElementById('successSourceId');

let pollInterval = null;
let currentComplaintId = null;
let currentSourceId = null;

// --- Main Analysis Flow (Step 1) ---

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorMsg.style.display = 'none';
    manualEntrySection.style.display = 'none';
    successSection.style.display = 'none';

    setLoading(true);
    resetResultsForNewAnalysis();

    const url = document.getElementById('socialUrl').value.trim();
    const note = document.getElementById('socialNote').value.trim();

    // Get logged-in user ID
    const userId = localStorage.getItem("USER_ID") ? parseInt(localStorage.getItem("USER_ID")) : null;

    try {
        const res = await fetch(`${API}/social/intake`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ url, note, user_id: userId })
        });

        if (!res.ok) throw new Error("Submission failed. Ensure you are logged in.");

        const data = await res.json();
        currentComplaintId = data.complaint_id;
        currentSourceId = data.social_source_id;

        // Check if already submitted previously in this browser
        if (localStorage.getItem(`praja_social_submitted_${currentSourceId}`)) {
            showSuccess(currentComplaintId, currentSourceId);
            setLoading(false);
            return;
        }

        // Show results area (Status part only initially)
        resultSection.style.display = 'block';
        sourceIdDisp.innerText = data.social_source_id;
        complaintIdDisp.innerText = data.complaint_id;

        updateStatusUI(data.status);

        // Start polling
        startPolling(data.social_source_id, data.complaint_id);

    } catch (err) {
        errorMsg.innerText = err.message || "An error occurred";
        errorMsg.style.display = 'block';
        setLoading(false);
    }
});

function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    btnText.innerText = isLoading ? "Analyzing..." : "Analyze Social Content";
}

function resetResultsForNewAnalysis() {
    resultSection.style.display = 'none';
    contentGrid.style.display = 'none';
    manualEntrySection.style.display = 'none';
    successSection.style.display = 'none';
    finalSubmitBtn.disabled = true;

    // Clear fields
    postText.innerText = '';
    transcriptText.innerText = '';
    metaContent.innerText = '';
    aiCategory.innerText = '-';
    aiPriority.innerText = '-';
    aiConfidence.innerText = '-';
    aiSummary.innerText = '-';
    aiRationale.innerText = '-';

    if (pollInterval) clearInterval(pollInterval);
}

function startPolling(sourceId, complaintId) {
    // Immediate check
    checkStatus(sourceId, complaintId);

    pollInterval = setInterval(() => {
        checkStatus(sourceId, complaintId);
    }, 2000);
}

async function checkStatus(sourceId, complaintId) {
    try {
        refreshSpinner.style.display = 'inline-block';

        const res = await fetch(`${API}/social/status/${sourceId}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) return;
        const data = await res.json();

        updateStatusUI(data.status);

        if (['DONE', 'FAILED', 'INVALID_URL', 'DUPLICATE', 'BLOCKED'].includes(data.status)) {
            clearInterval(pollInterval);
            refreshSpinner.style.display = 'none';
            setLoading(false);

            if (data.status === 'DONE') {
                await fetchAndDisplayContent(sourceId);
                await fetchAndDisplayAI(complaintId);

                // Allow submit only if we have meaningful data
                finalSubmitBtn.disabled = false;
            } else {
                errorMsg.innerText = `Processing stopped: ${data.status} - ${data.error || 'Check details'}`;
                errorMsg.style.display = 'block';
                manualEntrySection.style.display = 'block';
            }
        }
    } catch (e) {
        console.error("Poll error", e);
    }
}

function updateStatusUI(status) {
    statusBadge.className = 'status-badge';
    statusBadge.innerText = status;

    if (status === 'DONE') {
        statusBadge.classList.add('status-done');
        statusBadge.style.background = '#dcfce7';
        statusBadge.style.color = '#166534';
    } else if (['FAILED', 'INVALID_URL', 'DUPLICATE', 'BLOCKED'].includes(status)) {
        statusBadge.classList.add('status-error');
        statusBadge.style.background = '#fee2e2';
        statusBadge.style.color = '#991b1b';
    } else {
        statusBadge.classList.add('status-processing');
        statusBadge.style.background = '#dbeafe';
        statusBadge.style.color = '#1e40af';
    }
}

async function fetchAndDisplayContent(id) {
    try {
        const res = await fetch(`${API}/social/source/${id}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error("Failed to fetch content");

        const data = await res.json();
        const extracted = data.extracted || {};

        // Show grid
        contentGrid.style.display = 'grid';

        // Fill data
        if (extracted.post_text_preview) {
            postText.innerText = extracted.post_text_preview;
            postLen.innerText = `Length: ${extracted.post_text_len || 0} chars`;
        } else {
            postText.innerText = 'No text content extracted.';
            postLen.innerText = '';
        }

        if (extracted.transcript_preview) {
            transcriptText.innerText = extracted.transcript_preview;
            transLen.innerText = `Length: ${extracted.transcript_len || 0} chars`;
        } else {
            transcriptText.innerText = 'No transcript available.';
            transLen.innerText = '';
        }

        metaContent.innerText = JSON.stringify(extracted.source_metadata || {}, null, 2);

    } catch (e) {
        console.error("Content fetch error", e);
    }
}

async function fetchAndDisplayAI(complaintId) {
    if (!complaintId) return;

    // Attempt logic: Admin ID -> My Complaints -> Public?
    const token = localStorage.getItem("ADMIN_TOKEN") || localStorage.getItem("USER_TOKEN");

    try {
        let aiData = null;

        // 1. Try Admin Endpoint (Best for full details)
        const adminRes = await fetch(`${API}/admin/complaints/${complaintId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (adminRes.ok) {
            const data = await adminRes.json();
            aiData = data.complaint;
        } else {
            // 2. Fallback: Try My Complaints (Citizen context)
            const myRes = await fetch(`${API}/complaints/my`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (myRes.ok) {
                const list = await myRes.json();
                const found = list.find(c => c.id === complaintId);
                if (found) aiData = found;
            }
        }

        if (aiData) {
            aiCategory.innerText = aiData.ai_category || 'Unclassified';
            aiPriority.innerText = aiData.ai_priority || 'Normal';
            aiConfidence.innerText = aiData.ai_confidence ? (typeof aiData.ai_confidence === 'number' ? (aiData.ai_confidence * 100).toFixed(0) + '%' : aiData.ai_confidence) : '-';
            aiSummary.innerText = aiData.ai_summary || 'Analysis pending or not available.';
            aiRationale.innerText = aiData.ai_rationale || '';

            if (aiData.ai_priority === 'Critical') aiPriority.style.color = '#dc2626';
            if (aiData.ai_priority === 'High') aiPriority.style.color = '#ea580c';
        } else {
            aiSummary.innerText = "Could not fetch AI details. (Permission denied)";
        }

    } catch (e) {
        console.error("AI fetch error", e);
        aiSummary.innerText = "Error fetching AI analysis.";
    }
}

// --- Final Submit Action (Step 2) ---
finalSubmitBtn.addEventListener('click', () => {
    // 1. Mark local storage
    if (currentSourceId) {
        localStorage.setItem(`praja_social_submitted_${currentSourceId}`, "1");
    }

    // 2. Switch UI to success
    showSuccess(currentComplaintId, currentSourceId);
});

function showSuccess(compId, sourceId) {
    contentGrid.style.display = 'none'; // Hide preview
    finalSubmitBtn.disabled = true;

    successSection.style.display = 'block';
    successCompId.innerText = compId;
    successSourceId.innerText = sourceId;

    // Scroll to success
    successSection.scrollIntoView({ behavior: 'smooth' });
}

// --- Reset ---
resetBtn.addEventListener('click', () => {
    document.getElementById('socialForm').reset();
    resetResultsForNewAnalysis();
    setLoading(false);
    errorMsg.style.display = 'none';
    currentComplaintId = null;
    currentSourceId = null;
});

// --- Utils & Header ---

window.copyToClipboard = function (text) {
    navigator.clipboard.writeText(text).then(() => {
        alert("Copied to clipboard!");
    });
};

function getAuthHeaders() {
    const token = localStorage.getItem("ADMIN_TOKEN") || localStorage.getItem("USER_TOKEN");
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}

// Initialize header (Copy from previous shared logic)
async function initHeader() {
    const token = localStorage.getItem("USER_TOKEN") || localStorage.getItem("ADMIN_TOKEN");
    if (!token) return;

    try {
        const rootApi = API.replace('/api/v1', '');
        const res = await fetch(`${rootApi}/auth/me`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.ok) {
            const user = await res.json();
            const avatar = document.getElementById("userAvatar");
            const name = document.getElementById("menuUserName");
            const userId = user.id || user.user_id; // handle different schemas

            if (avatar) avatar.innerText = (user.full_name || user.username || "U").charAt(0).toUpperCase();
            if (name) name.innerText = user.full_name || user.username || "User";
            if (userId) localStorage.setItem("USER_ID", userId);
        }
    } catch (e) { console.error("Header init failed", e); }
}

initHeader();

// User Menu Toggle
window.toggleMenu = function () {
    const menu = document.getElementById("userMenu");
    if (menu) menu.classList.toggle("active");
};
document.addEventListener("click", function (e) {
    if (!e.target.closest(".user-menu-container")) {
        const m = document.getElementById("userMenu");
        if (m) m.classList.remove("active");
    }
});
const btnLogout = document.getElementById("btnLogout");
if (btnLogout) {
    btnLogout.addEventListener("click", () => {
        localStorage.clear();
        window.location.href = "user_login.html";
    });
}
