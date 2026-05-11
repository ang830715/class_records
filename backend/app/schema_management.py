from __future__ import annotations

from sqlalchemy import Engine, inspect, text


def ensure_runtime_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    dialect = engine.dialect.name
    statements: list[str] = []

    if "password_hash" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")
    if "is_active" not in columns:
        if dialect == "postgresql":
            statements.append("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE")
        else:
            statements.append("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")
    if "is_admin" not in columns:
        if dialect == "postgresql":
            statements.append("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE")
        else:
            statements.append("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
