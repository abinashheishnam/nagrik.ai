from __future__ import annotations
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import joblib
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ---- NEW ----
import app.ai.stt as stt

MODELS_DIR = Path(__file__).resolve().parent / "models"

_category_model = None
_priority_model = None
_whisper_model = None

_sent = SentimentIntensityAnalyzer()


def load_models() -> None:
    """
    Load all AI models:
    - Category classifier
    - Priority classifier
    - Whisper STT (for live audio + uploads)
    """
    global _category_model, _priority_model, _whisper_model

    # ---- CLASSIFIERS ----
    cat_path = MODELS_DIR / "category_model.joblib"
    pri_path = MODELS_DIR / "priority_model.joblib"

    if cat_path.exists():
        _category_model = joblib.load(cat_path)
        print("[AI] Category model loaded")

    if pri_path.exists():
        _priority_model = joblib.load(pri_path)
        print("[AI] Priority model loaded")

    # ---- WHISPER STT ----
    try:
        import whisper

        # You can tune this:
        # tiny / base / small / medium / large
        model_size = "base"

        _whisper_model = whisper.load_model(model_size)

        # Inject into STT module so live audio + API can use it
        stt.whisper_model = _whisper_model

        print(f"[AI] Whisper STT model loaded ({model_size})")

    except Exception as e:
        _whisper_model = None
        stt.whisper_model = None
        print("[AI] Whisper STT not available:", type(e).__name__, str(e))


def predict_category(text: str) -> Tuple[Optional[str], float]:
    if _category_model is None:
        return None, 0.0
    proba = _category_model.predict_proba([text])[0]
    idx = int(proba.argmax())
    label = str(_category_model.classes_[idx])
    return label, float(proba[idx])


def predict_priority(text: str) -> Tuple[Optional[str], float]:
    if _priority_model is None:
        return None, 0.0
    proba = _priority_model.predict_proba([text])[0]
    idx = int(proba.argmax())
    label = str(_priority_model.classes_[idx])
    return label, float(proba[idx])


def sentiment(text: str) -> Tuple[str, float, Dict[str, Any]]:
    scores = _sent.polarity_scores(text)
    comp = float(scores.get("compound", 0.0))
    if comp >= 0.35:
        label = "Positive"
    elif comp <= -0.35:
        label = "Negative"
    else:
        label = "Neutral"
    return label, comp, scores
