from __future__ import annotations

from fastapi import Depends, HTTPException, status

from fastapi_app.database import User
from fastapi_app.middleware.auth import get_current_user


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admins only.",
        )
    return user
