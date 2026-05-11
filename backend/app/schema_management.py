from __future__ import annotations

from collections import defaultdict

from sqlalchemy import Engine, inspect, text


def _execute_all(connection, statements: list[str]) -> None:
    for statement in statements:
        connection.execute(text(statement))


def _ensure_default_user_row(connection, dialect: str) -> int:
    existing_user_id = connection.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
    if existing_user_id is not None:
        return int(existing_user_id)

    if dialect == "postgresql":
        connection.execute(
            text(
                """
                INSERT INTO users (id, name, email, password_hash, is_active, is_admin)
                VALUES (1, 'Teacher', NULL, NULL, TRUE, FALSE)
                """
            )
        )
    else:
        connection.execute(
            text(
                """
                INSERT INTO users (id, name, email, password_hash, is_active, is_admin)
                VALUES (1, 'Teacher', NULL, NULL, 1, 0)
                """
            )
        )
    return 1


def _teaching_class_user_refs(connection) -> dict[int, set[int]]:
    refs: dict[int, set[int]] = defaultdict(set)
    for row in connection.execute(text("SELECT teaching_class_id, user_id FROM schedule_rules")).mappings():
        refs[int(row["teaching_class_id"])].add(int(row["user_id"]))
    for row in connection.execute(text("SELECT teaching_class_id, user_id FROM class_records")).mappings():
        refs[int(row["teaching_class_id"])].add(int(row["user_id"]))
    return refs


def _all_user_ids(connection, fallback_user_id: int) -> list[int]:
    user_ids = [int(row[0]) for row in connection.execute(text("SELECT id FROM users ORDER BY id"))]
    return user_ids or [fallback_user_id]


def _migrate_teaching_classes_sqlite(engine: Engine) -> None:
    with engine.begin() as connection:
        fallback_user_id = _ensure_default_user_row(connection, "sqlite")
        class_rows = list(
            connection.execute(
                text("SELECT id, name, classroom, notes FROM teaching_classes ORDER BY id")
            ).mappings()
        )
        refs = _teaching_class_user_refs(connection)
        next_id = max((int(row["id"]) for row in class_rows), default=0)
        new_rows: list[dict[str, object]] = []
        remaps: list[dict[str, int]] = []

        for row in class_rows:
            class_id = int(row["id"])
            user_ids = sorted(refs.get(class_id) or {fallback_user_id})
            first = True
            for user_id in user_ids:
                if first:
                    new_id = class_id
                    first = False
                else:
                    next_id += 1
                    new_id = next_id
                    remaps.append({"old_id": class_id, "user_id": user_id, "new_id": new_id})
                new_rows.append(
                    {
                        "id": new_id,
                        "user_id": user_id,
                        "name": row["name"],
                        "classroom": row["classroom"],
                        "notes": row["notes"],
                    }
                )

        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.execute(text("ALTER TABLE teaching_classes RENAME TO teaching_classes_old"))
        connection.execute(
            text(
                """
                CREATE TABLE teaching_classes (
                    id INTEGER NOT NULL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(160) NOT NULL,
                    classroom VARCHAR(120),
                    notes TEXT,
                    CONSTRAINT uq_teaching_classes_user_name UNIQUE (user_id, name),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
        )
        for row in new_rows:
            connection.execute(
                text(
                    """
                    INSERT INTO teaching_classes (id, user_id, name, classroom, notes)
                    VALUES (:id, :user_id, :name, :classroom, :notes)
                    """
                ),
                row,
            )
        for remap in remaps:
            connection.execute(
                text(
                    """
                    UPDATE schedule_rules
                    SET teaching_class_id = :new_id
                    WHERE teaching_class_id = :old_id AND user_id = :user_id
                    """
                ),
                remap,
            )
            connection.execute(
                text(
                    """
                    UPDATE class_records
                    SET teaching_class_id = :new_id
                    WHERE teaching_class_id = :old_id AND user_id = :user_id
                    """
                ),
                remap,
            )
        connection.execute(text("DROP TABLE teaching_classes_old"))
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def _migrate_teaching_classes_postgresql(engine: Engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as connection:
        fallback_user_id = _ensure_default_user_row(connection, "postgresql")
        connection.execute(text("ALTER TABLE teaching_classes ADD COLUMN user_id INTEGER"))

        for constraint in inspector.get_unique_constraints("teaching_classes"):
            if constraint.get("column_names") == ["name"] and constraint.get("name"):
                safe_name = constraint["name"].replace('"', '""')
                connection.execute(text(f'ALTER TABLE teaching_classes DROP CONSTRAINT IF EXISTS "{safe_name}"'))

        class_rows = list(
            connection.execute(
                text("SELECT id, name, classroom, notes FROM teaching_classes ORDER BY id")
            ).mappings()
        )
        refs = _teaching_class_user_refs(connection)

        for row in class_rows:
            class_id = int(row["id"])
            user_ids = sorted(refs.get(class_id) or {fallback_user_id})
            connection.execute(
                text("UPDATE teaching_classes SET user_id = :user_id WHERE id = :class_id"),
                {"user_id": user_ids[0], "class_id": class_id},
            )
            for user_id in user_ids[1:]:
                new_id = connection.execute(
                    text(
                        """
                        INSERT INTO teaching_classes (user_id, name, classroom, notes)
                        VALUES (:user_id, :name, :classroom, :notes)
                        RETURNING id
                        """
                    ),
                    {
                        "user_id": user_id,
                        "name": row["name"],
                        "classroom": row["classroom"],
                        "notes": row["notes"],
                    },
                ).scalar_one()
                remap = {"old_id": class_id, "user_id": user_id, "new_id": int(new_id)}
                connection.execute(
                    text(
                        """
                        UPDATE schedule_rules
                        SET teaching_class_id = :new_id
                        WHERE teaching_class_id = :old_id AND user_id = :user_id
                        """
                    ),
                    remap,
                )
                connection.execute(
                    text(
                        """
                        UPDATE class_records
                        SET teaching_class_id = :new_id
                        WHERE teaching_class_id = :old_id AND user_id = :user_id
                        """
                    ),
                    remap,
                )

        connection.execute(text("UPDATE teaching_classes SET user_id = :user_id WHERE user_id IS NULL"), {"user_id": fallback_user_id})
        connection.execute(
            text(
                """
                ALTER TABLE teaching_classes
                ADD CONSTRAINT teaching_classes_user_id_fkey
                FOREIGN KEY (user_id) REFERENCES users(id)
                """
            )
        )
        connection.execute(text("ALTER TABLE teaching_classes ALTER COLUMN user_id SET NOT NULL"))
        connection.execute(
            text(
                """
                ALTER TABLE teaching_classes
                ADD CONSTRAINT uq_teaching_classes_user_name UNIQUE (user_id, name)
                """
            )
        )


def _migrate_semesters_sqlite(engine: Engine) -> None:
    with engine.begin() as connection:
        fallback_user_id = _ensure_default_user_row(connection, "sqlite")
        semester_rows = list(
            connection.execute(
                text("SELECT id, name, start_date, end_date FROM semesters ORDER BY id")
            ).mappings()
        )
        user_ids = _all_user_ids(connection, fallback_user_id)
        next_id = max((int(row["id"]) for row in semester_rows), default=0)
        new_rows: list[dict[str, object]] = []

        for row in semester_rows:
            first = True
            for user_id in user_ids:
                if first:
                    new_id = int(row["id"])
                    first = False
                else:
                    next_id += 1
                    new_id = next_id
                new_rows.append(
                    {
                        "id": new_id,
                        "user_id": user_id,
                        "name": row["name"],
                        "start_date": row["start_date"],
                        "end_date": row["end_date"],
                    }
                )

        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.execute(text("ALTER TABLE semesters RENAME TO semesters_old"))
        connection.execute(
            text(
                """
                CREATE TABLE semesters (
                    id INTEGER NOT NULL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(160) NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    CONSTRAINT uq_semesters_user_name UNIQUE (user_id, name),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
        )
        for row in new_rows:
            connection.execute(
                text(
                    """
                    INSERT INTO semesters (id, user_id, name, start_date, end_date)
                    VALUES (:id, :user_id, :name, :start_date, :end_date)
                    """
                ),
                row,
            )
        connection.execute(text("DROP TABLE semesters_old"))
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def _migrate_semesters_postgresql(engine: Engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as connection:
        fallback_user_id = _ensure_default_user_row(connection, "postgresql")
        user_ids = _all_user_ids(connection, fallback_user_id)
        connection.execute(text("ALTER TABLE semesters ADD COLUMN user_id INTEGER"))

        for constraint in inspector.get_unique_constraints("semesters"):
            if constraint.get("column_names") == ["name"] and constraint.get("name"):
                safe_name = constraint["name"].replace('"', '""')
                connection.execute(text(f'ALTER TABLE semesters DROP CONSTRAINT IF EXISTS "{safe_name}"'))

        semester_rows = list(
            connection.execute(
                text("SELECT id, name, start_date, end_date FROM semesters ORDER BY id")
            ).mappings()
        )

        for row in semester_rows:
            connection.execute(
                text("UPDATE semesters SET user_id = :user_id WHERE id = :semester_id"),
                {"user_id": user_ids[0], "semester_id": int(row["id"])},
            )
            for user_id in user_ids[1:]:
                connection.execute(
                    text(
                        """
                        INSERT INTO semesters (user_id, name, start_date, end_date)
                        VALUES (:user_id, :name, :start_date, :end_date)
                        """
                    ),
                    {
                        "user_id": user_id,
                        "name": row["name"],
                        "start_date": row["start_date"],
                        "end_date": row["end_date"],
                    },
                )

        connection.execute(text("UPDATE semesters SET user_id = :user_id WHERE user_id IS NULL"), {"user_id": fallback_user_id})
        connection.execute(
            text(
                """
                ALTER TABLE semesters
                ADD CONSTRAINT semesters_user_id_fkey
                FOREIGN KEY (user_id) REFERENCES users(id)
                """
            )
        )
        connection.execute(text("ALTER TABLE semesters ALTER COLUMN user_id SET NOT NULL"))
        connection.execute(
            text(
                """
                ALTER TABLE semesters
                ADD CONSTRAINT uq_semesters_user_name UNIQUE (user_id, name)
                """
            )
        )


def ensure_runtime_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
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

        if statements:
            with engine.begin() as connection:
                _execute_all(connection, statements)

    inspector = inspect(engine)
    if "teaching_classes" in inspector.get_table_names():
        class_columns = {column["name"] for column in inspector.get_columns("teaching_classes")}
        if "user_id" not in class_columns:
            if engine.dialect.name == "sqlite":
                _migrate_teaching_classes_sqlite(engine)
            elif engine.dialect.name == "postgresql":
                _migrate_teaching_classes_postgresql(engine)
            else:
                raise RuntimeError(f"TeachingClass ownership migration is not implemented for {engine.dialect.name}")

    inspector = inspect(engine)
    if "semesters" in inspector.get_table_names():
        semester_columns = {column["name"] for column in inspector.get_columns("semesters")}
        if "user_id" not in semester_columns:
            if engine.dialect.name == "sqlite":
                _migrate_semesters_sqlite(engine)
            elif engine.dialect.name == "postgresql":
                _migrate_semesters_postgresql(engine)
            else:
                raise RuntimeError(f"Semester ownership migration is not implemented for {engine.dialect.name}")
