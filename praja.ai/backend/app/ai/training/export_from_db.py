import json
from pathlib import Path
from sqlalchemy import text

from app.db.session import SessionLocal

OUT = Path("dataset.jsonl").resolve()

def main():
    db = SessionLocal()
    try:
        # Pull complaints. Use ai_category/ai_priority if present, else fallback to category/priority.
        rows = db.execute(text("""
            SELECT
              title,
              description,
              COALESCE(NULLIF(ai_category,''), NULLIF(category,''), '') AS label_category,
              COALESCE(NULLIF(ai_priority,''), NULLIF(priority,''), '') AS label_priority
            FROM complaints
            WHERE (title IS NOT NULL OR description IS NOT NULL)
            ORDER BY id DESC
            LIMIT 5000
        """)).fetchall()

        if not rows:
            raise SystemExit("No complaints found in DB to export.")

        written = 0
        with OUT.open("w", encoding="utf-8") as f:
            for title, desc, cat, pri in rows:
                title = (title or "").strip()
                desc = (desc or "").strip()
                text_blob = (title + " " + desc).strip()
                if len(text_blob) < 5:
                    continue

                row = {
                    "text": text_blob,
                    "category": (cat or "").strip(),
                    "priority": (pri or "").strip()
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1

        print(f"✅ Exported {written} rows to {OUT}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
