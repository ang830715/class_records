from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, DATABASE_URL, engine  # noqa: E402
from app import models  # noqa: E402,F401
from app.schema_management import ensure_runtime_columns  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_columns(engine)
    with Session(engine) as db:
        db.execute(text("select 1"))

    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    masked_url = DATABASE_URL
    if "://" in masked_url and "@" in masked_url:
        scheme, rest = masked_url.split("://", maxsplit=1)
        _, host = rest.rsplit("@", maxsplit=1)
        masked_url = f"{scheme}://***:***@{host}"

    print(f"Database OK: {masked_url}")
    print(f"Tables: {', '.join(tables) if tables else 'none'}")


if __name__ == "__main__":
    main()
