from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Complaint
from app.ai.pipeline import enrich

def main():
    db: Session = SessionLocal()

    rows = db.query(Complaint).all()
    updated = 0

    for c in rows:
        # If any AI field missing -> generate
        if not c.ai_summary or not c.ai_keywords or not c.ai_rationale or not c.ai_category or not c.ai_priority:
            ai = enrich(c.title or "", c.description or "", address=c.address or "")
            c.ai_category = ai["ai_category"]
            c.ai_priority = ai["ai_priority"]
            c.ai_confidence = ai["ai_confidence"]
            c.ai_summary = ai["ai_summary"]
            c.ai_keywords = ai["ai_keywords"]
            c.ai_rationale = ai["ai_rationale"]
            c.source = c.source or "web"
            c.language = c.language or ai["language"]
            c.final_category = c.final_category or ""
            c.final_priority = c.final_priority or ""
            # also make API priority reflect AI (optional but good for demo)
            c.priority = c.ai_priority
            updated += 1

    db.commit()
    db.close()
    print(f"Backfilled AI for {updated} complaint(s).")

if __name__ == "__main__":
    main()
