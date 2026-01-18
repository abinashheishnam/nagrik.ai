from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.security import decode_token
from app.db.models import User, Admin

bearer = HTTPBearer()

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    data = decode_token(creds.credentials)
    if not data or data.get("role") != "user":
        raise HTTPException(status_code=401, detail="Invalid user token")

    user = db.query(User).filter(User.id == int(data.get("sub"))).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def get_current_admin(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> Admin:
    data = decode_token(creds.credentials)
    if not data or data.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Invalid admin token")

    admin = db.query(Admin).filter(Admin.id == int(data.get("sub"))).first()
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")
    return admin
