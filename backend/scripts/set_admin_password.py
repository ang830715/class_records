from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import models  # noqa: E402,F401
from app.auth import hash_password  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.models import User  # noqa: E402
from app.schema_management import ensure_runtime_columns  # noqa: E402


def normalize_email(email: str) -> str:
    return email.strip().lower()


def main() -> None:
    parser = argparse.ArgumentParser(description="Set or reset the primary admin login.")
    parser.add_argument("--email", required=True, help="Admin email address.")
    parser.add_argument("--name", default="Teacher", help="Admin display name.")
    parser.add_argument("--password", help="Admin password. If omitted, you will be prompted.")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    if not password:
        raise SystemExit("Password cannot be empty")

    Base.metadata.create_all(bind=engine)
    ensure_runtime_columns(engine)

    with Session(engine) as db:
        normalized_email = normalize_email(args.email)
        user = db.scalar(select(User).where(func.lower(User.email) == normalized_email))
        if user is None:
            user = User(name=args.name, email=normalized_email, is_active=True, is_admin=True)
            db.add(user)
        else:
            user.name = args.name
            user.email = normalized_email
            user.is_active = True
            user.is_admin = True
        user.password_hash = hash_password(password)
        db.commit()

    print(f"Admin login updated for {normalized_email}")


if __name__ == "__main__":
    main()
