import json
from pathlib import Path

# This reads your seed file and produces JSONL for training.
# You can later add a DB exporter too, but this keeps it simple and safe.

SEED = Path("../../../../data/seed/sample_complaints.json").resolve()
OUT = Path("dataset.jsonl").resolve()

def main():
    if not SEED.exists():
        raise SystemExit(f"Seed file not found: {SEED}")

    items = json.loads(SEED.read_text(encoding="utf-8"))
    out_lines = 0

    with OUT.open("w", encoding="utf-8") as f:
        for it in items:
            # Expecting fields like title/description/category/priority in your seed
            title = (it.get("title") or "").strip()
            desc = (it.get("description") or "").strip()
            text = (title + " " + desc).strip()
            if not text:
                continue

            category = (it.get("category") or it.get("ai_category") or "").strip()
            priority = (it.get("priority") or it.get("ai_priority") or "").strip()

            # If your seed doesn't have priority, keep it blank (we'll still train category)
            row = {
                "text": text,
                "category": category,
                "priority": priority
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            out_lines += 1

    print(f"✅ Wrote {out_lines} rows to {OUT}")

if __name__ == "__main__":
    main()
