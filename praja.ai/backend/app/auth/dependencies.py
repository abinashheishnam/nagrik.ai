from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, Admin
from app.auth.token import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/user/login")

def get_current_actor(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    actor_type = payload.get("actor_type") or payload.get("actor") or "user"
    sub = payload.get("sub")
    role = payload.get("role") or ""

    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token (no subject)")

    if actor_type == "admin":
        actor = db.query(Admin).filter(Admin.id == int(sub)).first()
        if not actor:
            raise HTTPException(status_code=401, detail="Admin not found")
        actor._actor_type = "admin"
        actor._role = role or getattr(actor, "role", "")
        return actor

    actor = db.query(User).filter(User.id == int(sub)).first()
    if not actor:
        raise HTTPException(status_code=401, detail="User not found")
    actor._actor_type = "user"
    actor._role = role or "CITIZEN"
    return actor

def get_actor_role(actor) -> str:
    # Prefer JWT role (attached as _role), fallback to DB role field
    return getattr(actor, "_role", "") or getattr(actor, "role", "") or "CITIZEN"

def get_current_admin(actor=Depends(get_current_actor)):
    if getattr(actor, "_actor_type", "") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return actor

def get_current_user(actor=Depends(get_current_actor)):
    if getattr(actor, "_actor_type", "") != "user":
        raise HTTPException(status_code=403, detail="Users only")
    return actor
