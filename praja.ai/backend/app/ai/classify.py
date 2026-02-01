from __future__ import annotations

import re
from typing import Tuple, List, Dict

from app.utils.labels import load_categories


def _clean(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t


# Extra keywords beyond categories.json (practical emergency boost)
EXTRA_KEYWORDS: Dict[str, List[str]] = {
    "emergency_disaster": [
        "fire", "fire accident", "burning", "smoke", "blast", "explosion",
        "ambulance", "injured", "injury", "bleeding", "unconscious", "critical",
        "collapse", "building collapse", "gas leak", "electrocution", "shock",
        "flood", "rescue", "help now", "life danger", "dying", "dead",
        "murder", "shoot", "gun", "knife", "attack", "violence", "rape"
    ],
    "public_safety_law": [
        "police", "theft", "robbery", "crime", "harassment", "stalking",
        "riot", "mob", "fight", "illegal", "smuggling", "trafficking"
    ],
    "roads_transport": [
        "pothole", "traffic jam", "signal not working", "bridge", "accident", "collision"
    ],
    "sanitation_waste": [
        "garbage", "trash", "dumping", "bad smell", "waste burning"
    ],
    "drainage_flooding": [
        "waterlogging", "sewage overflow", "blocked drain", "flooding after rain"
    ],
}


def predict_category(title: str, description: str) -> Tuple[str, float, List[str]]:
    """
    Returns (category_id, confidence, keywords_found)

    IMPORTANT:
    - category_id MUST match categories.json IDs
    - This is prototype/rule-based Phase-2 intelligence
    """
    cfg = load_categories()
    categories = cfg.get("categories", [])

    text = _clean(f"{title} {description}")
    if not text:
        return ("other", 0.2, [])

    scores: Dict[str, int] = {}
    hits: Dict[str, List[str]] = {}

    for c in categories:
        cid = c.get("id")
        if not cid:
            continue

        # Start with keywords_hint from categories.json
        kw_list = list(c.get("keywords_hint") or [])

        # Add extra keywords (emergency boost, etc)
        kw_list.extend(EXTRA_KEYWORDS.get(cid, []))

        count = 0
        found = []

        for kw in kw_list:
            k = _clean(str(kw))
            if not k:
                continue

            # phrase weight: multi-word hits more important
            if k in text:
                count += 2 if " " in k else 1
                found.append(k)

        if count > 0:
            scores[cid] = count
            hits[cid] = sorted(set(found))

    if not scores:
        return ("other", 0.35, [])

    # pick best
    best_id = max(scores, key=scores.get)
    best_score = scores[best_id]

    # Confidence heuristic
    if best_id == "emergency_disaster":
        conf = 0.93
    else:
        conf = min(0.90, 0.45 + 0.08 * min(best_score, 6))

    return (best_id, round(conf, 3), hits.get(best_id, []))
