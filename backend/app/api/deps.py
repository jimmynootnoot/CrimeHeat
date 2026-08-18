from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- Role vocabulary ------------------------------------------------------
# Ordered least to most privileged. Authorization is checked by explicit
# membership, not by comparing ranks, so a future non-hierarchical role can be
# added without silently granting it someone else's permissions.
ROLE_VIEWER = "viewer"
ROLE_ANALYST = "analyst"
ROLE_ADMIN = "admin"

ALL_ROLES = (ROLE_VIEWER, ROLE_ANALYST, ROLE_ADMIN)

# Roles permitted to upload, validate, and run analyses.
ANALYST_OR_ADMIN = (ROLE_ANALYST, ROLE_ADMIN)
# Roles permitted to manage users, delete data, and change analytical parameters.
ADMIN_ONLY = (ROLE_ADMIN,)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    email = decode_access_token(token)
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_role(*roles: str):
    """Dependency factory restricting a route to specific `User.role` values.

    Enforcement lives here, server-side. Hiding a control in the frontend is a
    usability affordance, not access control — every restricted route carries
    this dependency regardless of what the interface shows.

    Typical use:
        _=Depends(require_role(*ADMIN_ONLY))        # destructive / configuration
        _=Depends(require_role(*ANALYST_OR_ADMIN))  # upload, run analysis
        _=Depends(get_current_user)                 # any authenticated user, incl. viewer
    """

    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"This action requires one of these roles: {', '.join(roles)}. "
                f"Your account has the '{user.role}' role.",
            )
        return user

    return _check
