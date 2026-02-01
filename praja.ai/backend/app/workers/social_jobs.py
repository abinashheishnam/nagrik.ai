from __future__ import annotations

from datetime import datetime
import hashlib
import multiprocessing as _mp
import traceback as _tb

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.db.social_models import SocialSource, ExtractedSignals, AIInferenceRun
from app.db.models import Complaint, AuditLog
from app.db.models import ComplaintAssignment  # ✅ for routing persistence

from app.utils.social_platform import detect_platform
from app.utils.labels import normalize_ai_outputs
from app.ai.pipeline import enrich  # ✅ existing AI pipeline

# youtube
from app.social.extractors.youtube import extract as extract_youtube
from app.social.downloaders.youtube_audio import download_youtube_audio
from app.social.transcribe_whisper import transcribe_audio

# web
from app.social.downloaders.http_fetch import fetch_html
from app.social.extractors.html_article import extract_title_and_text


# ------------------------------
# Hard-timeout helper (process)
# ------------------------------
def _run_with_timeout(fn, args=(), kwargs=None, timeout_s=60):
    """
    Run fn(*args, **kwargs) in a child process and hard-timeout it.
    This is more reliable than signal.alarm for subprocess/network stalls.
    """
    if kwargs is None:
        kwargs = {}
    q = _mp.Queue()

    def _worker():
        try:
            res = fn(*args, **kwargs)
            q.put(("ok", res))
        except Exception as e:
            q.put(("err", str(e), _tb.format_exc()))

    proc = _mp.Process(target=_worker, daemon=True)
    proc.start()
    proc.join(timeout_s)

    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        raise RuntimeError(f"timeout_after_{timeout_s}s in {getattr(fn, '__name__', 'fn')}")

    if q.empty():
        raise RuntimeError(f"child_process_no_result in {getattr(fn, '__name__', 'fn')}")

    tag, *payload = q.get()
    if tag == "ok":
        return payload[0]

    msg = payload[0]
    tb = payload[1] if len(payload) > 1 else ""
    raise RuntimeError(f"{msg}\n{tb}")


def _db() -> Session:
    return SessionLocal()


def _sha256(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8", errors="ignore")).hexdigest()


def _clip_text(s: str, max_chars: int = 8000) -> str:
    """Keep AI input bounded so summarizer doesn't choke."""
    s = (s or "").strip()
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "\n...[truncated]..."


# ------------------------------
# Safe wrappers
# ------------------------------
def _yt_extract_safe(url: str):
    return _run_with_timeout(extract_youtube, args=(url,), timeout_s=45)


def _dl_audio_safe(url: str, out_dir: str, video_id: str):
    return _run_with_timeout(
        download_youtube_audio,
        args=(url,),
        kwargs={"out_dir": out_dir, "video_id": video_id},
        timeout_s=120,
    )


def _whisper_safe(audio_path: str):
    return _run_with_timeout(
        transcribe_audio,
        args=(audio_path,),
        kwargs={"language": None},
        timeout_s=240,
    )


def _set_ss_status(db: Session, ss: SocialSource, status: str, error: str | None = None):
    ss.status = status
    ss.error = error
    if hasattr(ss, "updated_at"):
        ss.updated_at = datetime.utcnow()
    db.commit()


def _upsert_assignment(db: Session, complaint_id: int, department: str, note: str | None = None):
    """
    Persist routing decision into operations layer.
    We keep ONE active assignment row per complaint for now (latest wins).
    """
    dept = (department or "").strip() or "General Administration"

    existing = (
        db.query(ComplaintAssignment)
        .filter(ComplaintAssignment.complaint_id == complaint_id)
        .order_by(ComplaintAssignment.id.desc())
        .first()
    )

    if existing:
        # If already assigned, only update if it’s empty / generic
        if (existing.department or "").strip() in ("", "General Administration"):
            existing.department = dept
        if note:
            existing.note = note
    else:
        db.add(
            ComplaintAssignment(
                complaint_id=complaint_id,
                department=dept,
                assigned_to_admin_id=None,
                due_at=None,
                note=note,
            )
        )


def process_social_source(social_source_id: int) -> None:
    db = _db()
    ss = None

    try:
        ss = db.query(SocialSource).filter(SocialSource.id == social_source_id).first()
        if not ss:
            return

        # Stage 1: mark fetching
        _set_ss_status(db, ss, "FETCHING", None)

        platform = ss.platform or detect_platform(ss.url)

        extracted_text = ""
        transcript_text = None

        meta: dict = {
            "platform": platform,
            "url": ss.url,
            "pipeline": "social_jobs_ai_v2",
            "audio_attempted": False,
            "audio_stage": "not_started",
            "extract_stage": "starting",
        }

        platform_id = None
        canonical_url = ss.url

        # ----------------------------
        # A) YOUTUBE
        # ----------------------------
        if platform == "youtube":
            meta["extract_stage"] = "youtube_extract"
            try:
                yt = _yt_extract_safe(ss.url)
            except ValueError as ve:
                _set_ss_status(db, ss, "INVALID_URL", str(ve))
                return
            except Exception as e:
                _set_ss_status(db, ss, "FAILED", f"youtube_extract_failed: {e}")
                return

            platform_id = yt.get("platform_id")
            canonical_url = yt.get("canonical_url") or ss.url

            extracted_text = (yt.get("title") or "").strip()
            transcript_text = yt.get("transcript")  # may be None

            meta.update(
                {
                    "title": yt.get("title"),
                    "author_name": yt.get("author_name"),
                    "author_url": yt.get("author_url"),
                    "thumbnail_url": yt.get("thumbnail_url"),
                    "transcript_meta": yt.get("transcript_meta"),
                }
            )

            # Evidence expansion: yt-dlp + whisper (optional)
            meta["audio_attempted"] = True
            meta["audio_stage"] = "starting"

            try:
                if transcript_text and transcript_text.strip():
                    meta["audio_stage"] = "skipped_transcript_available"
                elif platform_id:
                    out_dir = "storage/social/youtube"
                    audio_path, dmeta = _dl_audio_safe(ss.url, out_dir=out_dir, video_id=platform_id)
                    meta["audio_download"] = dmeta
                    meta["audio_path"] = audio_path
                    meta["audio_stage"] = "downloaded"

                    wtext, wmeta = _whisper_safe(audio_path)
                    meta["whisper"] = wmeta

                    wclean = (wtext or "").strip()
                    meta["whisper_text_len"] = len(wclean)
                    meta["whisper_preview"] = wclean[:200] if wclean else ""

                    if wclean:
                        transcript_text = wclean
                        meta["audio_stage"] = "transcribed"
                    else:
                        if transcript_text is None:
                            transcript_text = ""
                        meta["audio_stage"] = "transcribed_empty"
                else:
                    meta["audio_stage"] = "skipped_no_platform_id"
            except Exception as e:
                meta["audio_or_whisper_error"] = str(e)
                meta["audio_stage"] = "error"

        # ----------------------------
        # B) WEB LINK
        # ----------------------------
        elif platform in ("web", "unknown"):
            meta["extract_stage"] = "web_fetch"
            try:
                html, fmeta = fetch_html(ss.url, retries=2, timeout=20)
                meta["fetch"] = fmeta
                meta["extract_stage"] = "web_extract"

                article = extract_title_and_text(html)
                meta["extract"] = {"title": article.get("title"), "text_len": article.get("text_len")}

                title = (article.get("title") or "").strip()
                body = (article.get("text") or "").strip()

                extracted_text = title if title else "Web link report"
                transcript_text = body

            except Exception as e:
                _set_ss_status(db, ss, "FAILED", f"web_extract_failed: {e}")
                if hasattr(ss, "fetched_at"):
                    ss.fetched_at = datetime.utcnow()
                db.commit()
                return

        else:
            extracted_text = f"Social link submitted: {ss.url}"
            transcript_text = None

        # Combine evidence for hashing + AI
        combined = (extracted_text or "").strip()
        if transcript_text is not None and transcript_text.strip():
            combined = (combined + "\n\n" + transcript_text.strip()).strip()

        payload_hash = _sha256(combined)

        # Duplicate guard (youtube)
        if platform_id:
            existing = (
                db.query(SocialSource)
                .filter(SocialSource.platform == platform)
                .filter(SocialSource.platform_id == platform_id)
                .filter(SocialSource.id != ss.id)
                .first()
            )
            if existing:
                _set_ss_status(db, ss, "DUPLICATE", f"duplicate_of_social_source_id={existing.id}")
                if hasattr(ss, "fetched_at"):
                    ss.fetched_at = datetime.utcnow()
                db.commit()
                return

        # Update social_source metadata
        try:
            ss.platform = platform
            if hasattr(ss, "platform_id"):
                ss.platform_id = platform_id
            if hasattr(ss, "canonical_url"):
                ss.canonical_url = canonical_url
            if hasattr(ss, "payload_hash"):
                ss.payload_hash = payload_hash
            if hasattr(ss, "fetched_at"):
                ss.fetched_at = datetime.utcnow()

            _set_ss_status(db, ss, "FETCHED", None)

        except IntegrityError as e:
            db.rollback()
            ss2 = db.query(SocialSource).filter(SocialSource.id == social_source_id).first()
            if ss2:
                _set_ss_status(db, ss2, "DUPLICATE", "integrity_duplicate:" + str(e))
            return

        # Upsert extracted_signals
        signals = (
            db.query(ExtractedSignals)
            .filter(ExtractedSignals.social_source_id == ss.id)
            .first()
        )

        if not signals:
            signals = ExtractedSignals(
                complaint_id=ss.complaint_id,
                social_source_id=ss.id,
                post_text=extracted_text,
                transcript=transcript_text,
                ocr_text=None,
                entities=None,
                source_metadata=meta,
            )
            db.add(signals)
        else:
            signals.post_text = extracted_text
            signals.transcript = transcript_text
            signals.source_metadata = meta
            if signals.social_source_id is None:
                signals.social_source_id = ss.id

        db.commit()

        # ----------------------------
        # AI ENRICH
        # ----------------------------
        ai_input_title = f"Social report ({platform})"
        ai_input_desc = _clip_text(combined, max_chars=8000)

        if not ai_input_desc.strip():
            _set_ss_status(db, ss, "FAILED", "no_extractable_text")
            return

        ai = enrich(ai_input_title, ai_input_desc, address="")

        # Normalize category/priority with policy
        norm = normalize_ai_outputs(ai.get("ai_category"), ai.get("ai_priority"))
        norm_cat = norm["category"]
        norm_pri = norm["priority"]

        suggested_dept = (ai.get("suggested_department") or "General Administration").strip()
        category_name = (ai.get("ai_category_name") or norm_cat).strip()

        ai_output = {
            "category": norm_cat,
            "category_name": category_name,
            "priority": norm_pri,
            "confidence": ai.get("ai_confidence", 0.5),
            "summary": ai.get("ai_summary", ""),
            "keywords": ai.get("ai_keywords", "[]"),
            "rationale": ai.get("ai_rationale", "[]"),
            "suggested_department": suggested_dept,
            "signals": {
                "platform": platform,
                "platform_id": platform_id,
                "has_transcript": bool(transcript_text) and bool((transcript_text or "").strip()),
                "audio_stage": meta.get("audio_stage"),
            },
        }

        db.add(
            AIInferenceRun(
                complaint_id=ss.complaint_id,
                model_name="praja_enrich_pipeline",
                model_version="v2",
                output=ai_output,
                confidence=float(ai_output["confidence"] or 0.0),
                requires_review=1,
            )
        )

        c = db.query(Complaint).filter(Complaint.id == ss.complaint_id).first()
        if c:
            c.ai_category = norm_cat
            c.ai_priority = norm_pri
            c.ai_confidence = float(ai_output["confidence"] or 0.0)
            c.ai_summary = ai_output["summary"]
            c.ai_rationale = ai_output["rationale"]
            c.ai_keywords = ai_output["keywords"]
            c.status = "AI_PROPOSED"

            # ✅ Persist suggested department into operations layer
            _upsert_assignment(
                db,
                complaint_id=c.id,
                department=suggested_dept,
                note=f"AI suggested dept via social ({platform})",
            )

            # Optional: if you later add complaints.suggested_department column,
            # you can store it too without breaking:
            if hasattr(c, "suggested_department"):
                c.suggested_department = suggested_dept

        db.add(
            AuditLog(
                actor_type="system",
                actor_id=0,
                action="social_processed",
                entity_type="complaint",
                entity_id=ss.complaint_id,
                meta={"social_source_id": ss.id, "platform": platform, "platform_id": platform_id, "suggested_department": suggested_dept},
                ip=None,
                user_agent="worker",
            )
        )

        _set_ss_status(db, ss, "DONE", None)

    except Exception as e:
        try:
            db.rollback()
            if ss:
                _set_ss_status(db, ss, "FAILED", str(e)[:2000])
        finally:
            raise
    finally:
        db.close()
