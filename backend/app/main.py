from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from .database import Base, engine, get_db
from .models import ClassRecord, ClassStatus, Course, EditLog, ScheduleRule, Semester, StudentGroup, User
from .schemas import (
    ClassRecordCreate,
    ClassRecordRead,
    ClassRecordUpdate,
    CourseCreate,
    CourseRead,
    CourseUpdate,
    EditLogRead,
    ScheduleRuleCreate,
    ScheduleRuleRead,
    ScheduleRuleUpdate,
    SemesterCreate,
    SemesterRead,
    StatsByStudent,
    StatsRead,
    StudentGroupCreate,
    StudentGroupRead,
    StudentGroupUpdate,
    TodayItem,
)

DbSession = Annotated[Session, Depends(get_db)]

app = FastAPI(title="Teaching Record System", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        if db.get(User, 1) is None:
            db.add(User(id=1, name="Teacher", email=None))
            db.commit()


def get_or_404(db: Session, model: type, item_id: int):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


def schedule_query(user_id: int = 1) -> Select[tuple[ScheduleRule]]:
    return (
        select(ScheduleRule)
        .where(ScheduleRule.user_id == user_id)
        .options(selectinload(ScheduleRule.student_group), selectinload(ScheduleRule.course))
        .order_by(ScheduleRule.weekday, ScheduleRule.start_time)
    )


def record_query(user_id: int = 1) -> Select[tuple[ClassRecord]]:
    return (
        select(ClassRecord)
        .where(ClassRecord.user_id == user_id)
        .options(selectinload(ClassRecord.student_group), selectinload(ClassRecord.course))
        .order_by(ClassRecord.date.desc(), ClassRecord.start_time.desc())
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/student-groups", response_model=list[StudentGroupRead])
def list_student_groups(db: DbSession) -> list[StudentGroup]:
    return list(db.scalars(select(StudentGroup).order_by(StudentGroup.name)))


@app.post("/student-groups", response_model=StudentGroupRead, status_code=status.HTTP_201_CREATED)
def create_student_group(payload: StudentGroupCreate, db: DbSession) -> StudentGroup:
    item = StudentGroup(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.put("/student-groups/{group_id}", response_model=StudentGroupRead)
def update_student_group(group_id: int, payload: StudentGroupUpdate, db: DbSession) -> StudentGroup:
    item = get_or_404(db, StudentGroup, group_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/student-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student_group(group_id: int, db: DbSession) -> None:
    db.delete(get_or_404(db, StudentGroup, group_id))
    db.commit()


@app.get("/courses", response_model=list[CourseRead])
def list_courses(db: DbSession) -> list[Course]:
    return list(db.scalars(select(Course).order_by(Course.name)))


@app.post("/courses", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: DbSession) -> Course:
    item = Course(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.put("/courses/{course_id}", response_model=CourseRead)
def update_course(course_id: int, payload: CourseUpdate, db: DbSession) -> Course:
    item = get_or_404(db, Course, course_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, db: DbSession) -> None:
    db.delete(get_or_404(db, Course, course_id))
    db.commit()


@app.get("/schedule", response_model=list[ScheduleRuleRead])
def list_schedule(db: DbSession, user_id: int = 1) -> list[ScheduleRule]:
    return list(db.scalars(schedule_query(user_id)))


@app.post("/schedule", response_model=ScheduleRuleRead, status_code=status.HTTP_201_CREATED)
def create_schedule_rule(payload: ScheduleRuleCreate, db: DbSession) -> ScheduleRule:
    if payload.active_until and payload.active_until < payload.active_from:
        raise HTTPException(status_code=400, detail="active_until must be after active_from")
    item = ScheduleRule(**payload.model_dump())
    db.add(item)
    db.commit()
    return get_or_404(db, ScheduleRule, item.id)


@app.put("/schedule/{rule_id}", response_model=ScheduleRuleRead)
def update_schedule_rule(rule_id: int, payload: ScheduleRuleUpdate, db: DbSession) -> ScheduleRule:
    item = get_or_404(db, ScheduleRule, rule_id)
    values = payload.model_dump(exclude_unset=True)
    active_from = values.get("active_from", item.active_from)
    active_until = values.get("active_until", item.active_until)
    if active_until and active_until < active_from:
        raise HTTPException(status_code=400, detail="active_until must be after active_from")
    for key, value in values.items():
        setattr(item, key, value)
    db.commit()
    return get_or_404(db, ScheduleRule, rule_id)


@app.delete("/schedule/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_rule(rule_id: int, db: DbSession) -> None:
    db.delete(get_or_404(db, ScheduleRule, rule_id))
    db.commit()


@app.get("/records", response_model=list[ClassRecordRead])
def list_records(
    db: DbSession,
    user_id: int = 1,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ClassRecord]:
    query = record_query(user_id)
    if start_date:
        query = query.where(ClassRecord.date >= start_date)
    if end_date:
        query = query.where(ClassRecord.date <= end_date)
    return list(db.scalars(query))


@app.post("/records", response_model=ClassRecordRead, status_code=status.HTTP_201_CREATED)
def create_record(payload: ClassRecordCreate, db: DbSession) -> ClassRecord:
    item = ClassRecord(**payload.model_dump())
    db.add(item)
    db.commit()
    return get_or_404(db, ClassRecord, item.id)


@app.put("/records/{record_id}", response_model=ClassRecordRead)
def update_record(record_id: int, payload: ClassRecordUpdate, db: DbSession) -> ClassRecord:
    item = get_or_404(db, ClassRecord, record_id)
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        old_value = getattr(item, key)
        if old_value != value:
            db.add(
                EditLog(
                    record_id=item.id,
                    field_name=key,
                    old_value=None if old_value is None else str(old_value),
                    new_value=None if value is None else str(value),
                )
            )
            setattr(item, key, value)
    db.commit()
    return get_or_404(db, ClassRecord, record_id)


@app.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, db: DbSession) -> None:
    db.delete(get_or_404(db, ClassRecord, record_id))
    db.commit()


@app.get("/records/{record_id}/edits", response_model=list[EditLogRead])
def list_record_edits(record_id: int, db: DbSession) -> list[EditLog]:
    get_or_404(db, ClassRecord, record_id)
    return list(db.scalars(select(EditLog).where(EditLog.record_id == record_id).order_by(EditLog.edited_at.desc())))


@app.get("/today", response_model=list[TodayItem])
def today(db: DbSession, target_date: date | None = None, user_id: int = 1) -> list[TodayItem]:
    target = target_date or date.today()
    schedules = list(
        db.scalars(
            schedule_query(user_id)
            .where(ScheduleRule.weekday == target.weekday())
            .where(ScheduleRule.is_active.is_(True))
            .where(ScheduleRule.active_from <= target)
            .where((ScheduleRule.active_until.is_(None)) | (ScheduleRule.active_until >= target))
        )
    )
    records = list(db.scalars(record_query(user_id).where(ClassRecord.date == target)))
    records_by_schedule = {record.schedule_rule_id: record for record in records if record.schedule_rule_id is not None}
    items: list[TodayItem] = []
    for rule in schedules:
        record = records_by_schedule.get(rule.id)
        items.append(
            TodayItem(
                kind="matched" if record else "expected",
                schedule_rule=rule,
                record=record,
                expected_date=target,
            )
        )
    scheduled_ids = {rule.id for rule in schedules}
    for record in records:
        if record.schedule_rule_id not in scheduled_ids:
            items.append(TodayItem(kind="actual", schedule_rule=None, record=record, expected_date=target))
    return sorted(items, key=lambda item: (item.record.start_time if item.record else item.schedule_rule.start_time))


@app.get("/missing-days", response_model=list[date])
def missing_days(
    db: DbSession,
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: int = 1,
) -> list[date]:
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    rules = list(db.scalars(schedule_query(user_id).where(ScheduleRule.is_active.is_(True))))
    records = {
        row[0]
        for row in db.execute(
            select(ClassRecord.date).where(
                ClassRecord.user_id == user_id,
                ClassRecord.date >= start_date,
                ClassRecord.date <= end_date,
            )
        )
    }
    missing: list[date] = []
    current = start_date
    while current <= end_date:
        has_schedule = any(
            rule.weekday == current.weekday()
            and rule.active_from <= current
            and (rule.active_until is None or rule.active_until >= current)
            for rule in rules
        )
        if has_schedule and current not in records:
            missing.append(current)
        current += timedelta(days=1)
    return missing


@app.get("/stats", response_model=StatsRead)
def stats(
    db: DbSession,
    range: str = Query(default="month", pattern="^(week|month|semester|custom)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    semester_id: int | None = None,
    user_id: int = 1,
) -> StatsRead:
    today_date = date.today()
    if range == "week":
        start = today_date - timedelta(days=today_date.weekday())
        end = start + timedelta(days=6)
    elif range == "month":
        start = today_date.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(days=1)
    elif range == "semester":
        semester = db.get(Semester, semester_id) if semester_id else db.scalar(
            select(Semester)
            .where(Semester.start_date <= today_date, Semester.end_date >= today_date)
            .order_by(Semester.start_date.desc())
        )
        if semester is None:
            raise HTTPException(status_code=404, detail="No matching semester found")
        start, end = semester.start_date, semester.end_date
    else:
        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="custom range requires start_date and end_date")
        start, end = start_date, end_date
    if end < start:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    records = list(
        db.scalars(
            record_query(user_id)
            .where(ClassRecord.date >= start)
            .where(ClassRecord.date <= end)
        )
    )

    def count(status: ClassStatus) -> int:
        return sum(1 for record in records if record.status == status)

    taught_records = [record for record in records if record.status == ClassStatus.taught]
    salary = sum((Decimal(record.fee_amount) for record in taught_records), Decimal("0"))
    total_minutes = sum(record.duration_minutes for record in taught_records)
    by_student_rows = db.execute(
        select(
            StudentGroup.id,
            StudentGroup.name,
            func.count(ClassRecord.id),
            func.coalesce(func.sum(ClassRecord.duration_minutes), 0),
            func.coalesce(func.sum(ClassRecord.fee_amount), 0),
        )
        .join(ClassRecord, ClassRecord.student_group_id == StudentGroup.id)
        .where(
            ClassRecord.user_id == user_id,
            ClassRecord.date >= start,
            ClassRecord.date <= end,
            ClassRecord.status == ClassStatus.taught,
        )
        .group_by(StudentGroup.id, StudentGroup.name)
        .order_by(StudentGroup.name)
    )

    return StatsRead(
        start_date=start,
        end_date=end,
        taught_count=count(ClassStatus.taught),
        canceled_count=count(ClassStatus.canceled),
        rescheduled_count=count(ClassStatus.rescheduled),
        extra_count=count(ClassStatus.extra),
        pending_count=count(ClassStatus.pending),
        total_minutes=total_minutes,
        salary=salary,
        by_student=[
            StatsByStudent(
                student_group_id=row[0],
                student_group_name=row[1],
                taught_count=row[2],
                total_minutes=row[3],
                salary=row[4],
            )
            for row in by_student_rows
        ],
    )


@app.get("/semesters", response_model=list[SemesterRead])
def list_semesters(db: DbSession) -> list[Semester]:
    return list(db.scalars(select(Semester).order_by(Semester.start_date.desc())))


@app.post("/semesters", response_model=SemesterRead, status_code=status.HTTP_201_CREATED)
def create_semester(payload: SemesterCreate, db: DbSession) -> Semester:
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    item = Semester(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
