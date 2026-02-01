from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Any

# backend/app/utils/labels.py
# Reads praja.ai/data/labels/categories.json (repo-level data folder)

@lru_cache(maxsize=1)
def load_categories() -> Dict[str, Any]:
    """
    Loads category configuration from repo data/labels/categories.json.

    Returns dict with:
      - version
      - categories (list)
      - priority_labels (list)
    """
    # Resolve repo root: .../praja.ai/backend/app/utils/labels.py -> .../praja.ai/backend -> .../praja.ai
    backend_dir = Path(__file__).resolve().parents[2]     # .../backend
    praja_root = backend_dir.parent                      # .../praja.ai
    cfg_path = praja_root / "data" / "labels" / "categories.json"

    if not cfg_path.exists():
        raise FileNotFoundError(f"categories.json not found at {cfg_path}")

    data = json.loads(cfg_path.read_text(encoding="utf-8"))

    if not isinstance(data.get("categories"), list) or len(data["categories"]) == 0:
        raise ValueError("categories.json has no categories")

    if "priority_labels" not in data or not isinstance(data["priority_labels"], list):
        data["priority_labels"] = ["Low", "Medium", "High", "Critical"]

    return data


def allowed_category_ids() -> List[str]:
    cfg = load_categories()
    return [c["id"] for c in cfg.get("categories", []) if isinstance(c, dict) and "id" in c]


def normalize_ai_outputs(category_id: str | None, priority: str | None) -> Dict[str, str]:
    """
    Enforces:
    - category must be in categories.json else 'other'
    - if category is emergency_disaster -> priority Critical
    - priority must be one of priority_labels else Medium
    """
    cfg = load_categories()
    allowed_cats = set(allowed_category_ids())
    allowed_pri = set(cfg.get("priority_labels", ["Low", "Medium", "High", "Critical"]))

    cat = (category_id or "").strip() or "other"
    if cat not in allowed_cats:
        cat = "other"

    pri = (priority or "").strip() or "Medium"
    if pri not in allowed_pri:
        pri = "Medium"

    if cat == "emergency_disaster":
        pri = "Critical"

    return {"category": cat, "priority": pri}
def category_id_to_name(category_id: str) -> str:
    cfg = load_categories()
    for c in cfg.get("categories", []):
        if c.get("id") == category_id:
            return c.get("name") or category_id
    return category_id
