import re
from typing import Dict, List, Tuple

# ---------- Category rules (Phase-1 explainable AI) ----------
RULES: Dict[str, List[str]] = {
    "Electricity": ["electricity", "power", "current", "outage", "transformer", "voltage", "blackout", "load shedding"],
    "Water Supply": ["water", "tap", "pipeline", "leak", "no water", "phed", "drinking water", "water supply"],
    "Roads & Potholes": ["road", "pothole", "bridge", "street", "broken road", "bad road", "crack"],
    "Sanitation/Waste": ["garbage", "waste", "drain", "sewage", "dirty", "mosquito", "overflow", "stinking", "blocked"],
    "Healthcare": ["hospital", "ambulance", "medicine", "doctor", "injury", "fever", "sick", "emergency ward"],
    "Public Safety": ["theft", "robbery", "attack", "violence", "fight", "fire", "emergency", "threat", "assault"],
    "Education": ["school", "college", "teacher", "exam", "classroom", "student"],
    "Transport": ["bus", "traffic", "parking", "train", "auto", "signal", "jam"],
    "Government Services": ["certificate", "document", "ration", "aadhaar", "passport", "bribe", "office", "scheme"],
}

DEPT_MAP = {
    "Water Supply": "PHED / Water Department",
    "Electricity": "Power Department",
    "Roads & Potholes": "PWD / Roads",
    "Sanitation/Waste": "Municipality / Sanitation",
    "Healthcare": "Health Department",
    "Public Safety": "Police / Disaster Management",
    "Education": "Education Department",
    "Transport": "Transport Department",
    "Government Services": "Citizen Service Center",
}

# ---------- AI signals (Phase-1 strong heuristics) ----------
RISK_KEYWORDS = [
    "accident", "bleeding", "fire", "attack", "violence", "emergency", "urgent", "help",
    "trapped", "assault", "threat", "riot",
    # poisoning/serious health events
    "poison", "poisonous", "deadly", "killing", "death", "die", "fainted", "unconscious"
]

VULNERABLE = ["child", "children", "pregnant", "elderly", "old", "disabled", "baby", "senior"]

HEALTH_HAZARD = [
    "sewage", "mosquito", "disease", "cholera", "dengue", "malaria",
    "contamination", "contaminated", "toxic", "vomiting", "diarrhea",
    "smelly", "foul", "stinking", "bad smell", "poison", "poisonous"
]

CORRUPTION = ["bribe", "corrupt", "fraud", "scam", "illegal fee", "commission"]

# ---------- Helper functions ----------
def _count_matches(text: str, keywords: List[str]) -> int:
    t = text.lower()
    return sum(1 for kw in keywords if kw in t)

def _duration_boost(text: str) -> int:
    """
    Adds points if complaint mentions duration like:
    'since 3 days', 'for 2 weeks', 'since last night', etc.
    """
    t = text.lower()
    boost = 0

    if "since last night" in t or "since yesterday" in t or "from yesterday" in t:
        boost += 8

    m = re.search(r"(since|for)\s+(\d+)\s*(day|days|week|weeks|month|months)", t)
    if m:
        n = int(m.group(2))
        unit = m.group(3)
        if "week" in unit:
            boost += min(18, 6 + n * 3)
        elif "month" in unit:
            boost += 22
        else:
            boost += min(14, 4 + n * 2)

    return boost

def extract_tags(text: str, category: str) -> List[str]:
    t = text.lower()
    tags = []

    if _count_matches(t, RISK_KEYWORDS) > 0:
        tags.append("Urgent/Risk")
    if _count_matches(t, VULNERABLE) > 0:
        tags.append("Vulnerable Group")
    if _count_matches(t, HEALTH_HAZARD) > 0:
        tags.append("Health Hazard")
    if _count_matches(t, CORRUPTION) > 0:
        tags.append("Corruption")

    # category-based tags
    if category in ["Electricity", "Water Supply", "Roads & Potholes", "Sanitation/Waste"]:
        tags.append("Infrastructure")
    if category in ["Healthcare", "Public Safety"]:
        tags.append("Safety/Health")

    # duration
    if _duration_boost(text) > 0:
        tags.append("Ongoing Issue")

    # de-dupe tags list
    seen = set()
    out = []
    for tag in tags:
        if tag not in seen:
            out.append(tag)
            seen.add(tag)
    return out

def classify_category(text: str) -> str:
    t = text.lower()
    best_cat = "Government Services"
    best_score = 0

    for cat, kws in RULES.items():
        score = _count_matches(t, kws)

        # extra boosts for strong phrases
        if cat == "Electricity" and ("no power" in t or "no electricity" in t):
            score += 2
        if cat == "Water Supply" and ("no water" in t):
            score += 2
        if cat == "Sanitation/Waste" and ("garbage" in t or "sewage" in t):
            score += 1

        if score > best_score:
            best_score = score
            best_cat = cat

    return best_cat

def route_department(category: str) -> str:
    return DEPT_MAP.get(category, "General Grievance Cell")

def predict_sla_hours(priority_label: str) -> int:
    # Phase-1 governance SLA (demo-friendly)
    return {
        "Critical": 2,
        "High": 24,
        "Medium": 72,
        "Low": 168,  # 7 days
    }.get(priority_label, 72)

def priority_score_and_label(text: str, category: str) -> Tuple[int, str, str, Dict[str, int]]:
    """
    Returns:
      score (0-100),
      label (Low/Medium/High/Critical),
      explanation (short human),
      breakdown (transparent scoring contributions)
    """
    t = text.lower()

    risk = _count_matches(t, RISK_KEYWORDS) > 0
    vuln = _count_matches(t, VULNERABLE) > 0
    hazard = _count_matches(t, HEALTH_HAZARD) > 0
    corrupt = _count_matches(t, CORRUPTION) > 0
    duration_pts = _duration_boost(text)

    # base severity by category (more stable than random)
    base = 20
    if category in ["Healthcare", "Public Safety"]:
        base = 50
    elif category in ["Electricity", "Water Supply"]:
        base = 32
    elif category in ["Sanitation/Waste", "Roads & Potholes"]:
        base = 26

    breakdown = {
        "base": base,
        "risk": 0,
        "vulnerable": 0,
        "hazard": 0,
        "corruption": 0,
        "duration": duration_pts,
    }

    if risk:
        breakdown["risk"] = 25
    if vuln:
        breakdown["vulnerable"] = 15
    if hazard:
        breakdown["hazard"] = 18
    if corrupt:
        breakdown["corruption"] = 12

    # special: contaminated/poison water must not be Low
    if category == "Water Supply" and (hazard or risk):
        breakdown["hazard"] += 12

    # special: death/killing terms are immediate escalation
    if any(w in t for w in ["killing", "death", "die", "deadly"]):
        breakdown["risk"] += 20

    score = sum(breakdown.values())
    score = max(0, min(100, score))

    if score >= 80:
        label = "Critical"
    elif score >= 60:
        label = "High"
    elif score >= 35:
        label = "Medium"
    else:
        label = "Low"

    reasons = []
    if category in ["Healthcare", "Public Safety"]:
        reasons.append("safety/health category")
    if risk:
        reasons.append("emergency/risk keywords")
    if vuln:
        reasons.append("vulnerable group")
    if hazard:
        reasons.append("health hazard")
    if corrupt:
        reasons.append("possible corruption")
    if duration_pts > 0:
        reasons.append("duration/recency signals")

    explanation = "Priority based on: " + (", ".join(reasons) if reasons else "general severity")
    return score, label, explanation, breakdown

def analyze_text(text: str) -> Dict:
    """
    Single AI "brain" entrypoint (useful for hackathon demo).
    """
    category = classify_category(text)
    department = route_department(category)
    tags = extract_tags(text, category)
    score, label, explanation, breakdown = priority_score_and_label(text, category)
    sla_hours = predict_sla_hours(label)

    return {
        "category": category,
        "department": department,
        "tags": tags,
        "priority_score": score,
        "priority": label,
        "sla_hours": sla_hours,
        "explanation": explanation,
        "breakdown": breakdown,
    }
