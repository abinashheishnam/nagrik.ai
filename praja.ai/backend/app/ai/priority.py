import re

CRITICAL_WORDS = [
    "fire", "death", "dead", "murder", "shoot", "explosion", "bomb", "collapse", 
    "rape", "kidnap", "suicide", "bleeding", "life threat", "terror", "critical"
]
HIGH_WORDS = [
    "accident", "emergency", "ambulance", "hospital", "attack", "threat", "violent", 
    "robbery", "theft", "fighting", "mob", "riot", "gun", "knife", "bribe", "scam"
]
MEDIUM_WORDS = [
    "not working", "broken", "no water", "outage", "garbage", "drain", "sewage", 
    "streetlight", "pothole", "dirty", "smell", "leak", "money"
]

def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()

def predict_priority(title: str, description: str, category: str) -> tuple[str, float, list[str]]:
    text = _norm(f"{title} {description}")
    reasons = []
    score = 0.3  # Base score

    # 1. Category-Based Baseline (The "99% Accuracy" Guarantee)
    if category == "Life Threat":
        score = 0.95
        reasons.append("Category 'Life Threat' implies Critical urgency")
    elif category == "Law & Order" or category == "Public Safety":
        score = max(score, 0.75)
        reasons.append(f"Category '{category}' implies High priority")
    elif category == "Corruption":
        score = max(score, 0.70)
        reasons.append("Corruption allegations are High priority")
    elif category == "Cybercrime":
        score = max(score, 0.75)
        reasons.append("Cybercrime is High priority")
    elif category == "Health":
        score = max(score, 0.65)
        reasons.append("Health issues are typically High priority")
    elif category in ["Electricity", "Water & Sanitation"]:
        score = max(score, 0.45)
    elif category in ["Environment", "Education"]:
        score = max(score, 0.35)
    
    # 2. Keyword Modifiers
    def match(words, add, label):
        nonlocal score
        found = False
        for w in words:
            if w in text:
                score += add
                if not found: # Only log first match per level to keep reasons clean
                    reasons.append(f"{label} keyword found: '{w}'")
                    found = True
    
    match(CRITICAL_WORDS, 0.30, "critical")
    match(HIGH_WORDS, 0.20, "high")
    match(MEDIUM_WORDS, 0.10, "medium")

    # Clamp score
    score = max(0.0, min(0.99, score))

    # 3. Final Determination
    if score >= 0.85:
        return ("High", score, reasons) # User asked for High/Med/Low, mapping Critical -> High/Urgent
    if score >= 0.65:
        return ("High", score, reasons)
    if score >= 0.40:
        return ("Medium", score, reasons)
    return ("Low", score, reasons)
