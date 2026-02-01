import json
from app.ai.classify import predict_category
from app.ai.priority import predict_priority
from app.ai.summarize import summarize

def enrich(title: str, description: str, address: str = "") -> dict:
    ai_category, cat_conf, keywords = predict_category(title, description)
    ai_priority, pr_score, pr_reasons = predict_priority(title, description, ai_category)

    # combine confidence: category confidence + priority score averaged
    confidence = round((cat_conf + pr_score) / 2, 3)

    ai_summary = summarize(title, description, ai_category, ai_priority, address=address)

    return {
        "ai_category": ai_category,
        "ai_priority": ai_priority,
        "ai_confidence": confidence,
        "ai_summary": ai_summary,
        "ai_keywords": json.dumps(keywords),
        "ai_rationale": json.dumps(pr_reasons),
        "language": "en",
    }
