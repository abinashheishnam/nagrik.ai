from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from app.auth.dependencies import get_current_user
from app.ai.pipeline import enrich

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

class DraftRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=160)
    address: str = ""
    latitude: float | None = None
    longitude: float | None = None

@router.post("/draft")
def draft_description(payload: DraftRequest, user=Depends(get_current_user)):
    ai = enrich(payload.title, payload.title, address=payload.address)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    who = f"{user.full_name} ({user.phone})"
    where = payload.address or (f"{payload.latitude}, {payload.longitude}" if payload.latitude and payload.longitude else "Unknown location")

    # Dynamic / Sentimental Description Generation
    # "Not readymade" as requested
    
    cat = ai['ai_category']
    pri = ai['ai_priority']
    
    # 1. Openers
    openers_emergency = [
        "Urgent Attention Required,",
        "Critical Incident Report,",
        "To the Emergency Response Team,",
        "Respected Authorities (Urgent),"
    ]
    openers_normal = [
        "Respected Sir/Madam,",
        "To the Concerned Department,",
        "Dear Administrative Officer,",
        "Subject: Civic Grievance Report,"
    ]
    
    # 2. Context Setters
    contexts = [
        f"I am writing to formally report a {cat} issue located at {where}.",
        f"I wish to bring to your immediate notice a problem regarding {cat} at {where}.",
        f"This is to inform you about a concerning situation involving {cat} at {where}.",
        f"A serious issue has been observed at {where} related to {cat}."
    ]
    
    # 3. Impact / Sentiment
    impacts_crit = [
        "This is causing severe distress to the residents and poses a danger to life.",
        "The situation is critical and could lead to further harm if not addressed immediately.",
        "Residents are living in fear due to this ongoing threat.",
        "This requires immediate intervention to prevent any mishap."
    ]
    impacts_high = [
        "This is significantly affecting the daily lives of people in this area.",
        "The community is facing major difficulties due to this unresolved issue.",
        "It has become a major nuisance and needs prompt resolution.",
        "We are deeply concerned about the lack of maintenance here."
    ]
    impacts_med = [
        "It is causing inconvenience to commuters and pedestrians.",
        "This needs repair to restore normalcy in the neighborhood.",
        "We request you to look into this at the earliest convenience.",
        "Proper maintenance would be greatly appreciated by the locals."
    ]
    
    # 4. Closers
    closers = [
        "We trust the administration will resolve this promptly.",
        "Your quick action in this regard will be highly appreciated.",
        "Looking forward to a positive response from your end.",
        "Please treat this matter with the priority it deserves."
    ]

    # Selection Logic
    import random
    
    opener = random.choice(openers_emergency) if pri in ["High", "Critical"] else random.choice(openers_normal)
    context = random.choice(contexts)
    closer = random.choice(closers)
    
    if pri in ["High", "Critical"]:
        impact = random.choice(impacts_crit + impacts_high)
        urgency_text = "This is a severe issue that requires immediate action."
    else:
        impact = random.choice(impacts_med + impacts_high)
        urgency_text = "I request you to kindly look into this issue."
    
    # Narrative Construction
    narrative = (
        f"{opener}\n\n"
        f"{context} The specific issue, identified as '{payload.title}', is currently active. "
        f"{impact} {urgency_text}\n\n"
        f"Details: {payload.title}. "
        f"Our automated system has flagged this as {pri} Priority based on the severity. "
        f"{closer}\n\n"
        f"Sincerely,\n{user.full_name}\n"
        f"Contact: {user.phone}"
    )

    return {"generated_description": narrative, "ai": ai}
