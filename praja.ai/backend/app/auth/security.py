from datetime import datetime, timedelta
from jose import jwt, JWTError
import bcrypt
from app.utils.config import settings

def hash_password(password: str) -> str:
    pw = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pw, salt).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    pw = password.encode("utf-8")
    ph = password_hash.encode("utf-8")
    return bcrypt.checkpw(pw, ph)

def create_access_token(sub: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    payload = {"sub": sub, "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGO)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGO])
    except JWTError:
        return {}
