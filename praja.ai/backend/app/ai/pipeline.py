import json

from app.ai.classify import predict_category
from app.ai.priority import predict_priority
from app.ai.summarize import summarize
from app.utils.labels import normalize_ai_outputs, category_id_to_name
from app.services.routing_ai import suggest_department


def enrich(title: str, description: str, address: str = "") -> dict:
    # 1) Predict category
    ai_category, cat_conf, keywords = predict_category(title, description)

    # 2) Predict priority
    ai_priority, pr_score, pr_reasons = predict_priority(title, description, ai_category)

    # 3) Enforce policy (Emergency => Critical, invalid => other)
    norm = normalize_ai_outputs(ai_category, ai_priority)
    ai_category = norm["category"]
    ai_priority = norm["priority"]

    # 4) Confidence heuristic
    confidence = round((float(cat_conf or 0.0) + float(pr_score or 0.0)) / 2, 3)

    # 5) Governance signals
    category_name = category_id_to_name(ai_category)
    suggested_dept = suggest_department(ai_category)

    # 6) Summary (use display fields)
    ai_summary = summarize(
        title,
        description,
        ai_category,
        ai_priority,
        address=address,
        category_name=category_name,
        suggested_department=suggested_dept,
    )

    return {
        "ai_category": ai_category,
        "ai_category_name": category_name,
        "ai_priority": ai_priority,
        "ai_confidence": confidence,
        "suggested_department": suggested_dept,
        "ai_summary": ai_summary,
        "ai_keywords": json.dumps(keywords),
        "ai_rationale": json.dumps(pr_reasons),
        "language": "en",
    }
