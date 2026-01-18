import os
import re
import random
from typing import Optional, Dict, Any, Tuple

import requests
from fastapi import APIRouter, Form, Request, Response
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import User, Complaint, WhatsAppSession

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "praja-verify-token")

# -----------------------------
# Persona (human touch)
# -----------------------------
ASSISTANT_NAME = os.getenv("WHATSAPP_ASSISTANT_NAME", "Praja Assistant")

def _say(msg: str, tone: str = "info") -> str:
    base = (msg or "").strip()
    if not base:
        base = "Okay."
    if tone == "emergency":
        return f"{base}\n\nIf you are in immediate danger, call 112 now.\n— {ASSISTANT_NAME}"
    if tone == "confirm":
        return f"{base}\n\n(Reply YES or NO)\n— {ASSISTANT_NAME}"
    if tone == "success":
        return f"{base}\n\n— {ASSISTANT_NAME}"
    if tone == "error":
        return f"{base}\n\nNo worries — try again.\n— {ASSISTANT_NAME}"
    return f"{base}\n\n— {ASSISTANT_NAME}"

def _twiml(message: str) -> str:
    message = (
        message.replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;")
               .replace('"', "&quot;")
               .replace("'", "&apos;")
    )
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{message}</Message></Response>'

# -----------------------------
# Helpers
# -----------------------------
def _now():
    from datetime import datetime
    return datetime.utcnow()

def _clean_phone(raw: str) -> str:
    raw = (raw or "").replace("whatsapp:", "").strip()
    raw = re.sub(r"[^0-9+]", "", raw)
    return raw

def _safe_text(val: Optional[str], fallback: str = "") -> str:
    if val is None:
        return fallback
    v = str(val).strip()
    return v if v else fallback

def _normalize(text: str) -> str:
    t = _safe_text(text, "").lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _looks_like_email(s: str) -> bool:
    s = _safe_text(s, "")
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", s))

def _title_from_text(text: str) -> str:
    t = _safe_text(text, "")
    if not t:
        return "WhatsApp Complaint"
    words = t.split()
    title = " ".join(words[:8])
    return title[:160] if len(title) > 160 else title

def _guess_address_from_text(text: str) -> Optional[str]:
    t = _safe_text(text, "")
    if not t:
        return None
    m = re.search(r"\b(near|at|in|around)\b\s+(.+)$", t, flags=re.IGNORECASE)
    if m:
        addr = m.group(2).strip()
        if 3 <= len(addr) <= 255:
            return addr[:255]
    return None

def _extract_latlon_from_google_maps_link(text: str) -> Tuple[Optional[float], Optional[float]]:
    t = _safe_text(text, "")
    if not t:
        return None, None

    m = re.search(r"[?&]q=([0-9.\-]+)(?:%2C|,)([0-9.\-]+)", t)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except Exception:
            return None, None

    m2 = re.search(r"/@([0-9.\-]+),([0-9.\-]+),", t)
    if m2:
        try:
            return float(m2.group(1)), float(m2.group(2))
        except Exception:
            return None, None

    # short form sometimes: google.com/maps/place/...!3dLAT!4dLON
    m3 = re.search(r"!3d([0-9.\-]+)!4d([0-9.\-]+)", t)
    if m3:
        try:
            return float(m3.group(1)), float(m3.group(2))
        except Exception:
            return None, None

    return None, None

def _detect_language(text: str) -> str:
    t = _safe_text(text, "")
    if not t:
        return "en"
    try:
        from app.utils.language import detect_language
        code = detect_language(t)
        if isinstance(code, str) and code.strip():
            return code.strip()[:10]
    except Exception:
        pass
    try:
        from langdetect import detect
        code = detect(t)
        if isinstance(code, str) and code.strip():
            return code.strip()[:10]
    except Exception:
        pass
    return "en"

# -----------------------------
# Session safety
# -----------------------------
GREETINGS = {"hi", "hey", "hello", "hii", "yo", "good morning", "good evening", "good afternoon", "sup", "hola"}
END_WORDS = {"nothing", "no issue", "no", "nope", "thanks", "thank you", "ok", "okay", "bye", "good night", "gn", "hmm"}
HELP_WORDS = {"help", "i need help", "need help", "advice", "guide", "what to do", "assist", "assistance", "is this assistance"}

STALE_SESSION_MINUTES = int(os.getenv("STALE_SESSION_MINUTES", "10"))

def _is_greeting(text: str) -> bool:
    return _normalize(text) in GREETINGS

def _is_end(text: str) -> bool:
    return _normalize(text) in END_WORDS

def _is_helpish(text: str) -> bool:
    t = _normalize(text)
    return (t in HELP_WORDS) or ("need help" in t) or ("help me" in t) or ("advice" in t)

def _minutes_since(dt) -> int:
    try:
        from datetime import datetime
        if not dt:
            return 0
        return int((datetime.utcnow() - dt).total_seconds() // 60)
    except Exception:
        return 0

def _is_stale_session(s: WhatsAppSession) -> bool:
    return _minutes_since(getattr(s, "updated_at", None)) >= STALE_SESSION_MINUTES

def _looks_like_issue_text(text: str) -> bool:
    t = _normalize(text)
    if not t:
        return False
    if len(t.split()) < 3:
        return False
    kws = [
        "broken", "bad", "not working", "no water", "water", "electric", "power", "outage",
        "road", "garbage", "drain", "flood", "pothole", "streetlight",
        "crime", "robbery", "threat", "fire", "smoke",
        "ambulance", "injured", "accident", "stalking", "following", "harass"
    ]
    return any(k in t for k in kws)

# -----------------------------
# Emergency detection (strong)
# -----------------------------
EMERGENCY_PHRASES = {
    "police": [
        "follow", "following me", "someone following", "being followed",
        "threat", "threatened", "danger", "unsafe", "scared",
        "harassment", "stalking", "someone watching", "someone outside",
        "break in", "break-in", "robbery", "attack", "violence",
        "help me", "sos", "urgent", "kidnap", "abduction",
        "call police", "need police", "someone trying to hurt me",
        "knife", "gun", "assault"
    ],
    "medical": [
        "bleeding", "unconscious", "not breathing", "can't breathe",
        "heart", "heart attack", "stroke", "collapsed",
        "injured", "accident", "ambulance", "fainted",
        "severe pain", "medical emergency"
    ],
    "fire": [
        "fire", "smoke", "burning", "gas leak", "explosion",
        "flames", "house on fire", "kitchen fire"
    ]
}

def _detect_emergency_super(text: str) -> str:
    t = _normalize(text)
    if not t:
        return ""
    if t in ("emergency", "urgent", "sos"):
        return "police"
    for etype, phrases in EMERGENCY_PHRASES.items():
        for p in phrases:
            if p in t:
                return etype
    return ""

def _emergency_numbers_for(type_: str) -> str:
    if type_ == "fire":
        return "🔥 Fire: 101 | 🚨 Emergency: 112"
    if type_ == "medical":
        return "🚑 Ambulance: 108 | 🚨 Emergency: 112"
    if type_ == "police":
        return "👮 Police: 100 | 🚨 Emergency: 112"
    return "🚨 Emergency: 112"

def _chat_reply(text: str) -> str:
    t = _normalize(text)

    if t in ("hmm", "hmmm", "ok", "okay"):
        return "I’m here. Tell me what’s going on — one line is enough."

    if "smoke" in t or "fire" in t:
        return (
            "If there’s smoke/fire nearby:\n"
            "1) Get people out and stay upwind.\n"
            "2) Call 101 or 112 now.\n"
            "3) Don’t go inside.\n"
            "Want me to trigger an emergency alert too? (YES/NO)"
        )

    if "following" in t or "stalking" in t or "threat" in t:
        return (
            "If someone is following you:\n"
            "1) Move to a crowded/public place.\n"
            "2) Call 112 if you feel unsafe.\n"
            "3) Share live location with someone you trust.\n"
            "Want me to trigger an emergency alert? (YES/NO)"
        )

    if "police siren" in t or "siren" in t:
        return (
            "Hearing sirens can mean something is happening nearby.\n"
            "Are you safe? If you feel at risk, call 112.\n"
            "If you want, tell me your area/landmark and I can file a report."
        )

    if _is_helpish(text) or "help" in t:
        return (
            "Tell me what happened (one sentence).\n"
            "If it’s urgent, type EMERGENCY.\n"
            "If you want me to file a report, describe the issue + location."
        )

    return (
        "Got you. Tell me:\n"
        "1) What’s happening?\n"
        "2) Where is it (landmark or paste Google Maps link)?\n"
        "If it’s urgent, type EMERGENCY."
    )

# -----------------------------
# DB helpers
# -----------------------------
def _get_password_hash_for_system_user() -> str:
    try:
        from app.auth.security import get_password_hash
        return get_password_hash("WHATSAPP_SYSTEM_USER_NOLOGIN")
    except Exception:
        return "WHATSAPP_SYSTEM_USER_NOLOGIN"

def _find_user_by_phone(db: Session, phone: str) -> Optional[User]:
    return db.query(User).filter(User.phone == phone).first()

def _create_user(db: Session, phone: str, name: str, email: Optional[str]) -> User:
    u = User(
        full_name=name,
        phone=phone,
        email=email,
        password_hash=_get_password_hash_for_system_user(),
        created_at=_now()
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

def _update_user_profile(db: Session, user: User, name: str, email: Optional[str]):
    user.full_name = name
    user.email = email
    db.commit()

def _needs_profile(user: User) -> bool:
    nm = _safe_text(getattr(user, "full_name", ""), "").strip().lower()
    return (not nm) or (nm == "whatsapp user")

def _get_or_create_session(db: Session, phone: str) -> WhatsAppSession:
    s = db.query(WhatsAppSession).filter(WhatsAppSession.phone == phone).first()
    if s:
        return s
    s = WhatsAppSession(phone=phone, state="START", updated_at=_now())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

def _reset_session(db: Session, s: WhatsAppSession, state: str = "START"):
    s.state = state
    s.name = None
    s.email = None
    s.otp_code = None
    s.otp_expires_at = None
    s.issue_text = None
    s.address = None
    s.latitude = None
    s.longitude = None
    s.updated_at = _now()
    db.commit()

def _issue_otp(db: Session, s: WhatsAppSession) -> str:
    from datetime import timedelta
    otp = f"{random.randint(100000, 999999)}"
    s.otp_code = otp
    s.otp_expires_at = _now() + timedelta(minutes=5)
    s.updated_at = _now()
    db.commit()
    return otp

def _verify_otp(s: WhatsAppSession, user_input: str) -> bool:
    ui = _safe_text(user_input, "")
    if not ui or not s.otp_code or not s.otp_expires_at:
        return False
    if _now() > s.otp_expires_at:
        return False
    return ui == s.otp_code

# -----------------------------
# AI + Geo
# -----------------------------
def _run_ai(text: str) -> Dict[str, Any]:
    t = _safe_text(text, "")
    try:
        from app.ai import pipeline as ai_pipeline
        for fn_name in ("run", "process", "process_text", "analyze", "predict"):
            fn = getattr(ai_pipeline, fn_name, None)
            if callable(fn):
                out = fn(t)
                if isinstance(out, dict):
                    cat = out.get("category") or out.get("ai_category") or "General"
                    pri = out.get("priority") or out.get("ai_priority") or "Medium"
                    conf = out.get("confidence") or out.get("ai_confidence") or 0.0
                    summ = out.get("summary") or out.get("ai_summary") or ""
                    kw = out.get("keywords") or out.get("ai_keywords") or ""
                    rat = out.get("rationale") or out.get("ai_rationale") or ""
                    return {
                        "ai_category": str(cat)[:80],
                        "ai_priority": str(pri)[:20],
                        "ai_confidence": float(conf) if conf is not None else 0.0,
                        "ai_summary": str(summ),
                        "ai_keywords": str(kw),
                        "ai_rationale": str(rat),
                    }
    except Exception:
        pass
    return {
        "ai_category": "General",
        "ai_priority": "Medium",
        "ai_confidence": 0.0,
        "ai_summary": (t[:220] if t else ""),
        "ai_keywords": "",
        "ai_rationale": "",
    }

def _geocode_address(address: str) -> Tuple[Optional[float], Optional[float]]:
    addr = _safe_text(address, "")
    if not addr:
        return None, None
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": addr, "format": "json", "limit": 1}
        headers = {"User-Agent": "PrajaAI/1.0 (hackathon)"}
        r = requests.get(url, params=params, headers=headers, timeout=8)
        if r.status_code != 200:
            return None, None
        data = r.json()
        if not data:
            return None, None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None, None

def _build_auto_report(user: User, phone: str, address: str, issue: str, lang: str, ai: Dict[str, Any], emergency_type: str = "") -> str:
    when_utc = _now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "Citizen Report (AI Auto-generated)",
        f"- Reporter: {user.full_name} ({phone})",
        f"- Time: {when_utc} UTC",
        f"- Location: {address}",
        f"- Issue: {issue}",
        f"- Language: {lang}",
        f"- AI Category: {ai.get('ai_category','General')} | AI Priority: {ai.get('ai_priority','Medium')} | Confidence: {ai.get('ai_confidence',0.0)}",
    ]
    if emergency_type:
        lines.append(f"- Emergency Type: {emergency_type.upper()}")
    if _safe_text(ai.get("ai_summary"), ""):
        lines.append(f"- AI Summary: {ai.get('ai_summary','')}")
    if _safe_text(ai.get("ai_keywords"), ""):
        lines.append(f"- Keywords: {ai.get('ai_keywords','')}")
    if _safe_text(ai.get("ai_rationale"), ""):
        lines.append(f"- Rationale: {ai.get('ai_rationale','')}")
    lines.append("")
    lines.append("Notes: This report was generated automatically. Admin can verify and override if needed.")
    return "\n".join(lines) + "\n"

def _create_complaint_from_session(db: Session, user: User, s: WhatsAppSession, force_priority: Optional[str] = None, emergency_type: str = "") -> int:
    issue = _safe_text(s.issue_text, "No description provided")
    addr = _safe_text(s.address, "Unknown")
    lang = _detect_language(issue)
    ai = _run_ai(issue)

    if force_priority:
        ai["ai_priority"] = force_priority

    desc = _build_auto_report(user, s.phone, addr, issue, lang, ai, emergency_type=emergency_type)

    c = Complaint(
        user_id=user.id,
        title=_title_from_text(issue),
        description=desc,
        category=ai["ai_category"],
        priority=ai["ai_priority"],
        status="NEW" if emergency_type else "Open",
        latitude=s.latitude,
        longitude=s.longitude,
        address=addr,
        created_at=_now(),
        source="whatsapp",
        language=lang,
        ai_category=ai["ai_category"],
        ai_priority=ai["ai_priority"],
        ai_confidence=float(ai["ai_confidence"] or 0.0),
        ai_summary=_safe_text(ai.get("ai_summary"), ""),
        ai_keywords=_safe_text(ai.get("ai_keywords"), ""),
        ai_rationale=_safe_text(ai.get("ai_rationale"), ""),
        final_category=ai["ai_category"],
        final_priority=ai["ai_priority"],
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c.id

def _confirm_message(s: WhatsAppSession) -> str:
    preview_addr = _safe_text(s.address, "Unknown")
    gps_note = "✅ GPS pinned" if (s.latitude is not None and s.longitude is not None) else "⚠️ No GPS pin (share WhatsApp Location or paste Google Maps link)"
    return (
        "Quick check before I submit:\n"
        f"📝 Issue: {_safe_text(s.issue_text,'')}\n"
        f"📍 Location: {preview_addr}\n"
        f"{gps_note}\n"
        "Reply YES to submit or NO to cancel."
    )

# -----------------------------
# Twilio webhook
# -----------------------------
@router.post("/twilio")
async def twilio_webhook(
    From: str = Form(...),
    Body: str = Form(""),
    Latitude: Optional[str] = Form(None),
    Longitude: Optional[str] = Form(None),
    Address: Optional[str] = Form(None),
):
    phone = _clean_phone(From)
    msg = _safe_text(Body, "")

    lat = None
    lon = None
    try:
        if Latitude:
            lat = float(Latitude)
        if Longitude:
            lon = float(Longitude)
    except Exception:
        lat, lon = None, None

    link_lat, link_lon = _extract_latlon_from_google_maps_link(msg)
    if link_lat is not None and link_lon is not None:
        lat, lon = link_lat, link_lon

    db = SessionLocal()
    try:
        if not phone:
            return Response(content=_twiml(_say("Invalid sender.", "error")), media_type="application/xml")

        s = _get_or_create_session(db, phone)
        user = _find_user_by_phone(db, phone)

        # Stale session auto-clear
        if _is_stale_session(s) and s.state not in ("START", "ASK_ISSUE", "ASK_NAME", "ASK_EMAIL", "ASK_OTP"):
            _reset_session(db, s, state=("ASK_ISSUE" if user else "START"))
            s = _get_or_create_session(db, phone)

        # Always accept location link/pin and store it (any state)
        if lat is not None and lon is not None:
            s.latitude = lat
            s.longitude = lon
            if Address and Address.strip():
                s.address = Address[:255]
            if not s.address:
                s.address = "Pinned via Google Maps"
            s.updated_at = _now()
            db.commit()
            # If they were confirming, re-confirm with updated pin
            if s.state in ("CONFIRM", "EMERGENCY_CONFIRM_1", "EMERGENCY_CONFIRM_2"):
                return Response(content=_twiml(_say("📍 Location received.\n" + _confirm_message(s), "confirm")), media_type="application/xml")

        # GLOBAL EMERGENCY OVERRIDE (any state)
        em_type = _detect_emergency_super(msg)
        if em_type:
            s.issue_text = s.issue_text or msg
            s.state = "EMERGENCY_CONFIRM_1"
            s.updated_at = _now()
            db.commit()

            nums = _emergency_numbers_for(em_type)
            return Response(content=_twiml(_say(
                f"🚨 I hear you. This may be a {em_type.upper()} emergency.\n\n"
                f"{nums}\n\n"
                "Are you safe right now?\n"
                "Reply YES to trigger emergency alert, or NO to handle as a normal report.\n\n"
                "Tip: Share your location pin (WhatsApp Location) or paste a Google Maps link for an exact map pin.",
                "emergency"
            )), media_type="application/xml")

        # Soft reset greetings/help out of YES/NO traps
        if _is_greeting(msg) or _is_helpish(msg):
            if s.state in ("CONFIRM", "EMERGENCY_CONFIRM_1", "EMERGENCY_CONFIRM_2"):
                _reset_session(db, s, state=("ASK_ISSUE" if user else "START"))
                return Response(content=_twiml(_say(
                    "Hey 👋 I’m here.\nTell me what’s going on in one line.\n\n"
                    "If it’s urgent, type EMERGENCY.\n"
                    "To pin location: share WhatsApp Location or paste Google Maps link.",
                    "info"
                )), media_type="application/xml")

            nm = user.full_name if user else "there"
            return Response(content=_twiml(_say(f"Hey {nm} 👋\nTell me what’s going on — I’ll help you.", "info")), media_type="application/xml")

        if _normalize(msg) in ("help", "menu"):
            return Response(content=_twiml(_say(
                "You can:\n"
                "• Send your issue (one line)\n"
                "• Paste Google Maps link to pin location\n"
                "• Type EMERGENCY for urgent cases\n"
                "• Type RESET to start over",
                "info"
            )), media_type="application/xml")

        if _normalize(msg) in ("reset", "start over", "cancel"):
            _reset_session(db, s, state=("ASK_ISSUE" if user else "START"))
            return Response(content=_twiml(_say("✅ Reset done. Tell me what happened.", "info")), media_type="application/xml")

        # If user exists but profile is placeholder, update
        if user and _needs_profile(user) and s.state in ("START", "ASK_ISSUE"):
            s.state = "ASK_NAME"
            s.updated_at = _now()
            db.commit()
            return Response(content=_twiml(_say("👤 Let’s update your profile. What’s your full name?", "info")), media_type="application/xml")

        # Start onboarding if no user
        if not user and s.state == "START":
            s.state = "ASK_NAME"
            s.updated_at = _now()
            db.commit()
            return Response(content=_twiml(_say("👋 Welcome to Praja.ai. What’s your full name?", "info")), media_type="application/xml")

        # Onboarding
        if s.state == "ASK_NAME":
            if len(msg) < 2 or _is_end(msg):
                return Response(content=_twiml(_say("Please send your full name.", "error")), media_type="application/xml")
            s.name = msg[:120]
            s.state = "ASK_EMAIL"
            s.updated_at = _now()
            db.commit()
            return Response(content=_twiml(_say("📧 Optional: send your email, or type SKIP.", "info")), media_type="application/xml")

        if s.state == "ASK_EMAIL":
            if _normalize(msg) == "skip":
                s.email = None
            else:
                if not _looks_like_email(msg):
                    return Response(content=_twiml(_say("That email looks invalid. Send again, or type SKIP.", "error")), media_type="application/xml")
                s.email = msg[:120]

            s.state = "ASK_OTP"
            s.updated_at = _now()
            db.commit()

            otp = _issue_otp(db, s)
            return Response(content=_twiml(_say(f"🔐 OTP: {otp}\nReply with this 6-digit OTP within 5 minutes.", "info")), media_type="application/xml")

        if s.state == "ASK_OTP":
            if not _verify_otp(s, msg):
                if s.otp_expires_at and _now() > s.otp_expires_at:
                    otp = _issue_otp(db, s)
                    return Response(content=_twiml(_say(f"⏳ OTP expired. New OTP: {otp}", "error")), media_type="application/xml")
                return Response(content=_twiml(_say("❌ OTP incorrect. Try again.", "error")), media_type="application/xml")

            if user:
                _update_user_profile(db, user, name=_safe_text(s.name, user.full_name), email=s.email)
            else:
                user = _create_user(db, phone=phone, name=_safe_text(s.name, "Citizen"), email=s.email)

            s.state = "ASK_ISSUE"
            s.updated_at = _now()
            db.commit()
            return Response(content=_twiml(_say(f"✅ Verified, {user.full_name}. Now tell me your issue.", "info")), media_type="application/xml")

        # Known user -> move to ASK_ISSUE
        if user and s.state == "START":
            s.state = "ASK_ISSUE"
            s.updated_at = _now()
            db.commit()

        # ASK_ISSUE
        if s.state == "ASK_ISSUE":
            if not msg or _is_end(msg):
                nm = user.full_name if user else "Citizen"
                return Response(content=_twiml(_say(
                    f"Okay {nm}. Tell me the issue in one line.\nExample: 'Road is broken near Kangla'.",
                    "info"
                )), media_type="application/xml")

            # If it looks like pure chat, answer without filing
            if not _looks_like_issue_text(msg) and _is_helpish(msg):
                return Response(content=_twiml(_say(_chat_reply(msg), "info")), media_type="application/xml")

            # Take as issue
            s.issue_text = msg

            guessed = _guess_address_from_text(msg)
            if guessed:
                s.address = guessed

            if Address and Address.strip():
                s.address = Address[:255]

            if s.address and (s.latitude is None or s.longitude is None):
                glat, glon = _geocode_address(s.address)
                if glat is not None and glon is not None:
                    s.latitude, s.longitude = glat, glon

            s.state = "CONFIRM"
            s.updated_at = _now()
            db.commit()
            return Response(content=_twiml(_say(_confirm_message(s), "confirm")), media_type="application/xml")

        # CONFIRM (no more trap)
        if s.state == "CONFIRM":
            if not s.issue_text:
                s.state = "ASK_ISSUE"
                s.updated_at = _now()
                db.commit()
                return Response(content=_twiml(_say("No draft pending. Tell me the issue in one line.", "info")), media_type="application/xml")

            if _normalize(msg) in ("no", "n", "cancel"):
                _reset_session(db, s, state=("ASK_ISSUE" if user else "START"))
                return Response(content=_twiml(_say("Okay, cancelled. Tell me the issue again when ready.", "info")), media_type="application/xml")

            if _normalize(msg) in ("yes", "y", "submit", "confirm"):
                user = _find_user_by_phone(db, phone)
                if not user:
                    _reset_session(db, s, state="ASK_NAME")
                    return Response(content=_twiml(_say("Before I submit: send your full name.", "info")), media_type="application/xml")

                cid = _create_complaint_from_session(db, user, s)
                _reset_session(db, s, state="ASK_ISSUE")
                return Response(content=_twiml(_say(f"✅ Submitted. Complaint ID: {cid}\nAnything else you want to report?", "success")), media_type="application/xml")

            # If user is chatting / frustrated in confirm: respond humanly and guide
            if _is_helpish(msg) or not _looks_like_issue_text(msg) or _is_end(msg):
                return Response(content=_twiml(_say(
                    _chat_reply(msg) + "\n\n(You have a draft report ready. Reply YES to submit, NO to cancel, or RESET to edit.)",
                    "info"
                )), media_type="application/xml")

            # Treat as edit and re-confirm
            s.issue_text = msg
            s.updated_at = _now()
            db.commit()
            return Response(content=_twiml(_say(_confirm_message(s), "confirm")), media_type="application/xml")

        # EMERGENCY flow (officer-style)
        if s.state == "EMERGENCY_CONFIRM_1":
            # If user is confused / chatting, keep calm and ask for YES/NO gently
            if _is_helpish(msg) or _is_greeting(msg) or _normalize(msg) in ("hmm", "bro", "what", "wtf"):
                return Response(content=_twiml(_say(
                    "I’m with you.\n"
                    "Tell me what’s happening (one sentence).\n"
                    "If you want me to trigger the emergency alert, reply YES.\n"
                    "If you want it as a normal report, reply NO.\n\n"
                    "Tip: Paste Google Maps link or share WhatsApp Location for exact pin.",
                    "emergency"
                )), media_type="application/xml")

            if _normalize(msg) in ("no", "n"):
                # downgrade to normal confirm
                s.state = "CONFIRM"
                s.updated_at = _now()
                db.commit()
                return Response(content=_twiml(_say(
                    "Okay. I will handle this as a normal report.\n" + _confirm_message(s),
                    "confirm"
                )), media_type="application/xml")

            if _normalize(msg) in ("yes", "y"):
                s.state = "EMERGENCY_CONFIRM_2"
                s.updated_at = _now()
                db.commit()
                return Response(content=_twiml(_say(
                    "Understood.\nThis will mark the report as HIGH priority.\nReply CONFIRM to proceed or CANCEL to stop.\n\n(If you're in immediate danger, call 112 now.)",
                    "emergency"
                )), media_type="application/xml")

            return Response(content=_twiml(_say(
                "Reply YES to trigger emergency alert, or NO to handle as normal report.\nTip: Paste Google Maps link to pin location.",
                "emergency"
            )), media_type="application/xml")

        if s.state == "EMERGENCY_CONFIRM_2":
            if _normalize(msg) in ("cancel", "no", "n"):
                _reset_session(db, s, state=("ASK_ISSUE" if user else "START"))
                return Response(content=_twiml(_say("Okay, cancelled. Are you safe?", "info")), media_type="application/xml")

            if _normalize(msg) not in ("confirm", "yes", "y"):
                return Response(content=_twiml(_say(
                    "Reply CONFIRM to proceed or CANCEL to stop.\nTip: Share location pin for exact map pin.",
                    "emergency"
                )), media_type="application/xml")

            user = _find_user_by_phone(db, phone)
            if not user:
                _reset_session(db, s, state="ASK_NAME")
                return Response(content=_twiml(_say("Before I proceed: send your full name.", "info")), media_type="application/xml")

            emergency_type = _detect_emergency_super(_safe_text(s.issue_text, "")) or "police"
            cid = _create_complaint_from_session(db, user, s, force_priority="High", emergency_type=emergency_type)
            _reset_session(db, s, state="ASK_ISSUE")
            return Response(content=_twiml(_say(
                f"🚨 Emergency report submitted as HIGH priority.\nComplaint ID: {cid}\n\nIf you are in immediate danger, call 112 now.",
                "success"
            )), media_type="application/xml")

        # Fallback
        _reset_session(db, s, state=("ASK_ISSUE" if user else "START"))
        return Response(content=_twiml(_say("Session refreshed. Tell me what’s going on.", "info")), media_type="application/xml")

    finally:
        db.close()

# -----------------------------
# Meta verify endpoints (optional)
# -----------------------------
@router.get("/meta")
async def meta_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN and challenge:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)

@router.post("/meta")
async def meta_incoming(request: Request):
    return {"ok": True}
