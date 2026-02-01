from __future__ import annotations

import re
from typing import List, Dict, Tuple

# -----------------------------
# Utility helpers
# -----------------------------
_STOPWORDS = set("""
a an the and or but if then else when while of in on at to for from by with about as into like
is are was were be been being it this that these those i you he she they we
""".split())

_DEPT_HINTS = [
    ("road|pothole|highway|bridge|traffic|signal|street light|streetlight|flyover", "Public Works / Roads"),
    ("water|pipeline|tap|drain|sewer|sewage|leak|waterlogging|flood", "Water & Sanitation"),
    ("electric|power|transformer|voltage|outage|blackout", "Electricity / Power"),
    ("hospital|clinic|doctor|ambulance|medicine|health", "Health"),
    ("school|college|teacher|education|exam", "Education"),
    ("police|theft|assault|violence|threat|crime|harassment", "Police / Law & Order"),
    ("garbage|waste|dump|trash|cleaning|sanitation", "Municipal / Waste"),
    ("fire|smoke|burning", "Fire & Emergency"),
    ("land|encroach|illegal construction|building", "Urban Development / Land"),
]

_LOC_PAT = re.compile(r"\b(in|at|near|around)\s+([A-Z][A-Za-z0-9 .,'-]{3,60})")
_DATE_PAT = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b|\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}\b|\b\d{4}\b", re.IGNORECASE)


def _clean_text(s: str) -> str:
    s = (s or "").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _first_sentences(text: str, max_chars: int = 600) -> str:
    text = _clean_text(text)
    if not text:
        return ""
    # split into sentences (simple heuristic)
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for p in parts:
        if not p:
            continue
        if len(out) + len(p) + 1 > max_chars:
            break
        out = (out + " " + p).strip()
    return out or text[:max_chars]


def _top_keywords(text: str, k: int = 8) -> List[str]:
    text = _clean_text(text).lower()
    words = re.findall(r"[a-z]{3,}", text)
    freq: Dict[str, int] = {}
    for w in words:
        if w in _STOPWORDS:
            continue
        freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:k]]


def _infer_location(text: str) -> str:
    text = _clean_text(text)
    m = _LOC_PAT.search(text)
    if m:
        return m.group(2).strip(" ,.-")
    return ""


def _infer_date(text: str) -> str:
    text = _clean_text(text)
    m = _DATE_PAT.search(text)
    if m:
        return (m.group(0) or "").strip()
    return ""


def _infer_department(text: str) -> str:
    t = _clean_text(text).lower()
    for pat, dept in _DEPT_HINTS:
        if re.search(pat, t):
            return dept
    return "General Administration"


# -----------------------------
# Main summarizer (drop-in)
# -----------------------------
def summarize(title: str, description: str, category: str, priority: str, address: str = "") -> str:
    """
    Deterministic civic brief summarizer.
    Does NOT require LLM. Produces admin-ready structured text.
    """
    title = _clean_text(title)
    description = _clean_text(description)
    address = _clean_text(address)

    combined = "\n".join([x for x in [title, description, address] if x]).strip()

    # Guard: no content
    if not combined:
        return "Summary unavailable: no extractable text provided."

    location = _infer_location(combined) or address
    date_hint = _infer_date(combined)
    dept = _infer_department(combined)
    key_points = _first_sentences(description or combined, max_chars=700)
    keywords = _top_keywords(combined, k=8)

    # Basic action request detection (very lightweight)
    action = ""
    lower = combined.lower()
    if any(x in lower for x in ["please", "request", "urgent", "kindly", "need", "help"]):
        action = "Citizen requests prompt action/inspection and resolution."
    elif any(x in lower for x in ["complaint", "report", "issue", "problem"]):
        action = "Citizen is reporting an issue for official attention."
    else:
        action = "Issue reported for review."

    lines = []
    lines.append(f"**AI Case Brief**")
    lines.append(f"- Category: {category}")
    lines.append(f"- Priority: {priority}")
    if dept:
        lines.append(f"- Suggested Department: {dept}")
    if location:
        lines.append(f"- Location Hint: {location}")
    if date_hint:
        lines.append(f"- Date/Time Hint: {date_hint}")
    lines.append("")
    lines.append("**What happened (extracted):**")
    lines.append(key_points if key_points else (combined[:700] + ("..." if len(combined) > 700 else "")))
    lines.append("")
    lines.append("**Requested action:**")
    lines.append(action)
    lines.append("")
    if keywords:
        lines.append(f"**Keywords:** {', '.join(keywords)}")

    return "\n".join(lines).strip()

# ------------------------------
# v2 summary generator (overrides v1)
# Uses category display-name + suggested department
# ------------------------------
def summarize(
    title: str,
    description: str,
    category: str,
    priority: str,
    address: str = "",
    category_name: str | None = None,
    suggested_department: str | None = None,
) -> str:
    """
    Government-style issue brief.
    - category: category_id (e.g., emergency_disaster)
    - category_name: human label (e.g., Emergency & Disaster)
    - suggested_department: routing output for governance workflow
    """
    display_category = (category_name or category or "other").strip()
    display_dept = (suggested_department or "General Administration").strip()

    t = (title or "").strip() or "Citizen Report"
    d = (description or "").strip()

    # Keep description short in the letter body
    short_desc = d if len(d) <= 420 else (d[:420] + "…")

    # Tone: formal + urgent when needed
    urgent = " (Urgent)" if str(priority).strip().lower() in {"critical", "high"} else ""

    letter = (
        f"Respected Authorities{urgent},\n\n"
        f"I wish to bring to your immediate notice a problem regarding {display_category} "
        f"at {address if address else 'the reported location'}. The specific issue, identified as "
        f"'{t}', is currently active. This is a {priority} priority matter and requires prompt action.\n\n"
        f"Suggested Department: {display_dept}\n\n"
        f"Details: {short_desc if short_desc else t}.\n\n"
        f"Sincerely,\n"
        f"Heishnam\n"
    )
    return letter
