import json
from pathlib import Path
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

DATA = Path("dataset.jsonl").resolve()
OUT_DIR = (Path(__file__).resolve().parents[1] / "models").resolve()
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_jsonl(path: Path):
    X, y_cat, y_pri = [], [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        text = (row.get("text") or "").strip()
        if not text:
            continue
        X.append(text)
        y_cat.append((row.get("category") or "").strip())
        y_pri.append((row.get("priority") or "").strip())
    return X, y_cat, y_pri

def train_classifier(X, y, name: str):
    # keep only labeled rows
    X2, y2 = [], []
    for xi, yi in zip(X, y):
        if yi:
            X2.append(xi)
            y2.append(yi)

    labels = sorted(set(y2))
    if len(labels) < 2:
        print(f"⚠️ Not enough labeled classes to train {name}. Found: {labels}")
        return None

    # with tiny data, avoid stratify errors by checking class sizes
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X2, y2, test_size=0.33, random_state=42, stratify=y2
        )
    except Exception:
        X_train, X_test, y_train, y_test = train_test_split(
            X2, y2, test_size=0.33, random_state=42
        )

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=1, max_df=0.95)),
        ("clf", LogisticRegression(max_iter=2000))
    ])

    pipe.fit(X_train, y_train)
    preds = pipe.predict(X_test)

    print(f"\n===== {name.upper()} REPORT =====")
    print(classification_report(y_test, preds, zero_division=0))

    out_path = OUT_DIR / f"{name}_model.joblib"
    joblib.dump(pipe, out_path)
    print(f"✅ Saved: {out_path}")
    return pipe

def main():
    if not DATA.exists():
        raise SystemExit(f"dataset not found: {DATA}")

    X, y_cat, y_pri = load_jsonl(DATA)
    print(f"Loaded {len(X)} samples from {DATA}")

    train_classifier(X, y_cat, "category")
    train_classifier(X, y_pri, "priority")

if __name__ == "__main__":
    main()
