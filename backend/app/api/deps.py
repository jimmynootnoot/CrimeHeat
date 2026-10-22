from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- Role vocabulary ------------------------------------------------------
# The use-case model has two actors: PNP Personnel and Administrator.
ROLE_PNP_PERSONNEL = "pnp_personnel"
ROLE_ADMIN = "admin"

ALL_ROLES = (ROLE_PNP_PERSONNEL, ROLE_ADMIN)

# Existing deployments may still contain the former viewer/analyst values.
# Treat both as PNP Personnel so current accounts continue working while all
# newly created accounts use the two-role vocabulary from the use-case diagram.
LEGACY_PNP_ROLES = ("viewer", "analyst")


def normalize_role(role: str) -> str:
    return ROLE_PNP_PERSONNEL if role in LEGACY_PNP_ROLES else role


# Both actors can import records, run analyses, and generate reports.
PNP_PERSONNEL_OR_ADMIN = (ROLE_PNP_PERSONNEL, ROLE_ADMIN)
# Only administrators can manage users and perform destructive operations.
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
        _=Depends(require_role(*ADMIN_ONLY))                 # user management / deletion
        _=Depends(require_role(*PNP_PERSONNEL_OR_ADMIN))      # operational functions
        _=Depends(get_current_user)                           # any authenticated actor
    """

    def _check(user: User = Depends(get_current_user)) -> User:
        normalized_role = normalize_role(user.role)
        if normalized_role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"This action requires one of these roles: {', '.join(roles)}. "
                f"Your account has the '{normalized_role}' role.",
            )
        return user

    return _check
