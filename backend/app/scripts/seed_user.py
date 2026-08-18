"""Create the local development accounts.

Run with: python -m app.scripts.seed_user

Seeds one account per role so the three access levels can be demonstrated and
tested without hand-provisioning users. `/api/auth/register` is administrator-
only, so these are the accounts used to bootstrap a fresh environment.

LOCAL DEVELOPMENT ONLY. These credentials are published in the README and must
never exist in a deployment holding real records.
"""
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User

DEFAULT_EMAIL = "analyst@ppalma.local"
DEFAULT_PASSWORD = "ppalma-dev-2026"

# (email, password, role)
DEMO_ACCOUNTS = [
    (DEFAULT_EMAIL, DEFAULT_PASSWORD, "admin"),
    ("analyst2@ppalma.local", "ppalma-dev-2026", "analyst"),
    ("viewer@ppalma.local", "ppalma-dev-2026", "viewer"),
]


def run() -> None:
    db = SessionLocal()
    try:
        for email, password, role in DEMO_ACCOUNTS:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                if existing.role != role:
                    previous = existing.role
                    existing.role = role
                    db.commit()
                    print(f"Updated {email}: role {previous} -> {role}")
                else:
                    print(f"Exists: {email} (role={role})")
                continue

            db.add(User(email=email, password_hash=hash_password(password), role=role))
            db.commit()
            print(f"Created: {email} / {password} (role={role})")

        print("\nLocal development credentials only — do not use in any deployment "
              "holding real records.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
