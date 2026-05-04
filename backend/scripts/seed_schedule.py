from __future__ import annotations

import argparse
import sys
from datetime import date, time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, engine  # noqa: E402
from app.models import ScheduleRule, TeachingClass, User  # noqa: E402


USER_ID = 1

CLASSES = ("3.5B", "PA4", "A2-4", "PreDP4", "A2-3", "A2-1")

SCHEDULE = [
    (0, "08:20", "3.5B", "P1"),
    (0, "09:15", "PA4", "P2"),
    (0, "14:55", "A2-4", "P7"),
    (0, "15:50", "PreDP4", "P8"),
    (1, "08:20", "A2-3", "P1"),
    (1, "09:15", "PreDP4", "P2"),
    (1, "10:10", "3.5B", "P3"),
    (1, "13:05", "PA4", "P5"),
    (1, "14:00", "PA4", "P6"),
    (2, "08:20", "A2-4", "P1"),
    (2, "11:05", "A2-1", "P4"),
    (3, "08:20", "PA4", "P1"),
    (3, "09:15", "3.5B", "P2"),
    (3, "14:00", "PreDP4", "P6"),
    (4, "08:20", "A2-3", "P1"),
    (4, "11:05", "A2-1", "P4"),
    (4, "14:00", "PA4", "P6"),
    (4, "14:55", "PreDP4", "P7"),
    (4, "15:50", "PreDP4", "P8"),
]


def parse_time(value: str) -> time:
    hour, minute = value.split(":", maxsplit=1)
    return time(hour=int(hour), minute=int(minute))


def ensure_user(db: Session) -> None:
    if db.get(User, USER_ID) is None:
        db.add(User(id=USER_ID, name="Teacher", email=None))


def ensure_classes(db: Session) -> dict[str, TeachingClass]:
    classes_by_name = {
        item.name: item
        for item in db.scalars(select(TeachingClass).where(TeachingClass.name.in_(CLASSES)))
    }
    for name in CLASSES:
        if name not in classes_by_name:
            item = TeachingClass(name=name, classroom=None, notes=None)
            db.add(item)
            db.flush()
            classes_by_name[name] = item
    return classes_by_name


def seed_schedule(active_from: date, duration_minutes: int) -> None:
    Base.metadata.create_all(bind=engine)
    created = 0
    updated = 0

    with Session(engine) as db:
        ensure_user(db)
        classes_by_name = ensure_classes(db)

        for weekday, start_value, class_name, period_label in SCHEDULE:
            start_time = parse_time(start_value)
            teaching_class = classes_by_name[class_name]
            rule = db.scalar(
                select(ScheduleRule).where(
                    ScheduleRule.user_id == USER_ID,
                    ScheduleRule.teaching_class_id == teaching_class.id,
                    ScheduleRule.weekday == weekday,
                    ScheduleRule.start_time == start_time,
                )
            )
            if rule is None:
                db.add(
                    ScheduleRule(
                        user_id=USER_ID,
                        teaching_class_id=teaching_class.id,
                        weekday=weekday,
                        start_time=start_time,
                        duration_minutes=duration_minutes,
                        active_from=active_from,
                        active_until=None,
                        is_active=True,
                        notes=period_label,
                    )
                )
                created += 1
            else:
                rule.duration_minutes = duration_minutes
                rule.active_from = active_from
                rule.active_until = None
                rule.is_active = True
                rule.notes = period_label
                updated += 1

        db.commit()

    print(f"Seeded schedule: {created} created, {updated} updated")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the real weekly teaching schedule.")
    parser.add_argument("--active-from", default="2026-01-01", help="Schedule start date, YYYY-MM-DD.")
    parser.add_argument("--duration-minutes", type=int, default=45, help="Duration for each period.")
    args = parser.parse_args()

    seed_schedule(date.fromisoformat(args.active_from), args.duration_minutes)


if __name__ == "__main__":
    main()
