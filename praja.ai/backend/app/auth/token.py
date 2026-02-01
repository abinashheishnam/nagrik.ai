from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt

# Single source of truth for JWT settings
# Make sure BOTH create + decode use these.
SECRET_KEY = "change_me_to_a_long_random_secret"  # TODO: move to env later
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h


def create_access_token(*, sub: str, role: str, actor_type: str, expires_minutes: Optional[int] = None) -> str:
    now = datetime.now(timezone.utc)
    exp_minutes = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    expire = now + timedelta(minutes=exp_minutes)

    payload: Dict[str, Any] = {
        "sub": str(sub),
        "role": role,
        "actor_type": actor_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        # Raise same message you are seeing
        raise ValueError("Invalid or expired token") from e
