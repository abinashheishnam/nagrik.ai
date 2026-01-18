from __future__ import annotations
from datetime import datetime, timezone
import json
import re
from typing import Dict, Any, Tuple

from app.ai.ml import predict_category, predict_priority, sentiment

def _keywords(text: str, limit: int = 6):
    # super simple keyword extractor (hackathon friendly)
    tokens = re.findall(r"[a-zA-Z]{3,}", (text or "").lower())
    stop = {"the","and","for","with","this","that","from","have","has","been","since","near","need","urgent","please","area"}
    out = []
    for t in tokens:
        if t in stop: 
            continue
        if t not in out:
            out.append(t)
        if len(out) >= limit:
            break
    return out

def enrich_text(title: str, description: str) -> Dict[str, Any]:
    text = (title or "").strip()
    if description:
        text = (text + " " + description.strip()).strip()

    # ML category + priority
    cat, cat_conf = predict_category(text)
    pri, pri_conf = predict_priority(text)

    # If priority model is weak, we can upgrade using simple emergency signals
    emergency_signals = ["emergency", "critical", "life", "accident", "fire", "ambulance", "blood", "attack", "violence"]
    em_hit = any(w in text.lower() for w in emergency_signals)
    if em_hit:
        pri = "High" if pri != "Critical" else pri
        pri_conf = max(pri_conf, 0.80)

    # Sentiment
    sent_label, sent_score, sent_raw = sentiment(text)

    # Defaults if model can't decide
    if not cat:
        cat = "General"
        cat_conf = max(cat_conf, 0.50)
    if not pri:
        pri = "Medium"
        pri_conf = max(pri_conf, 0.55)

    # Compose AI artifacts
    kws = _keywords(text)
    ai_summary = f"{cat} issue reported: {title}. Priority assessed as {pri}. Sentiment: {sent_label}."
    rationale = []
    if em_hit:
        rationale.append("emergency signal keywords detected")
    rationale.append(f"ml_category_conf={round(cat_conf,3)}")
    rationale.append(f"ml_priority_conf={round(pri_conf,3)}")
    rationale.append(f"sentiment={sent_label}({round(sent_score,3)})")

    # Overall confidence: blend
    conf = float(max(cat_conf, pri_conf))

    return {
        "language": "en",
        "ai_category": cat,
        "ai_priority": pri,
        "ai_confidence": round(conf, 3),
        "ai_summary": ai_summary,
        "ai_keywords": json.dumps(kws),
        "ai_rationale": json.dumps(rationale),
        # sentiment info (not DB fields, but usable in draft/report text)
        "sentiment_label": sent_label,
        "sentiment_score": round(sent_score, 3),
        "sentiment_raw": sent_raw,
    }

def generate_official_report(*, user_full_name: str, user_phone: str, title: str,
                             address: str, latitude: float | None, longitude: float | None,
                             ai: Dict[str, Any]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    loc = address or (f"{latitude}, {longitude}" if latitude is not None and longitude is not None else "Unknown")

    return (
        "Citizen Report (AI Auto-generated)\n"
        f"- Reporter: {user_full_name} ({user_phone})\n"
        f"- Time: {now}\n"
        f"- Location: {loc}\n"
        f"- Issue: {title}\n"
        f"- AI Category: {ai.get('ai_category')} | AI Priority: {ai.get('ai_priority')} | Confidence: {ai.get('ai_confidence')}\n"
        f"- Sentiment: {ai.get('sentiment_label')} (score={ai.get('sentiment_score')})\n"
        f"- AI Summary: {ai.get('ai_summary')}\n"
        f"- Keywords: {ai.get('ai_keywords')}\n"
        f"- Rationale: {ai.get('ai_rationale')}\n"
        "\nNotes: This report was generated automatically. Admin can verify and override if needed.\n"
    )
