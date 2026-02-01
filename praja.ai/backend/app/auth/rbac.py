from typing import Callable, Set, Iterable
from fastapi import Depends, HTTPException

from app.auth.dependencies import get_current_actor, get_actor_role

def require_roles(*allowed_roles: str) -> Callable:
    """
    Usage:
      dependencies=[Depends(require_roles("OFFICER", "ADMIN"))]
    """
    allowed: Set[str] = {r.strip().upper() for r in allowed_roles if isinstance(r, str) and r.strip()}

    def dep(actor=Depends(get_current_actor)):
        role = (get_actor_role(actor) or "").upper()
        if role not in allowed:
            raise HTTPException(status_code=403, detail="Forbidden (insufficient role)")
        return actor

    return dep
