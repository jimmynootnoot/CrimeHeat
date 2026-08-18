from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ONLY, ALL_ROLES, get_current_user, require_role
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.services import audit_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        audit_service.record(
            db,
            audit_service.LOGIN_FAILED,
            user_email=form_data.username,
            status="failure",
            request=request,
        )
        # Deliberately the same message for an unknown email and a wrong
        # password — distinguishing them would let an attacker enumerate
        # which accounts exist.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    token = create_access_token(subject=user.email, role=user.role)
    audit_service.record(db, audit_service.LOGIN_SUCCESS, user=user, request=request)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "email": user.email,
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Record the logout in the audit trail.

    Access tokens are stateless JWTs, so the server cannot revoke one — the
    client discards it and it expires on its own. This endpoint exists so that
    logouts are visible in the audit log alongside logins.
    """
    audit_service.record(db, audit_service.LOGOUT, user=user, request=request)
    return {"detail": "Logged out"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    email: str,
    password: str,
    request: Request,
    role: str = "viewer",
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(*ADMIN_ONLY)),
):
    """Create a user account. Administrator only.

    Open self-registration is deliberately NOT offered. This is an internal
    analytical tool over crime data; an unauthenticated sign-up route would let
    anyone provision themselves access. Accounts default to the least
    privileged role and must be upgraded explicitly.
    """
    if role not in ALL_ROLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown role '{role}'. Valid roles: {', '.join(ALL_ROLES)}",
        )
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    if len(password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must be at least 8 characters")

    user = User(email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)

    audit_service.record(
        db,
        audit_service.USER_CREATED,
        user=actor,
        entity_type="user",
        entity_id=user.id,
        details={"created_email": user.email, "role": user.role},
        request=request,
    )
    return {"id": user.id, "email": user.email, "role": user.role}
